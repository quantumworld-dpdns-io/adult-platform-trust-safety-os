terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }

  backend "s3" {
    bucket         = "trust-safety-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "adult-platform-trust-safety-os"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  cluster_name = "${var.cluster_name}-${var.environment}"
  azs          = slice(data.aws_availability_zones.available.names, 0, 3)
}

module "eks" {
  source = "./modules/eks"

  cluster_name       = local.cluster_name
  cluster_version    = var.cluster_version
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets
  node_instance_types = var.node_instance_types
  node_desired_size  = var.node_desired_size
  node_min_size      = var.node_min_size
  node_max_size      = var.node_max_size
}

module "rds" {
  source = "./modules/rds"

  identifier        = "${local.cluster_name}-db"
  engine_version    = var.db_engine_version
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  database_name     = var.db_name
  database_user     = var.db_user
  database_password = var.db_password
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.database_subnets
  allowed_security_group_ids = [module.eks.node_security_group_id]
}

module "elasticache" {
  source = "./modules/elasticache"

  cluster_id        = "${local.cluster_name}-redis"
  engine_version    = var.redis_engine_version
  node_type         = var.redis_node_type
  num_cache_nodes   = var.redis_num_cache_nodes
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.database_subnets
  allowed_security_group_ids = [module.eks.node_security_group_id]
}

module "s3" {
  source = "./modules/s3"

  bucket_name     = "${local.cluster_name}-media"
  environment     = var.environment
  enable_versioning = true
}

module "cloudfront" {
  source = "./modules/cloudfront"

  domain_name         = var.domain_name
  origin_bucket_id    = module.s3.bucket_id
  origin_bucket_arn   = module.s3.bucket_arn
  api_origin_domain   = module.eks.cluster_endpoint
  acm_certificate_arn = var.acm_certificate_arn
}

module "waf" {
  source = "./modules/waf"

  name        = "${local.cluster_name}-waf"
  description = "WAF rules for Trust & Safety API"
  cloudfront_arn = module.cloudfront.distribution_arn
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${local.cluster_name}-vpc"
  cidr = var.vpc_cidr

  azs             = local.azs
  private_subnets = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 4, i)]
  public_subnets  = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 4, i + 4)]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "production"
  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}
