# =============================================================================
# Enthropy Trading Platform - Terraform Variables
# =============================================================================

# -----------------------------------------------------------------------------
# General
# -----------------------------------------------------------------------------
variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "aws_region" {
  description = "Primary AWS region for deployment"
  type        = string
  default     = "ap-southeast-1"
}

# -----------------------------------------------------------------------------
# VPC
# -----------------------------------------------------------------------------
variable "vpc_cidr" {
  description = "CIDR block for the primary VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

# -----------------------------------------------------------------------------
# Jakarta Region VPC
# -----------------------------------------------------------------------------
variable "jakarta_vpc_cidr" {
  description = "CIDR block for Jakarta region VPC"
  type        = string
  default     = "10.1.0.0/16"
}

variable "jakarta_private_subnet_cidrs" {
  description = "CIDR blocks for Jakarta private subnets"
  type        = list(string)
  default     = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]
}

variable "jakarta_public_subnet_cidrs" {
  description = "CIDR blocks for Jakarta public subnets"
  type        = list(string)
  default     = ["10.1.101.0/24", "10.1.102.0/24", "10.1.103.0/24"]
}

# -----------------------------------------------------------------------------
# EKS
# -----------------------------------------------------------------------------
variable "eks_cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.28"
}

variable "eks_general_instance_types" {
  description = "Instance types for general EKS node group"
  type        = list(string)
  default     = ["t3.large", "t3.xlarge"]
}

variable "eks_general_min_size" {
  description = "Minimum number of nodes in general node group"
  type        = number
  default     = 2
}

variable "eks_general_max_size" {
  description = "Maximum number of nodes in general node group"
  type        = number
  default     = 10
}

variable "eks_general_desired_size" {
  description = "Desired number of nodes in general node group"
  type        = number
  default     = 3
}

variable "eks_compute_instance_types" {
  description = "Instance types for compute-intensive EKS node group"
  type        = list(string)
  default     = ["c5.2xlarge", "c5.4xlarge"]
}

variable "eks_compute_min_size" {
  description = "Minimum number of nodes in compute node group"
  type        = number
  default     = 0
}

variable "eks_compute_max_size" {
  description = "Maximum number of nodes in compute node group"
  type        = number
  default     = 20
}

variable "eks_compute_desired_size" {
  description = "Desired number of nodes in compute node group"
  type        = number
  default     = 2
}

# -----------------------------------------------------------------------------
# RDS PostgreSQL
# -----------------------------------------------------------------------------
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "rds_allocated_storage" {
  description = "Allocated storage in GB for RDS"
  type        = number
  default     = 100
}

variable "rds_max_allocated_storage" {
  description = "Maximum allocated storage in GB for RDS autoscaling"
  type        = number
  default     = 500
}

# -----------------------------------------------------------------------------
# ElastiCache Redis
# -----------------------------------------------------------------------------
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.r6g.large"
}

variable "redis_auth_token" {
  description = "Auth token for Redis (must be at least 16 characters)"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.redis_auth_token) >= 16
    error_message = "Redis auth token must be at least 16 characters."
  }
}
