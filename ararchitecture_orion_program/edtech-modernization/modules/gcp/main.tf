# ---------------------------------------------------------
# GCP MODULE - The Analytics/AI Focused Implementation
# ---------------------------------------------------------

locals {
  project_id = var.gcp_project_id != "" ? var.gcp_project_id : "your-gcp-project-id"
}

# 0. NETWORK
resource "google_compute_network" "vpc" {
  name                    = "${var.project_name}-vpc"
  auto_create_subnetworks = true
  project                 = local.project_id
}

# 1. COMPUTE - GKE (AKS Equivalent)
resource "google_container_cluster" "primary" {
  name     = "${var.project_name}-gke"
  location = var.location
  project  = local.project_id

  # Autopilot is best for "Hands-off" scaling
  enable_autopilot = true

  network    = google_compute_network.vpc.name
  subnetwork = null # Autopilot manages subnets

  deletion_protection = false
}

# 2. DATA - FIRESTORE (Cosmos DB Equivalent)
resource "google_firestore_database" "database" {
  name        = "(default)"
  location_id = var.location
  type        = "FIRESTORE_NATIVE"
  project     = local.project_id
}

# 3. EVENTING - PUB/SUB (Service Bus Equivalent)
resource "google_pubsub_topic" "grading_topic" {
  name    = "${var.project_name}-grading-submissions"
  project = local.project_id
}

resource "google_pubsub_subscription" "grading_sub" {
  name    = "${var.project_name}-grading-workers"
  topic   = google_pubsub_topic.grading_topic.name
  project = local.project_id
}

# 4. CACHING - MEMORYSTORE (Redis Equivalent)
resource "google_redis_instance" "cache" {
  name           = "${var.project_name}-redis"
  memory_size_gb = 1
  region         = var.location
  project        = local.project_id
  tier           = "BASIC"
  
  authorized_network = google_compute_network.vpc.id
}