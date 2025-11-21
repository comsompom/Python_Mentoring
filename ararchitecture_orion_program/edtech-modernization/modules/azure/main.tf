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
    name                = "default"
    node_count          = 3
    vm_size             = "Standard_D4s_v5" # Balanced CPU/Mem for General Workload
    vnet_subnet_id      = azurerm_subnet.aks_subnet.id

    # ELASTIC SCALING (Goal 1: Handle Exams)
    enable_auto_scaling = true
    min_count          = 3
    max_count          = 50
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
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

  # Enable Serverless for cost efficiency
  capabilities {
    name = "EnableServerless"
  }
  
  # Note: Serverless and Autoscale are mutually exclusive
  # Use Serverless for variable workloads, or remove this capability to use Autoscale
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
