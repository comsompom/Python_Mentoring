# Technical Implementation: Terraform Strategy

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

Here is the complete setup. You can save the "Azure" section into a file to deploy the primary solution, but I have provided the AWS and GCP mappings to demonstrate the cross-cloud capability.

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


### 5. Use the Cloud Formation Overall Description

This is a technical request with a specific nuance. **CloudFormation** is a tool proprietary to **AWS**. You cannot strictly use CloudFormation to deploy resources to Azure or Google Cloud.

To fulfill your requirement for **Python-based Infrastructure as Code (IaC)** that feels like CloudFormation but works across clouds, the industry standard approach is:

1.  **AWS:** Use **AWS CDK (Cloud Development Kit)**. This allows you to write Python that *synthesizes* into CloudFormation templates.
2.  **Azure & GCP:** Since CloudFormation won't work, we will use **CDKTF (Cloud Development Kit for Terraform)**. This allows you to write the exact same style of Python code, but it synthesizes into Terraform JSON instead of CloudFormation.

Here is the implementation split into three separate Python projects.

---

### Cloud Formation: AWS Implementation
**Tool:** AWS CDK (Python)
**Output:** CloudFormation Template

This code deploys the **EKS (Compute)**, **DynamoDB (CQRS Storage)**, **SQS (Event Bus)**, and **API Gateway**.

## File: `app_aws.py`

```python
from aws_cdk import (
    App, Stack, RemovalPolicy,
    aws_ec2 as ec2,
    aws_eks as eks,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_apigatewayv2 as apigw,
    aws_iam as iam
)
from constructs import Construct

class EdTechAWSStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. VPC (Network Layer)
        vpc = ec2.Vpc(self, "EdTechVPC", max_azs=3)

        # 2. EKS Cluster (Compute / Grading Workers)
        cluster = eks.Cluster(self, "EdTechEKS",
            vpc=vpc,
            default_capacity=0,  # We manage node groups explicitly
            version=eks.KubernetesVersion.V1_27,
            cluster_name="edtech-scale-cluster"
        )

        # Elastic Scaling Node Group (The "Exam Day" logic)
        cluster.add_nodegroup_capacity("GradingNodeGroup",
            instance_types=[ec2.InstanceType("t3.medium")],
            min_size=3,
            max_size=50, # Scale up to 50 nodes for exams
            desired_size=3
        )

        # 3. DynamoDB (CQRS Write Store)
        # Using On-Demand billing for "Thundering Herd" spikes
        table = dynamodb.Table(self, "ExamSubmissions",
            partition_key=dynamodb.Attribute(name="exam_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="student_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # 4. SQS Queue (CQRS Event Bus)
        queue = sqs.Queue(self, "GradingQueue",
            queue_name="exam-submission-queue",
            visibility_timeout=cdk.Duration.seconds(300)
        )

        # 5. API Gateway (BFF Pattern)
        # Simplified HTTP API entry point
        api = apigw.HttpApi(self, "EdTechBFF",
            api_name="edtech-bff-api"
        )

        # Output the API Endpoint
        cdk.CfnOutput(self, "BFFEndpoint", value=api.api_endpoint)

app = App()
EdTechAWSStack(app, "EdTech-AWS-Prod")
app.synth()
```

---

### Cloud Formation: Azure Implementation
**Tool:** CDKTF (Python) -> Uses Terraform providers
**Output:** Terraform JSON

This mimics the CloudFormation style but targets Azure Resource Manager. It deploys **AKS**, **Cosmos DB**, **Service Bus**, and **Redis**.

## File: `main_azure.py`

```python
from constructs import Construct
from cdktf import App, TerraformStack, TerraformOutput
from imports.azurerm import (
    ResourceGroup,
    VirtualNetwork,
    KubernetesCluster,
    KubernetesClusterDefaultNodePool,
    CosmosdbAccount,
    ServicebusNamespace,
    ServicebusQueue,
    RedisCache
)

class EdTechAzureStack(TerraformStack):
    def __init__(self, scope: Construct, ns: str):
        super().__init__(scope, ns)

        # 0. Resource Group
        rg = ResourceGroup(self, "rg",
            name="edtech-rg",
            location="East US"
        )

        # 1. AKS (Compute)
        # Defining the Auto-scaling logic for exams
        aks = KubernetesCluster(self, "aks",
            name="edtech-aks",
            location=rg.location,
            resource_group_name=rg.name,
            dns_prefix="edtech-k8s",
            default_node_pool=KubernetesClusterDefaultNodePool(
                name="default",
                node_count=3,
                vm_size="Standard_D2_v2",
                enable_auto_scaling=True,
                min_count=3,
                max_count=50 # Scale limit
            ),
            identity={"type": "SystemAssigned"}
        )

        # 2. Cosmos DB (NoSQL Data)
        cosmos = CosmosdbAccount(self, "cosmos",
            name="edtech-global-db",
            location=rg.location,
            resource_group_name=rg.name,
            offer_type="Standard",
            kind="GlobalDocumentDB",
            geo_location=[{"location": rg.location, "failoverPriority": 0}],
            consistency_policy={"consistencyLevel": "Session"}
        )

        # 3. Service Bus (CQRS Messaging)
        sb = ServicebusNamespace(self, "sb",
            name="edtech-bus",
            location=rg.location,
            resource_group_name=rg.name,
            sku="Standard"
        )

        queue = ServicebusQueue(self, "queue",
            name="grading_submissions",
            namespace_id=sb.id
        )

        # 4. Redis (Caching)
        redis = RedisCache(self, "redis",
            name="edtech-cache",
            location=rg.location,
            resource_group_name=rg.name,
            capacity=2,
            family="C",
            sku_name="Standard"
        )

        TerraformOutput(self, "aks_name", value=aks.name)

app = App()
EdTechAzureStack(app, "EdTech-Azure-Prod")
app.synth()
```

---

### Cloud Formation: Google Cloud Implementation
**Tool:** CDKTF (Python) -> Uses Terraform providers
**Output:** Terraform JSON

This deploys **GKE Autopilot** (best for scaling), **Firestore**, and **Pub/Sub**.

## File: `main_gcp.py`

```python
from constructs import Construct
from cdktf import App, TerraformStack
from imports.google import (
    ComputeNetwork,
    ContainerCluster,
    PubsubTopic,
    FirestoreDatabase,
    RedisInstance
)

class EdTechGCPStack(TerraformStack):
    def __init__(self, scope: Construct, ns: str):
        super().__init__(scope, ns)

        project_id = "edtech-production"
        region = "us-central1"

        # 1. Network
        network = ComputeNetwork(self, "vpc",
            name="edtech-vpc",
            auto_create_subnetworks=True
        )

        # 2. GKE Autopilot (Compute)
        # Autopilot handles node provisioning automatically
        # This is ideal for the "Exam Day" scaling requirement
        gke = ContainerCluster(self, "gke",
            name="edtech-autopilot-cluster",
            location=region,
            network=network.name,
            enable_autopilot=True # The magic switch for scaling
        )

        # 3. Firestore (Data)
        # Native mode for real-time updates (Student Feedback Loop)
        firestore = FirestoreDatabase(self, "firestore",
            name="(default)",
            location_id=region,
            type="FIRESTORE_NATIVE"
        )

        # 4. Pub/Sub (CQRS Messaging)
        topic = PubsubTopic(self, "grading_topic",
            name="exam-submissions-topic"
        )

        # 5. Cloud Memorystore (Redis)
        redis = RedisInstance(self, "redis",
            name="edtech-cache",
            memory_size_gb=1,
            region=region
        )

app = App()
EdTechGCPStack(app, "EdTech-GCP-Prod")
app.synth()
```

---

### How to Deploy Cloud Formation:

Since these use Python to generate the infrastructure definitions, the workflow is slightly different for AWS vs the others.

#### For AWS (Part 1):
1.  Install AWS CDK: `npm install -g aws-cdk`
2.  Install Python dependencies: `pip install aws-cdk-lib constructs`
3.  Run: `cdk deploy`
    *   *This compiles Python directly to CloudFormation and deploys it to AWS.*

#### For Azure & GCP (Parts 2 & 3):
1.  Install CDKTF: `npm install -g cdktf-cli`
2.  Install Python dependencies: `pip install cdktf cdktf-cdktf-provider-azurerm cdktf-cdktf-provider-google`
3.  Run: `cdktf deploy`
    *   *This compiles Python to Terraform JSON and uses Terraform to deploy to Azure/GCP.*

