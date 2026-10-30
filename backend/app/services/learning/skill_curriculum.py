from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class RoadmapStage(BaseModel):
    stage_id: str
    title: str
    description: str
    concepts: List[str]
    estimated_hours: float
    is_completed: bool = False


class PracticalExercise(BaseModel):
    id: str
    title: str
    instruction: str
    is_completed: bool = False


class SkillCurriculum(BaseModel):
    skill_name: str
    category: str
    prerequisites: List[str]
    stages: List[RoadmapStage]
    practical_exercises: List[PracticalExercise]


SKILL_CURRICULUM_CATALOG: Dict[str, Dict[str, Any]] = {
    "docker": {
        "skill_name": "Docker",
        "category": "DevOps & Containers",
        "prerequisites": ["Linux CLI Basics", "Networking Fundamentals"],
        "stages": [
            {
                "stage_id": "fundamentals",
                "title": "Stage 1: Container Fundamentals & Architecture",
                "description": "Understand container isolation vs virtual machines, the Docker daemon, images, and layers.",
                "concepts": [
                    "Container namespace and cgroup isolation",
                    "Docker Engine and CLI architecture",
                    "Base images, tags, and immutable image layers",
                    "Core Dockerfile directives (FROM, RUN, COPY, CMD, ENTRYPOINT)"
                ],
                "estimated_hours": 4.0
            },
            {
                "stage_id": "intermediate",
                "title": "Stage 2: Storage, Networking & Compose",
                "description": "Manage multi-container compositions, persistent data volumes, and internal network bridges.",
                "concepts": [
                    "Volumes and bind mounts for database persistence",
                    "Bridge and host networks, container DNS resolution",
                    "Multi-container topology with Docker Compose",
                    "Environment variable injection and .env file handling"
                ],
                "estimated_hours": 5.0
            },
            {
                "stage_id": "practical",
                "title": "Stage 3: Multi-Stage Production Builds & CI/CD",
                "description": "Build slim, production-grade container images with multi-stage builds and automated CI pipelines.",
                "concepts": [
                    "Multi-stage Dockerfile patterns for compiled and interpreted runtimes",
                    "Image size reduction (<100MB) via alpine and distroless bases",
                    "Non-root security execution (USER directive)",
                    "GitHub Actions workflow building and publishing containers"
                ],
                "estimated_hours": 5.0
            },
            {
                "stage_id": "advanced",
                "title": "Stage 4: Security, Observability & Container Governance",
                "description": "Harden container runtimes, inspect image vulnerability CVEs, and configure health checks.",
                "concepts": [
                    "Trivy vulnerability and secret scanning",
                    "HEALTHCHECK directives and container lifecycle restarts",
                    "Resource limits (CPU, memory cgroups)",
                    "BuildKit cache mounts and secrets management"
                ],
                "estimated_hours": 4.0
            }
        ],
        "practical_exercises": [
            {
                "id": "ex-docker-1",
                "title": "Multi-Stage Distroless Build",
                "instruction": "Create a multi-stage Dockerfile that builds a backend service and copies only the runtime artifacts into a non-root distroless container image under 80MB."
            },
            {
                "id": "ex-docker-2",
                "title": "Resilient Docker Compose Topology",
                "instruction": "Write a docker-compose.yml file configuring a web API, PostgreSQL database, and Redis cache with health checks, depends_on conditions, and volume persistence."
            },
            {
                "id": "ex-docker-3",
                "title": "Automated Security Scanning",
                "instruction": "Run a Trivy vulnerability scan against your built container image and remediate all High and Critical CVE vulnerabilities."
            }
        ]
    },
    "fastapi": {
        "skill_name": "FastAPI",
        "category": "Backend Framework",
        "prerequisites": ["Python 3 Basics", "Type Annotations", "HTTP/REST Fundamentals"],
        "stages": [
            {
                "stage_id": "fundamentals",
                "title": "Stage 1: Async API Basics & Pydantic Schemas",
                "description": "Master non-blocking asynchronous request handlers and automatic input validation with Pydantic v2.",
                "concepts": [
                    "ASGI specification, Starlette foundation, and Uvicorn server",
                    "Path and query parameters with Pydantic field validation",
                    "Response models, status codes, and OpenAPI / Swagger documentation",
                    "Async/await execution semantics and threadpool offloading"
                ],
                "estimated_hours": 4.0
            },
            {
                "stage_id": "intermediate",
                "title": "Stage 2: Dependency Injection & Database Integration",
                "description": "Architect clean, maintainable microservices using FastAPI's hierarchical dependency injection.",
                "concepts": [
                    "FastAPI Depends pattern for database sessions and auth contexts",
                    "SQLAlchemy 2.0 AsyncSession integration",
                    "Custom middleware for request IDs and structured logging",
                    "Centralized error handling with HTTPException and exception handlers"
                ],
                "estimated_hours": 5.0
            },
            {
                "stage_id": "practical",
                "title": "Stage 3: Authentication, Security & Background Tasks",
                "description": "Implement enterprise OAuth2 security, password hashing, and non-blocking background workers.",
                "concepts": [
                    "OAuth2 Password Bearer flow with JWT access tokens",
                    "Bcrypt password hashing and user authorization",
                    "FastAPI BackgroundTasks for asynchronous email and logging jobs",
                    "CORS configuration and security headers"
                ],
                "estimated_hours": 4.0
            },
            {
                "stage_id": "advanced",
                "title": "Stage 4: High-Throughput Production Optimization & Testing",
                "description": "Test and tune FastAPI services for high-throughput, low-latency production workloads.",
                "concepts": [
                    "Pytest with AsyncClient and in-memory test databases",
                    "Connection pooling optimization and async redis caching",
                    "Streaming responses and WebSockets for real-time telemetry",
                    "Gunicorn with Uvicorn workers process management"
                ],
                "estimated_hours": 4.0
            }
        ],
        "practical_exercises": [
            {
                "id": "ex-fastapi-1",
                "title": "CRUD API with Pydantic Validation",
                "instruction": "Implement a full RESTful CRUD resource with strict Pydantic request and response schemas, returning HTTP 404, 422, and 201 appropriately."
            },
            {
                "id": "ex-fastapi-2",
                "title": "JWT Authentication Dependency",
                "instruction": "Create a reusable `get_current_active_user` dependency that parses Authorization Bearer tokens, validates signatures, and injects the user model."
            },
            {
                "id": "ex-fastapi-3",
                "title": "Asynchronous Integration Testing",
                "instruction": "Write an asynchronous pytest suite using httpx.AsyncClient verifying that your endpoints handle concurrent requests without database session collisions."
            }
        ]
    },
    "python": {
        "skill_name": "Python",
        "category": "Programming Language",
        "prerequisites": ["Basic Computer Literacy", "Command Line Basics"],
        "stages": [
            {
                "stage_id": "fundamentals",
                "title": "Stage 1: Core Syntax, Data Structures & Control Flow",
                "description": "Master Python fundamentals, builtin collections, and idiomatic coding practices.",
                "concepts": [
                    "Variables, dynamic typing, and operator semantics",
                    "Lists, dictionaries, sets, and tuples time-complexity",
                    "Functions, scope, *args, **kwargs, and return semantics",
                    "Exception handling with try/except/finally and custom exceptions"
                ],
                "estimated_hours": 4.0
            },
            {
                "stage_id": "intermediate",
                "title": "Stage 2: Object-Oriented & Functional Patterns",
                "description": "Build modular code with OOP, dunder methods, generators, and decorators.",
                "concepts": [
                    "Classes, inheritance, polymorphism, and composition",
                    "Special dunder methods (__str__, __repr__, __eq__, __iter__)",
                    "List/dict comprehensions and generator expressions",
                    "Custom function decorators and context managers (with statement)"
                ],
                "estimated_hours": 5.0
            },
            {
                "stage_id": "practical",
                "title": "Stage 3: Asynchronous Programming & Type Hints",
                "description": "Write modern, statically checked Python with typing and asyncio.",
                "concepts": [
                    "PEP 484 Type hints, Generic types, Union, Optional, Protocol",
                    "MyPy static type checking",
                    "Asyncio event loop, coroutines, Tasks, and asyncio.gather",
                    "File I/O, JSON serialization, and pathlib"
                ],
                "estimated_hours": 5.0
            },
            {
                "stage_id": "advanced",
                "title": "Stage 4: Packaging, Testing & Performance Profiling",
                "description": "Package production libraries and optimize execution speed.",
                "concepts": [
                    "Pytest fixtures, parameterization, and mocking",
                    "cProfile and memory profiling for bottleneck elimination",
                    "Packaging with pyproject.toml and virtual environment management",
                    "Concurrency vs Parallelism: threading, multiprocessing, and GIL"
                ],
                "estimated_hours": 4.0
            }
        ],
        "practical_exercises": [
            {
                "id": "ex-py-1",
                "title": "Custom Context Manager & Decorator",
                "instruction": "Implement a `@timed` execution decorator and a database transaction context manager handling automatic rollback on exceptions."
            },
            {
                "id": "ex-py-2",
                "title": "Asynchronous Batch Data Processor",
                "instruction": "Write an asyncio pipeline that concurrently fetches or processes 50 records with an asyncio.Semaphore(5) concurrency limiter."
            },
            {
                "id": "ex-py-3",
                "title": "Strict Type-Checked Module",
                "instruction": "Define a domain model with Python dataclasses and Protocols that passes `mypy --strict` with zero typing errors."
            }
        ]
    },
    "postgresql": {
        "skill_name": "PostgreSQL",
        "category": "Databases & Storage",
        "prerequisites": ["Basic SQL Understanding", "Relational Concepts"],
        "stages": [
            {
                "stage_id": "fundamentals",
                "title": "Stage 1: Relational Modeling & Schema Design",
                "description": "Design normalized database schemas with constraints and foreign keys.",
                "concepts": [
                    "Data types (UUID, TEXT, TIMESTAMP WITH TIME ZONE, JSONB)",
                    "Primary keys, foreign keys, and referential integrity constraints",
                    "Normalization (1NF to 3NF) vs pragmatic denormalization",
                    "DDL statements, ALTER TABLE, and schema migrations with Alembic"
                ],
                "estimated_hours": 4.0
            },
            {
                "stage_id": "intermediate",
                "title": "Stage 2: Advanced Querying, Joins & Aggregations",
                "description": "Write high-performance SQL queries for complex reporting and analytics.",
                "concepts": [
                    "INNER, LEFT, RIGHT, and FULL OUTER joins",
                    "Common Table Expressions (WITH queries) and subqueries",
                    "Window functions (ROW_NUMBER, RANK, LAG, LEAD)",
                    "GROUP BY, HAVING, and multi-column aggregation"
                ],
                "estimated_hours": 5.0
            },
            {
                "stage_id": "practical",
                "title": "Stage 3: Indexing Strategies & Query Optimization",
                "description": "Diagnose query performance bottlenecks using EXPLAIN ANALYZE.",
                "concepts": [
                    "B-tree, GIN (for JSONB/full-text), and Hash indexes",
                    "Composite and partial indexes for high-frequency filters",
                    "Interpreting EXPLAIN (ANALYZE, BUFFERS) execution plans",
                    "Eliminating Sequential Scans on large tables"
                ],
                "estimated_hours": 5.0
            },
            {
                "stage_id": "advanced",
                "title": "Stage 4: Transactions, Concurrency & High Availability",
                "description": "Master ACID transaction isolation levels and row-level locking.",
                "concepts": [
                    "ACID properties and isolation levels (Read Committed vs Serializable)",
                    "Row-level locking (SELECT FOR UPDATE) and deadlock prevention",
                    "Connection pooling with PgBouncer",
                    "JSONB operators, indexing, and hybrid document-relational models"
                ],
                "estimated_hours": 4.0
            }
        ],
        "practical_exercises": [
            {
                "id": "ex-pg-1",
                "title": "Schema Normalization & Migration",
                "instruction": "Design a schema for an e-commerce platform with users, orders, and line items, enforcing cascading deletes and unique constraints via Alembic."
            },
            {
                "id": "ex-pg-2",
                "title": "Window Function Analytics Query",
                "instruction": "Write a single SQL query using CTEs and window functions to compute each candidate's cumulative weighted opportunity coverage."
            },
            {
                "id": "ex-pg-3",
                "title": "Index Optimization with EXPLAIN ANALYZE",
                "instruction": "Optimize a slow query filtering on JSONB attributes from a 100ms Seq Scan to a <2ms Bitmap Index Scan using a GIN index."
            }
        ]
    },
    "kubernetes": {
        "skill_name": "Kubernetes",
        "category": "DevOps & Containers",
        "prerequisites": ["Docker Containerization", "Linux CLI", "Networking Basics"],
        "stages": [
            {
                "stage_id": "fundamentals",
                "title": "Stage 1: Cluster Architecture & Workloads",
                "description": "Understand the control plane, worker nodes, and declarative manifests.",
                "concepts": [
                    "Control plane components (API server, etcd, scheduler, controller)",
                    "Pods as the atomic scheduling unit",
                    "Deployments, ReplicaSets, and declarative rollouts",
                    "Writing YAML manifests and kubectl imperative commands"
                ],
                "estimated_hours": 6.0
            },
            {
                "stage_id": "intermediate",
                "title": "Stage 2: Services, Ingress & Configuration",
                "description": "Connect workloads securely and route external HTTP traffic into clusters.",
                "concepts": [
                    "ClusterIP, NodePort, and LoadBalancer Service types",
                    "Ingress Controllers and routing rules with NGINX/Traefik",
                    "ConfigMaps and Secrets injection into environment variables",
                    "Namespaces for environment isolation"
                ],
                "estimated_hours": 6.0
            },
            {
                "stage_id": "practical",
                "title": "Stage 3: Helm Packaging & Automated Deployments",
                "description": "Package applications into reusable Helm charts for multi-environment CD.",
                "concepts": [
                    "Helm chart structure, values.yaml, and templating",
                    "Helm lifecycle hooks and rollbacks",
                    "Horizontal Pod Autoscalers (HPA) based on CPU/memory metrics",
                    "Readiness and Liveness probes configuration"
                ],
                "estimated_hours": 6.0
            },
            {
                "stage_id": "advanced",
                "title": "Stage 4: Cluster Operations, Security & Observability",
                "description": "Operate production clusters with zero downtime and strict security.",
                "concepts": [
                    "Role-Based Access Control (RBAC) and ServiceAccounts",
                    "NetworkPolicies for microsegmentation",
                    "Resource quotas, limit ranges, and OOM prevention",
                    "Prometheus monitoring and Grafana cluster dashboards"
                ],
                "estimated_hours": 6.0
            }
        ],
        "practical_exercises": [
            {
                "id": "ex-k8s-1",
                "title": "Multi-Tier Deployment with Probes",
                "instruction": "Deploy a 3-replica backend deployment with liveness and readiness probes, connected to a ClusterIP service and ConfigMap."
            },
            {
                "id": "ex-k8s-2",
                "title": "Custom Helm Chart",
                "instruction": "Create a parameterizable Helm chart deploying your application with staging and production values overrides."
            },
            {
                "id": "ex-k8s-3",
                "title": "Zero-Downtime Rolling Update & HPA",
                "instruction": "Configure an HPA to scale pods between 2 and 10 replicas under ApacheBench load, validating zero dropped requests during an image upgrade."
            }
        ]
    },
    "aws": {
        "skill_name": "AWS",
        "category": "Cloud Platforms",
        "prerequisites": ["Networking Basics (VPC, CIDR)", "Linux Fundamentals", "Security Concepts"],
        "stages": [
            {
                "stage_id": "fundamentals",
                "title": "Stage 1: Core Cloud Infrastructure & IAM",
                "description": "Master AWS global infrastructure, identity, and security perimeters.",
                "concepts": [
                    "Regions, Availability Zones, and edge locations",
                    "IAM Users, Roles, Policies, and Least Privilege principles",
                    "Virtual Private Cloud (VPC), subnets, route tables, and Internet Gateways",
                    "Security Groups vs Network Access Control Lists (NACLs)"
                ],
                "estimated_hours": 5.0
            },
            {
                "stage_id": "intermediate",
                "title": "Stage 2: Compute, Storage & Managed Databases",
                "description": "Deploy scalable compute instances, object storage, and relational engines.",
                "concepts": [
                    "EC2 instance types, Auto Scaling Groups, and Application Load Balancers",
                    "S3 bucket policies, versioning, lifecycles, and encryption",
                    "Amazon RDS (PostgreSQL/MySQL) multi-AZ and read replicas",
                    "AWS EBS volume types and snapshot backups"
                ],
                "estimated_hours": 6.0
            },
            {
                "stage_id": "practical",
                "title": "Stage 3: Serverless & Container Services",
                "description": "Build event-driven architectures with AWS Lambda, API Gateway, and ECS.",
                "concepts": [
                    "AWS Lambda functions and event-source triggers",
                    "Amazon API Gateway REST and HTTP endpoints",
                    "Amazon ECS and Fargate serverless containers",
                    "Amazon SQS queues and SNS pub/sub messaging"
                ],
                "estimated_hours": 6.0
            },
            {
                "stage_id": "advanced",
                "title": "Stage 4: Infrastructure as Code & Reliability",
                "description": "Automate cloud provisioning with CloudFormation / Terraform and CloudWatch.",
                "concepts": [
                    "Infrastructure as Code with Terraform or AWS CDK",
                    "CloudWatch metrics, alarms, and CloudTrail auditing",
                    "Disaster recovery strategies (Backup & Restore, Pilot Light)",
                    "AWS Well-Architected Framework: Security, Reliability, Cost Optimization"
                ],
                "estimated_hours": 5.0
            }
        ],
        "practical_exercises": [
            {
                "id": "ex-aws-1",
                "title": "Secure Two-Tier VPC",
                "instruction": "Provision a VPC with public subnets for load balancers and private subnets with NAT Gateways for backend compute."
            },
            {
                "id": "ex-aws-2",
                "title": "Serverless Event Processor",
                "instruction": "Deploy a Lambda function triggered by S3 uploads that parses file metadata and writes records to an RDS database."
            },
            {
                "id": "ex-aws-3",
                "title": "Automated CloudWatch Alarm",
                "instruction": "Configure CloudWatch metric alarms monitoring ALB 5XX error rates and triggering SNS notifications."
            }
        ]
    },
    "redis": {
        "skill_name": "Redis",
        "category": "Databases & Storage",
        "prerequisites": ["Data Structures Basics", "Client-Server Networking"],
        "stages": [
            {
                "stage_id": "fundamentals",
                "title": "Stage 1: In-Memory Data Structures",
                "description": "Master Redis primitive data structures and memory optimization.",
                "concepts": [
                    "Strings, Hashes, Lists, Sets, and Sorted Sets (ZSET)",
                    "Key expiration (TTL) and eviction policies (LRU, LFU)",
                    "Redis CLI commands and atomic operations",
                    "Single-threaded event loop execution benefits"
                ],
                "estimated_hours": 3.0
            },
            {
                "stage_id": "intermediate",
                "title": "Stage 2: Caching Patterns & Session Stores",
                "description": "Design resilient caching strategies to accelerate relational databases.",
                "concepts": [
                    "Cache-aside, read-through, and write-through caching patterns",
                    "Handling Cache Stampede / Dogpiling with probabilistic early expiration",
                    "Distributed session management and token storage",
                    "Connection pooling and client library configuration"
                ],
                "estimated_hours": 4.0
            },
            {
                "stage_id": "practical",
                "title": "Stage 3: Message Queues & Distributed Locks",
                "description": "Implement pub/sub, background queues, and Redlock distributed synchronization.",
                "concepts": [
                    "Pub/Sub messaging and Redis Streams consumer groups",
                    "Background task queue brokering with Celery/RQ",
                    "Distributed locking with SET NX EX and Redlock algorithm",
                    "Rate limiting with sliding window algorithms"
                ],
                "estimated_hours": 4.0
            },
            {
                "stage_id": "advanced",
                "title": "Stage 4: Persistence, Clustering & High Availability",
                "description": "Operate production Redis with replication and Sentinel failover.",
                "concepts": [
                    "RDB snapshots vs Append-Only File (AOF) persistence",
                    "Primary-Replica replication and Redis Sentinel automatic failover",
                    "Redis Cluster sharding and hash slots",
                    "Memory optimization: jemalloc profiling and ziplist encoding"
                ],
                "estimated_hours": 3.0
            }
        ],
        "practical_exercises": [
            {
                "id": "ex-redis-1",
                "title": "Sliding-Window Rate Limiter",
                "instruction": "Implement a distributed API rate limiter using Redis Sorted Sets allowing at most 60 requests per minute per IP address."
            },
            {
                "id": "ex-redis-2",
                "title": "Cache-Aside Data Layer",
                "instruction": "Integrate a Redis caching decorator over database queries with automatic invalidation on record updates."
            },
            {
                "id": "ex-redis-3",
                "title": "Distributed Lock Manager",
                "instruction": "Build an atomic distributed lock helper ensuring that scheduled cron jobs execute on exactly one worker instance."
            }
        ]
    }
}


class SkillCurriculumService:
    @classmethod
    def get_skill_curriculum(
        cls,
        skill_name: str,
        estimated_hours: float = 16.0,
        prerequisites: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> SkillCurriculum:
        """
        Retrieves curated 4-stage roadmap and practical exercises for the skill.
        If the skill is not in the predefined catalog, dynamically generates a pedagogically
        sound 4-stage engineering curriculum.
        """
        norm_key = skill_name.lower().strip().replace(".", "").replace("-", "").replace(" ", "")
        
        # Check direct or alias key match
        for key, data in SKILL_CURRICULUM_CATALOG.items():
            if key == norm_key or data["skill_name"].lower() == skill_name.lower().strip():
                stages = [RoadmapStage(**s) for s in data["stages"]]
                exercises = [PracticalExercise(**e) for e in data["practical_exercises"]]
                return SkillCurriculum(
                    skill_name=data["skill_name"],
                    category=category or data["category"],
                    prerequisites=prerequisites or data["prerequisites"],
                    stages=stages,
                    practical_exercises=exercises
                )

        # Dynamic fallback curriculum for arbitrary technical skill
        q_hours = max(2.0, round(estimated_hours / 4.0, 1))
        dyn_stages = [
            RoadmapStage(
                stage_id="fundamentals",
                title="Stage 1: Core Syntax, Fundamentals & Environment Setup",
                description=f"Establish local toolchains, syntax foundations, and foundational mental models for {skill_name}.",
                concepts=[
                    f"Core terminology, specifications, and execution model for {skill_name}",
                    f"Environment setup, CLI tools, and runtime installation",
                    f"Basic primitives, declarative conventions, and configuration options",
                    f"Hello-World implementation and validation"
                ],
                estimated_hours=q_hours
            ),
            RoadmapStage(
                stage_id="intermediate",
                title="Stage 2: Core Architecture & Data Patterns",
                description=f"Design robust implementations and integrate {skill_name} with surrounding system components.",
                concepts=[
                    f"Structural design patterns and idiomatic idioms in {skill_name}",
                    f"State management, persistence, and external interface integration",
                    f"Error handling, edge cases, and logging practices",
                    f"Modular code organization and reusability"
                ],
                estimated_hours=q_hours
            ),
            RoadmapStage(
                stage_id="practical",
                title="Stage 3: Practical Implementation & Testing",
                description=f"Construct complete, working portfolio artifacts utilizing {skill_name} under real-world conditions.",
                concepts=[
                    f"End-to-end practical feature delivery with {skill_name}",
                    f"Automated testing, mock fixtures, and validation suites",
                    f"Integration into automated build and CI/CD pipelines",
                    f"Debugging workflows and telemetry inspection"
                ],
                estimated_hours=q_hours
            ),
            RoadmapStage(
                stage_id="advanced",
                title="Stage 4: Scalability, Security & Production Readiness",
                description=f"Harden {skill_name} implementations for enterprise throughput, security, and maintainability.",
                concepts=[
                    f"Performance profiling and bottleneck elimination for {skill_name}",
                    f"Security hardening, authentication, and credential isolation",
                    f"Observability, metrics, and production monitoring",
                    f"Industry best practices and architectural review"
                ],
                estimated_hours=q_hours
            )
        ]

        dyn_exercises = [
            PracticalExercise(
                id=f"ex-{norm_key}-1",
                title=f"{skill_name} Core Scaffolding",
                instruction=f"Scaffold a working implementation demonstrating the core fundamentals of {skill_name} with automated verification tests."
            ),
            PracticalExercise(
                id=f"ex-{norm_key}-2",
                title=f"{skill_name} Integration & Error Handling",
                instruction=f"Integrate {skill_name} with persistent storage or external interfaces, implementing comprehensive error boundaries and edge-case handling."
            ),
            PracticalExercise(
                id=f"ex-{norm_key}-3",
                title=f"{skill_name} Performance & CI Validation",
                instruction=f"Profile execution performance under simulated load and integrate validation checks into a CI pipeline."
            )
        ]

        return SkillCurriculum(
            skill_name=skill_name,
            category=category or "Technical Competency",
            prerequisites=prerequisites or ["Fundamental Software Engineering Concepts"],
            stages=dyn_stages,
            practical_exercises=dyn_exercises
        )
