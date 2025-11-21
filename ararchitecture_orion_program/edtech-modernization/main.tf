# root main.tf

provider "azurerm" {
  features {}
}

provider "aws" {
  region = "us-east-1"
}

provider "google" {
  project = var.gcp_project_id != "" ? var.gcp_project_id : "your-gcp-project-id"
  region  = var.location
}

# LOGIC SWITCHER
module "edtech_infrastructure" {
  # Based on your variable, it loads the correct folder
  source = "./modules/${var.cloud_provider}"

  project_name = var.project_name
  location     = var.location
  
  # GCP-specific variable
  gcp_project_id = var.gcp_project_id
}
