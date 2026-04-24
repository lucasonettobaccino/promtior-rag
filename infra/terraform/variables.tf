variable "aws_region" {
  description = "AWS region where all resources will be created."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Local AWS CLI profile to use for authentication. Defaults to null so Terraform uses AWS_PROFILE env var or the default credential chain."
  type        = string
  default     = null
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Short name used as prefix for all resources."
  type        = string
  default     = "promtior-rag"
}