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
```
## B. The Azure Module (`modules/azure/variables.tf`)

```hcl
variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
}

variable "location" {
  description = "Azure region (e.g., eastus, westus2)"
  type        = string
}
```
---

#### C. The AWS Module Equivalent (`modules/aws/main.tf`)
*Implementing the same architecture using AWS Native services.*

```hcl
# ---------------------------------------------------------
# AWS MODULE - The Alternative Implementation
# ---------------------------------------------------------

# 0. VPC (Network Layer)
data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-private-subnet-${count.index + 1}"
    "kubernetes.io/role/internal-elb" = "1"
  }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 10}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
    "kubernetes.io/role/elb" = "1"
  }
}

resource "aws_eip" "nat" {
  count  = 2
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-nat-eip-${count.index + 1}"
  }
}

resource "aws_nat_gateway" "main" {
  count         = 2
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "${var.project_name}-nat-${count.index + 1}"
  }
}

resource "aws_route_table" "private" {
  count  = 2
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = {
    Name = "${var.project_name}-private-rt-${count.index + 1}"
  }
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# 1. COMPUTE - EKS (AKS Equivalent)
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "${var.project_name}-eks"
  cluster_version = "1.27"

  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.private[*].id

  eks_managed_node_groups = {
    main = {
      min_size     = 3
      max_size     = 50 # Elastic Scaling
      desired_size = 3
      instance_types = ["t3.large"]
      subnet_ids     = aws_subnet.private[*].id
    }
  }
}

# 2. DATA - DYNAMODB (Cosmos DB Equivalent)
resource "aws_dynamodb_table" "exam_table" {
  name         = "${var.project_name}-exam-submissions"
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

  tags = {
    Name = "${var.project_name}-exam-table"
  }
}

# 3. EVENTING - SQS (Service Bus Equivalent for CQRS)
resource "aws_sqs_queue" "grading_queue" {
  name                      = "${var.project_name}-grading-submission-queue"
  message_retention_seconds = 86400

  # High throughput settings
  fifo_queue = false

  tags = {
    Name = "${var.project_name}-grading-queue"
  }
}

# 4. CACHING - ELASTICACHE REDIS (For reducing DB Load)
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.project_name}-redis-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_security_group" "redis" {
  name        = "${var.project_name}-redis-sg"
  description = "Security group for Redis cache"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Redis from VPC"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-redis-sg"
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${var.project_name}-redis"
  description                = "Redis cache for ${var.project_name}"
  node_type                  = "cache.t3.micro"
  port                       = 6379
  parameter_group_name       = "default.redis7"
  num_cache_clusters         = 1
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  automatic_failover_enabled = false
  at_rest_encryption_enabled = true
  transit_encryption_enabled = false

  tags = {
    Name = "${var.project_name}-redis"
  }
}

# 5. GATEWAY - API GATEWAY (APIM Equivalent)
resource "aws_apigatewayv2_api" "bff" {
  name          = "${var.project_name}-bff"
  protocol_type = "HTTP"
  
  tags = {
    Name = "${var.project_name}-bff-api"
  }
}
```

## C. The AWS Module Equivalent (`modules/aws/variables.tf`)

```hcl
variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
}

variable "location" {
  description = "AWS region (e.g., us-east-1, us-west-2)"
  type        = string
}
```

---

#### D. The Google Cloud Module Equivalent (`modules/gcp/main.tf`)
*Implementing the architecture using GCP Native services.*

```hcl
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
```

## D. The Google Cloud Module Equivalent (`modules/gcp/variables.tf`)

```hcl
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
    App, Stack, RemovalPolicy, Duration, CfnOutput,
    aws_ec2 as ec2,
    aws_eks as eks,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_apigatewayv2 as apigw,
    aws_iam as iam,
    aws_elasticache as elasticache
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
            visibility_timeout=Duration.seconds(300)
        )

        # 5. ElastiCache Redis (Caching)
        # Security group for Redis
        redis_sg = ec2.SecurityGroup(self, "RedisSecurityGroup",
            vpc=vpc,
            description="Security group for Redis cache",
            allow_all_outbound=True
        )
        
        # Allow inbound Redis traffic from EKS cluster
        redis_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(6379),
            description="Allow Redis access from VPC"
        )

        # Subnet group for Redis
        subnet_group = elasticache.CfnSubnetGroup(self, "RedisSubnetGroup",
            description="Subnet group for Redis cache",
            subnet_ids=[subnet.subnet_id for subnet in vpc.private_subnets],
            cache_subnet_group_name="edtech-redis-subnet-group"
        )

        # Redis cluster for caching
        redis = elasticache.CfnCacheCluster(self, "RedisCache",
            cache_node_type="cache.t3.micro",
            engine="redis",
            num_cache_nodes=1,
            cache_subnet_group_name=subnet_group.cache_subnet_group_name,
            vpc_security_group_ids=[redis_sg.security_group_id]
        )

        # 6. API Gateway (BFF Pattern)
        # Simplified HTTP API entry point
        api = apigw.HttpApi(self, "EdTechBFF",
            api_name="edtech-bff-api"
        )

        # Output the API Endpoint
        CfnOutput(self, "BFFEndpoint", value=api.api_endpoint)

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
    Subnet,
    KubernetesCluster,
    KubernetesClusterDefaultNodePool,
    CosmosdbAccount,
    CosmosdbSqlDatabase,
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

        # 0.5. Virtual Network
        vnet = VirtualNetwork(self, "vnet",
            name="edtech-vnet",
            location=rg.location,
            resource_group_name=rg.name,
            address_space=["10.0.0.0/16"]
        )

        # Subnet for AKS
        aks_subnet = Subnet(self, "aks_subnet",
            name="aks-subnet",
            resource_group_name=rg.name,
            virtual_network_name=vnet.name,
            address_prefixes=["10.0.1.0/24"]
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
            geo_location=[{"location": rg.location, "failover_priority": 0}],
            consistency_policy={"consistency_level": "Session"},
            capabilities=[{"name": "EnableServerless"}]
        )

        # Cosmos DB Database
        cosmos_db = CosmosdbSqlDatabase(self, "cosmos_db",
            name="EdTechDB",
            resource_group_name=rg.name,
            account_name=cosmos.name
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
    PubsubSubscription,
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
            project=project_id,
            auto_create_subnetworks=True
        )

        # 2. GKE Autopilot (Compute)
        # Autopilot handles node provisioning automatically
        # This is ideal for the "Exam Day" scaling requirement
        gke = ContainerCluster(self, "gke",
            name="edtech-autopilot-cluster",
            project=project_id,
            location=region,
            network=network.name,
            enable_autopilot=True # The magic switch for scaling
        )

        # 3. Firestore (Data)
        # Native mode for real-time updates (Student Feedback Loop)
        firestore = FirestoreDatabase(self, "firestore",
            name="(default)",
            project=project_id,
            location_id=region,
            type="FIRESTORE_NATIVE"
        )

        # 4. Pub/Sub (CQRS Messaging)
        topic = PubsubTopic(self, "grading_topic",
            name="exam-submissions-topic",
            project=project_id
        )

        subscription = PubsubSubscription(self, "grading_subscription",
            name="grading-workers",
            topic=topic.name,
            project=project_id
        )

        # 5. Cloud Memorystore (Redis)
        redis = RedisInstance(self, "redis",
            name="edtech-cache",
            project=project_id,
            memory_size_gb=1,
            region=region,
            tier="BASIC"
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

