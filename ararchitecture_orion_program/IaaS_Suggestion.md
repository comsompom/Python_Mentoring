it is a **Modular Infrastructure-as-Code (IaC)** structure. This approach uses a central `main.tf` 
that allows you to switch the target cloud provider by simply changing a variable or calling a different module.

Below is the **Terraform Strategy** and the code implementation.

---

### 1. The Project Structure
To support multi-cloud, organize your files like this:

```text
/edtech-modernization
├── variables.tf          # Global variables (Project name, Environment)
├── main.tf               # The entry point (Selects the cloud module)
├── /modules
│   ├── /azure            # The Azure implementation (Primary)
│   ├── /aws              # The AWS implementation
│   └── /gcp              # The GCP implementation
```

---

### 2. The Implementation Code

Here is the complete setup. You can save the "Azure" section into a file to deploy the primary solution, 
but I have provided the AWS and GCP mappings to demonstrate the cross-cloud capability.

#### A. Global Configuration (`variables.tf`)

```hcl
variable "cloud_provider" {
  description = "Target Cloud: azure, aws, or gcp"
  type        = string
  default     = "azure"
}

variable "project_name" {
  default = "edtech-core"
}

variable "environment" {
  default = "prod"
}

variable "location" {
  description = "Region (e.g., eastus, us-east-1)"
  default     = "eastus"
}
```

#### B. The Azure Module (`modules/azure/main.tf`)
*This is the core implementation of the "Architectural Design Document" tailored for EdTech Scale.*

```hcl
# ---------------------------------------------------------
# AZURE MODULE - The Primary Architecture
# ---------------------------------------------------------

resource "azurerm_resource_group" "rg" {
  name     = "${var.project_name}-rg"
  location = var.location
}

# 1. NETWORKING (VNet)
resource "azurerm_virtual_network" "vnet" {
  name                = "${var.project_name}-vnet"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = ["10.0.0.0/16"]
}

resource "azurerm_subnet" "aks_subnet" {
  name                 = "aks-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

# 2. COMPUTE - AKS (For Microservices & Grading Workers)
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "${var.project_name}-aks"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "${var.project_name}-k8s"

  default_node_pool {
    name       = "default"
    node_count = 3
    vm_size    = "Standard_D4s_v5" # Balanced CPU/Mem for General Workload
    
    # ELASTIC SCALING (Goal 1: Handle Exams)
    enable_auto_scaling = true
    min_count           = 3
    max_count           = 50
  }

  identity {
    type = "SystemAssigned"
  }
}

# 3. DATA - COSMOS DB (For Operational Data & Exam Results)
resource "azurerm_cosmosdb_account" "db" {
  name                = "${var.project_name}-cosmos"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level = "Session" # Best balance for User Sessions
  }

  # GEO-REDUNDANCY (Goal 2: High Availability)
  geo_location {
    location          = azurerm_resource_group.rg.location
    failover_priority = 0
  }
  
  # Enable Serverless if cost is priority, or Autoscale for performance
  capabilities {
    name = "EnableServerless"
  }
}

resource "azurerm_cosmosdb_sql_database" "main_db" {
  name                = "EdTechDB"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.db.name
}

# 4. EVENTING - SERVICE BUS (For CQRS Grading Pattern)
resource "azurerm_servicebus_namespace" "sb" {
  name                = "${var.project_name}-bus"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "Standard" # Required for Topics/Queues
}

resource "azurerm_servicebus_queue" "grading_queue" {
  name         = "grading-submission-queue"
  namespace_id = azurerm_servicebus_namespace.sb.id
  
  # Dead lettering for failed exams
  max_delivery_count = 5 
}

# 5. GATEWAY - API MANAGEMENT (BFF Pattern)
resource "azurerm_api_management" "apim" {
  name                = "${var.project_name}-apim"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  publisher_name      = "EdTech Co"
  publisher_email     = "admin@edtech.com"
  sku_name            = "Standard_1"
}

# 6. CACHING - REDIS (For reducing DB Load)
resource "azurerm_redis_cache" "redis" {
  name                = "${var.project_name}-redis"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  capacity            = 2
  family              = "C"
  sku_name            = "Standard"
}
```

---

#### C. The AWS Module Equivalent (`modules/aws/main.tf`)
*Implementing the same architecture using AWS Native services.*

```hcl
# ---------------------------------------------------------
# AWS MODULE - The Alternative Implementation
# ---------------------------------------------------------

# 1. COMPUTE - EKS (AKS Equivalent)
module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  cluster_name    = "${var.project_name}-eks"
  cluster_version = "1.27"
  
  eks_managed_node_groups = {
    main = {
      min_size     = 3
      max_size     = 50 # Elastic Scaling
      desired_size = 3
      instance_types = ["t3.large"]
    }
  }
}

# 2. DATA - DYNAMODB (Cosmos DB Equivalent)
resource "aws_dynamodb_table" "exam_table" {
  name         = "ExamSubmissions"
  billing_mode = "PAY_PER_REQUEST" # Handles "Thundering Herd" automatically
  hash_key     = "ExamID"
  range_key    = "StudentID"

  attribute {
    name = "ExamID"
    type = "S"
  }
  attribute {
    name = "StudentID"
    type = "S"
  }
}

# 3. EVENTING - SQS (Service Bus Equivalent for CQRS)
resource "aws_sqs_queue" "grading_queue" {
  name                      = "grading-submission-queue"
  message_retention_seconds = 86400
  
  # High throughput settings
  fifo_queue = false 
}

# 4. GATEWAY - API GATEWAY (APIM Equivalent)
resource "aws_apigatewayv2_api" "bff" {
  name          = "${var.project_name}-bff"
  protocol_type = "HTTP"
}
```

---

#### D. The Google Cloud Module Equivalent (`modules/gcp/main.tf`)
*Implementing the architecture using GCP Native services.*

```hcl
# ---------------------------------------------------------
# GCP MODULE - The Analytics/AI Focused Implementation
# ---------------------------------------------------------

# 1. COMPUTE - GKE (AKS Equivalent)
resource "google_container_cluster" "primary" {
  name     = "${var.project_name}-gke"
  location = var.location

  # Autopilot is best for "Hands-off" scaling
  enable_autopilot = true 
}

# 2. DATA - FIRESTORE (Cosmos DB Equivalent)
resource "google_firestore_database" "database" {
  name        = "(default)"
  location_id = var.location
  type        = "FIRESTORE_NATIVE"
}

# 3. EVENTING - PUB/SUB (Service Bus Equivalent)
resource "google_pubsub_topic" "grading_topic" {
  name = "grading-submissions"
}

resource "google_pubsub_subscription" "grading_sub" {
  name  = "grading-workers"
  topic = google_pubsub_topic.grading_topic.name
}

# 4. CACHING - MEMORYSTORE (Redis Equivalent)
resource "google_redis_instance" "cache" {
  name           = "${var.project_name}-redis"
  memory_size_gb = 1
}
```

---

### 3. How to Run This

To deploy this specifically for the **Azure Modernization** plan:

1.  Install Terraform and Azure CLI (`az login`).
2.  Create a file named `main.tf` in your root folder with the following content to invoke the Azure module:

```hcl
# root main.tf

provider "azurerm" {
  features {}
}

provider "aws" {
  region = "us-east-1"
}

provider "google" {
  project = "your-gcp-project-id"
  region  = "us-central1"
}

# LOGIC SWITCHER
module "edtech_infrastructure" {
  # Based on your variable, it loads the correct folder
  source = "./modules/${var.cloud_provider}"
  
  project_name = var.project_name
  location     = var.location
}
```

3.  **Run Command:**
    ```bash
    terraform init
    # To deploy Azure (Default)
    terraform apply -var="cloud_provider=azure"
    
    # To deploy AWS equivalent
    terraform apply -var="cloud_provider=aws"
    ```

### 4. Key Architectural Notes in Code

*   **Auto-Scaling:** In the Azure module, `enable_auto_scaling = true` and `max_count = 50` are the critical lines that solve the "Exam Day" crash.
*   **CQRS Enabler:** The `azurerm_servicebus_queue` is what physically separates the Student API (Write) from the Grading Worker (Read).
*   **Cost Optimization:** The `azurerm_cosmosdb_account` is set to `EnableServerless` (in capabilities) or standard provisioned. For a startup, Serverless is cheaper; for 5M students, standard with Autoscale is preferred.
