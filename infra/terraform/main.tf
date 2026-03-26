# =============================================================================
# Pyhron Trading Platform - Terraform Infrastructure
# =============================================================================
# Usage:
#   terraform init
#   terraform plan -var-file="environments/production.tfvars"
#   terraform apply -var-file="environments/production.tfvars"
# =============================================================================

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
  }

  backend "s3" {
    bucket         = "pyhron-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "ap-southeast-1"
    encrypt        = true
    dynamodb_table = "pyhron-terraform-locks"
  }
}

# =============================================================================
# Provider Configuration
# =============================================================================
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "pyhron"
      Environment = var.environment
      ManagedBy   = "terraform"
      Team        = "platform-engineering"
    }
  }
}

provider "aws" {
  alias  = "jakarta"
  region = "ap-southeast-3"

  default_tags {
    tags = {
      Project     = "pyhron"
      Environment = var.environment
      ManagedBy   = "terraform"
      Team        = "platform-engineering"
      Region      = "jakarta"
    }
  }
}

# =============================================================================
# Data Sources
# =============================================================================
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# =============================================================================
# VPC
# =============================================================================
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.4"

  name = "pyhron-${var.environment}-vpc"
  cidr = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs

  enable_nat_gateway     = true
  single_nat_gateway     = var.environment != "production"
  one_nat_gateway_per_az = var.environment == "production"

  enable_dns_hostnames = true
  enable_dns_support   = true

  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_iam_role             = true
  flow_log_max_aggregation_interval    = 60

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
    Type                     = "public"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
    Type                              = "private"
  }

  tags = {
    Component = "networking"
  }
}

# =============================================================================
# EKS Cluster
# =============================================================================
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.21"

  cluster_name    = "pyhron-${var.environment}"
  cluster_version = var.eks_cluster_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access  = var.environment != "production"
  cluster_endpoint_private_access = true

  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  eks_managed_node_groups = {
    general = {
      name           = "pyhron-general"
      instance_types = var.eks_general_instance_types
      capacity_type  = "ON_DEMAND"

      min_size     = var.eks_general_min_size
      max_size     = var.eks_general_max_size
      desired_size = var.eks_general_desired_size

      labels = {
        workload = "general"
      }
    }

    compute = {
      name           = "pyhron-compute"
      instance_types = var.eks_compute_instance_types
      capacity_type  = var.environment == "production" ? "ON_DEMAND" : "SPOT"

      min_size     = var.eks_compute_min_size
      max_size     = var.eks_compute_max_size
      desired_size = var.eks_compute_desired_size

      labels = {
        workload = "compute-intensive"
      }

      taints = {
        compute = {
          key    = "workload"
          value  = "compute"
          effect = "NO_SCHEDULE"
        }
      }
    }
  }

  manage_aws_auth_configmap = true

  tags = {
    Component = "compute"
  }
}

# =============================================================================
# RDS PostgreSQL
# =============================================================================
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.3"

  identifier = "pyhron-${var.environment}"

  engine               = "postgres"
  engine_version       = "16.1"
  family               = "postgres16"
  major_engine_version = "16"
  instance_class       = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage

  db_name  = "pyhron"
  username = "pyhron_admin"
  port     = 5432

  multi_az               = var.environment == "production"
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]
  create_db_subnet_group = false

  maintenance_window      = "Mon:03:00-Mon:04:00"
  backup_window           = "01:00-02:00"
  backup_retention_period = var.environment == "production" ? 30 : 7

  deletion_protection = var.environment == "production"
  skip_final_snapshot = var.environment != "production"

  performance_insights_enabled    = true
  monitoring_interval             = 60
  create_monitoring_role          = true
  monitoring_role_name            = "pyhron-rds-monitoring-${var.environment}"
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  storage_encrypted = true

  parameters = [
    {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements,auto_explain"
    },
    {
      name  = "log_min_duration_statement"
      value = "1000"
    },
    {
      name  = "max_connections"
      value = "200"
    }
  ]

  tags = {
    Component = "database"
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "pyhron-rds-${var.environment}-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.cluster_security_group_id]
    description     = "PostgreSQL access from EKS"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "pyhron-rds-${var.environment}"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# =============================================================================
# ElastiCache Redis
# =============================================================================
resource "aws_elasticache_subnet_group" "redis" {
  name       = "pyhron-redis-${var.environment}"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "redis" {
  name_prefix = "pyhron-redis-${var.environment}-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.cluster_security_group_id]
    description     = "Redis access from EKS"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "pyhron-redis-${var.environment}"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "pyhron-${var.environment}"
  description          = "Pyhron Redis cluster - ${var.environment}"

  node_type            = var.redis_node_type
  num_cache_clusters   = var.environment == "production" ? 3 : 1
  port                 = 6379
  parameter_group_name = "default.redis7"
  engine_version       = "7.0"

  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.redis_auth_token

  automatic_failover_enabled = var.environment == "production"
  multi_az_enabled           = var.environment == "production"

  snapshot_retention_limit = var.environment == "production" ? 7 : 1
  snapshot_window          = "02:00-03:00"
  maintenance_window       = "mon:03:00-mon:04:00"

  tags = {
    Component = "cache"
  }
}

# =============================================================================
# S3 Buckets - Backups & Artifacts
# =============================================================================
resource "aws_s3_bucket" "backups" {
  bucket = "pyhron-backups-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Component = "storage"
    Purpose   = "backups"
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "archive-old-backups"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = "pyhron-mlflow-artifacts-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Component = "storage"
    Purpose   = "ml-artifacts"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# Jakarta Region Module (ap-southeast-3)
# =============================================================================
module "jakarta_vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.4"

  providers = {
    aws = aws.jakarta
  }

  name = "pyhron-${var.environment}-jakarta-vpc"
  cidr = var.jakarta_vpc_cidr

  azs             = ["ap-southeast-3a", "ap-southeast-3b", "ap-southeast-3c"]
  private_subnets = var.jakarta_private_subnet_cidrs
  public_subnets  = var.jakarta_public_subnet_cidrs

  enable_nat_gateway     = true
  single_nat_gateway     = true
  enable_dns_hostnames   = true
  enable_dns_support     = true

  tags = {
    Component = "networking"
    Region    = "jakarta"
  }
}

resource "aws_s3_bucket" "jakarta_backups" {
  provider = aws.jakarta
  bucket   = "pyhron-backups-jakarta-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Component = "storage"
    Purpose   = "regional-backups"
    Region    = "jakarta"
  }
}

resource "aws_s3_bucket_versioning" "jakarta_backups" {
  provider = aws.jakarta
  bucket   = aws_s3_bucket.jakarta_backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "jakarta_backups" {
  provider = aws.jakarta
  bucket   = aws_s3_bucket.jakarta_backups.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "jakarta_backups" {
  provider = aws.jakarta
  bucket   = aws_s3_bucket.jakarta_backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# Outputs
# =============================================================================
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.db_instance_endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive   = true
}

output "backup_bucket_name" {
  description = "S3 backup bucket name"
  value       = aws_s3_bucket.backups.id
}

output "jakarta_vpc_id" {
  description = "Jakarta VPC ID"
  value       = module.jakarta_vpc.vpc_id
}
