variable "identifier" {
  type = string
}

variable "engine_version" {
  type    = string
  default = "16.1"
}

variable "instance_class" {
  type    = string
  default = "db.r6g.large"
}

variable "allocated_storage" {
  type    = number
  default = 100
}

variable "database_name" {
  type = string
}

variable "database_user" {
  type      = string
  sensitive = true
}

variable "database_password" {
  type      = string
  sensitive = true
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "allowed_security_group_ids" {
  type    = list(string)
  default = []
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.identifier}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Name = var.identifier
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.identifier}-"
  vpc_id      = var.vpc_id
  description = "Security group for ${var.identifier}"

  tags = {
    Name = "${var.identifier}-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group_rule" "rds_ingress" {
  for_each = toset(var.allowed_security_group_ids)

  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = each.value
  security_group_id        = aws_security_group.rds.id
}

resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_rds_cluster_instance" "main" {
  count = 2

  identifier         = "${var.identifier}-${count.index}"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = var.instance_class
  engine             = aws_rds_cluster.main.engine
  engine_version     = aws_rds_cluster.main.engine_version

  performance_insights_enabled = true
  monitoring_interval          = 60

  tags = {
    Name = "${var.identifier}-${count.index}"
  }
}

resource "aws_rds_cluster" "main" {
  cluster_identifier     = var.identifier
  engine                 = "aurora-postgresql"
  engine_version         = var.engine_version
  database_name          = var.database_name
  master_username        = var.database_user
  master_password        = var.database_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.rds.arn

  backup_retention_period = 14
  preferred_backup_window = "03:00-04:00"
  skip_final_snapshot     = var.environment != "production"
  final_snapshot_identifier = var.environment == "production" ? "${var.identifier}-final" : null

  deletion_protection = var.environment == "production"

  tags = {
    Name = var.identifier
  }
}

variable "environment" {
  type    = string
  default = "development"
}

output "endpoint" {
  value = aws_rds_cluster.main.endpoint
}

output "port" {
  value = aws_rds_cluster.main.port
}

output "security_group_id" {
  value = aws_security_group.rds.id
}
