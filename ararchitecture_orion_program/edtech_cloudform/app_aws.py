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
