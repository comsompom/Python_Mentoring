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
