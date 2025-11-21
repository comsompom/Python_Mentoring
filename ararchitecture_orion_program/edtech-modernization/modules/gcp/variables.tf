variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
}

variable "location" {
  description = "GCP region (e.g., us-central1, us-east1)"
  type        = string
}

variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
  default     = ""
}

