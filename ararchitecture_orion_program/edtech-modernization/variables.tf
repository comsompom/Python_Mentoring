variable "cloud_provider" {
  description = "Target Cloud: azure, aws, or gcp"
  type        = string
  default     = "azure"
  
  validation {
    condition     = contains(["azure", "aws", "gcp"], var.cloud_provider)
    error_message = "cloud_provider must be one of: azure, aws, gcp"
  }
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "edtech-core"
}

variable "environment" {
  description = "Environment name (e.g., prod, dev, staging)"
  type        = string
  default     = "prod"
}

variable "location" {
  description = "Region (e.g., eastus, us-east-1, us-central1)"
  type        = string
  default     = "eastus"
}

variable "gcp_project_id" {
  description = "GCP Project ID (required when cloud_provider is gcp)"
  type        = string
  default     = ""
}
