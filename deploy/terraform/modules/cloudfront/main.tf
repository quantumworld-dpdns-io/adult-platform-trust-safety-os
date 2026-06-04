variable "domain_name" {
  type    = string
  default = ""
}

variable "origin_bucket_id" {
  type = string
}

variable "origin_bucket_arn" {
  type = string
}

variable "api_origin_domain" {
  type    = string
  default = ""
}

variable "acm_certificate_arn" {
  type    = string
  default = ""
}

locals {
  s3_origin_id   = "S3-${var.origin_bucket_id}"
  api_origin_id  = "API-${var.api_origin_domain}"
  has_custom_domain = var.domain_name != "" && var.acm_certificate_arn != ""
}

resource "aws_cloudfront_origin_access_identity" "main" {
  comment = "OAI for ${var.origin_bucket_id}"
}

resource "aws_s3_bucket_policy" "cloudfront" {
  bucket = var.origin_bucket_id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowCloudFrontOAI"
      Effect    = "Allow"
      Principal = {
        AWS = aws_cloudfront_origin_access_identity.main.iam_arn
      }
      Action   = "s3:GetObject"
      Resource = "${var.origin_bucket_arn}/*"
    }]
  })
}

resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  http_version        = "http2and3"

  aliases = local.has_custom_domain ? [var.domain_name] : []

  viewer_certificate {
    cloudfront_default_certificate = !local.has_custom_domain
    acm_certificate_arn            = local.has_custom_domain ? var.acm_certificate_arn : null
    ssl_support_method             = local.has_custom_domain ? "sni-only" : null
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  origin {
    domain_name = data.aws_s3_bucket.origin.bucket_regional_domain_name
    origin_id   = local.s3_origin_id

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.main.cloudfront_access_identity_path
    }
  }

  origin {
    domain_name = replace(var.api_origin_domain, "https://", "")
    origin_id   = local.api_origin_id

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = local.s3_origin_id

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 86400
    max_ttl                = 31536000
    compress               = true
  }

  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = local.api_origin_id

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type", "Accept"]
      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "https-only"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 300
  }

  tags = {
    Name = "trust-safety-cdn"
  }
}

data "aws_s3_bucket" "origin" {
  bucket = var.origin_bucket_id
}

output "distribution_id" {
  value = aws_cloudfront_distribution.main.id
}

output "domain_name" {
  value = aws_cloudfront_distribution.main.domain_name
}

output "arn" {
  value = aws_cloudfront_distribution.main.arn
}
