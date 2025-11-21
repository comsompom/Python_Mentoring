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
