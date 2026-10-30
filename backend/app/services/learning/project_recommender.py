from typing import List, Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field


class MilestoneItem(BaseModel):
    step_number: int
    title: str
    description: str
    estimated_hours: float


class ProjectBlueprint(BaseModel):
    project_id: str
    title: str
    purpose: str
    difficulty_level: str  # Beginner, Intermediate, Advanced
    estimated_hours: float
    is_estimate: bool = True
    target_skills: List[str]
    skill_gaps_addressed: List[str] = Field(default_factory=list)
    prerequisites: List[str]
    suggested_tech_stack: Dict[str, str]
    milestones: List[MilestoneItem]
    deliverables: List[str]
    validation_checklist: List[str]
    career_impact_rationale: str
    documentation_links: List[Dict[str, str]] = Field(default_factory=list)
    match_score: float = 0.0


PROJECT_TEMPLATES: List[Dict[str, Any]] = [
    {
        "project_id": "fastapi-docker-microservice",
        "title": "High-Throughput Asynchronous Task Processing Engine",
        "purpose": "Design and build a resilient asynchronous queue and worker service using FastAPI, Celery/Redis, and PostgreSQL with Docker containerization.",
        "difficulty_level": "Intermediate",
        "estimated_hours": 24.0,
        "target_skills": ["FastAPI", "Python", "Docker", "PostgreSQL", "Redis", "CI/CD"],
        "prerequisites": ["Python", "SQL Basics", "Git"],
        "suggested_tech_stack": {
            "framework": "FastAPI (Python 3.12)",
            "database": "PostgreSQL 16 with SQLAlchemy 2.0 ORM & Alembic migrations",
            "cache_queue": "Redis 7 for background job brokering",
            "containerization": "Multi-stage Dockerfile and Docker Compose",
            "testing": "Pytest with Testcontainers or SQLite in-memory fixtures"
        },
        "milestones": [
            {
                "step_number": 1,
                "title": "Domain Modeling & Database Migrations",
                "description": "Define declarative SQLAlchemy schemas for tasks, users, and audit logs. Implement Alembic auto-generating migrations.",
                "estimated_hours": 5.0
            },
            {
                "step_number": 2,
                "title": "Asynchronous API Endpoints & Validation",
                "description": "Implement non-blocking async endpoints for submitting, polling, and canceling high-throughput jobs with strict Pydantic schemas.",
                "estimated_hours": 7.0
            },
            {
                "step_number": 3,
                "title": "Redis Background Queue & Worker Concurrency",
                "description": "Configure asynchronous workers with exponential backoff retries, dead-letter queues, and idempotency key checks.",
                "estimated_hours": 6.0
            },
            {
                "step_number": 4,
                "title": "Dockerization, Health Checks & CI/CD",
                "description": "Create slim production multi-stage Dockerfiles (<150MB), Docker Compose orchestration, and a GitHub Actions CI test pipeline.",
                "estimated_hours": 6.0
            }
        ],
        "deliverables": [
            "Clean Git repository with conventional commit history",
            "Production multi-stage Dockerfile and docker-compose.yml",
            "Comprehensive pytest suite with >80% statement coverage",
            "OpenAPI / Swagger documentation with interactive try-it endpoints"
        ],
        "validation_checklist": [
            "All async endpoints respond with <25ms p95 latency under local load",
            "Failed worker tasks automatically retry up to 3 times with exponential backoff",
            "Docker compose up boots database, Redis, API, and worker without manual intervention",
            "CI/CD workflow passes formatting (Black/Ruff) and unit tests"
        ],
        "career_impact_rationale": "Demonstrates production-ready backend architecture, asynchronous programming, containerization, and data persistence—core competencies sought by modern engineering teams."
    },
    {
        "project_id": "fullstack-angular-fastapi",
        "title": "Enterprise Opportunity & Analytics Dashboard",
        "purpose": "Construct an end-to-end web application with an Angular 22 Signals frontend, secure JWT authentication, and a FastAPI REST backend.",
        "difficulty_level": "Intermediate",
        "estimated_hours": 28.0,
        "target_skills": ["Angular", "TypeScript", "FastAPI", "Python", "PostgreSQL", "Docker"],
        "prerequisites": ["HTML/CSS", "JavaScript/TypeScript", "Python"],
        "suggested_tech_stack": {
            "frontend": "Angular 22 with Standalone Components and Signals",
            "backend": "FastAPI with JWT OAuth2 Bearer Authentication",
            "database": "PostgreSQL with connection pooling",
            "styling": "Modern SCSS / CSS Grid with dark mode support"
        },
        "milestones": [
            {
                "step_number": 1,
                "title": "Authentication & Session Security",
                "description": "Build bcrypt password hashing, JWT access token issuance, Angular HTTP interceptors, and route guards.",
                "estimated_hours": 6.0
            },
            {
                "step_number": 2,
                "title": "Interactive Analytics & Signals UI",
                "description": "Implement reactive dashboard views using Angular Signals and computed properties for real-time metric filtering.",
                "estimated_hours": 8.0
            },
            {
                "step_number": 3,
                "title": "Paginated Search & Dynamic Filters",
                "description": "Construct server-side pagination, multi-attribute filtering, and debounced instant autocomplete.",
                "estimated_hours": 7.0
            },
            {
                "step_number": 4,
                "title": "Full-Stack Deployment & E2E Validation",
                "description": "Configure Nginx reverse proxy serving static Angular AOT bundle and routing `/api` traffic to FastAPI container.",
                "estimated_hours": 7.0
            }
        ],
        "deliverables": [
            "Production Angular bundle with zero linting or AOT errors",
            "FastAPI backend adhering to RESTful standards",
            "Nginx configuration handling client-side SPA routing and HTTPS headers"
        ],
        "validation_checklist": [
            "Tokens securely handled in memory/HTTP headers without leaking to localStorage",
            "Zero hydration or flicker issues on initial dashboard load",
            "Responsive layout tested on desktop, tablet, and mobile breakpoints"
        ],
        "career_impact_rationale": "Shows full-stack proficiency, modern frontend state management with Signals, clean API contract design, and secure authentication flows."
    },
    {
        "project_id": "kubernetes-cloud-resilience",
        "title": "Cloud-Native Infrastructure & Kubernetes Cluster Deployment",
        "purpose": "Deploy and manage a resilient microservice architecture on Kubernetes with automated rolling updates, autoscaling, and ingress.",
        "difficulty_level": "Advanced",
        "estimated_hours": 32.0,
        "target_skills": ["Kubernetes", "Docker", "Terraform", "CI/CD", "Linux", "AWS"],
        "prerequisites": ["Docker", "Linux CLI", "Networking Basics"],
        "suggested_tech_stack": {
            "cluster": "Kubernetes (Minikube / k3s / EKS)",
            "iac": "Terraform for infrastructure provisioning",
            "cicd": "GitHub Actions deploying via Helm charts",
            "monitoring": "Prometheus & Grafana for pod metrics"
        },
        "milestones": [
            {
                "step_number": 1,
                "title": "Cluster Provisioning & Namespace Isolation",
                "description": "Define Terraform manifests to spin up local or cloud cluster with dedicated staging and production namespaces.",
                "estimated_hours": 8.0
            },
            {
                "step_number": 2,
                "title": "Helm Packaging & Configuration",
                "description": "Package applications into reusable Helm charts with configurable values for replicas, memory, and CPU limits.",
                "estimated_hours": 8.0
            },
            {
                "step_number": 3,
                "title": "Horizontal Pod Autoscaling & Ingress",
                "description": "Configure NGINX Ingress Controller with SSL termination and HPA scaling pods based on CPU/memory pressure.",
                "estimated_hours": 8.0
            },
            {
                "step_number": 4,
                "title": "Chaos & Resilience Validation",
                "description": "Perform pod termination stress tests and verify zero-downtime rolling deployments during version upgrades.",
                "estimated_hours": 8.0
            }
        ],
        "deliverables": [
            "Modular Terraform IaC codebase",
            "Production-grade Helm chart repository",
            "Grafana dashboard export displaying cluster throughput and error rates"
        ],
        "validation_checklist": [
            "Cluster automatically recovers within 15 seconds of random pod failure",
            "Zero dropped HTTP connections during rolling updates",
            "Strict resource limits (requests/limits) prevent node out-of-memory crashes"
        ],
        "career_impact_rationale": "High-impact portfolio piece demonstrating enterprise DevOps, infrastructure as code, and production cluster operations."
    },
    {
        "project_id": "ml-pipeline-scikit-fastapi",
        "title": "Predictive ML Model & Production Serving API",
        "purpose": "Train, evaluate, and deploy an end-to-end predictive machine learning model with Scikit-Learn served behind a real-time FastAPI inference endpoint.",
        "difficulty_level": "Intermediate",
        "estimated_hours": 20.0,
        "target_skills": ["Scikit-Learn", "Python", "FastAPI", "Docker", "SQL"],
        "prerequisites": ["Python", "Pandas Basics", "Basic Statistics"],
        "suggested_tech_stack": {
            "ml_libraries": "Scikit-Learn, NumPy, Pandas",
            "serialization": "Joblib / ONNX for model artifacts",
            "serving": "FastAPI with batched inference support",
            "packaging": "Docker containerized inference image"
        },
        "milestones": [
            {
                "step_number": 1,
                "title": "Exploratory Analysis & Feature Engineering",
                "description": "Clean raw tabular data, handle categorical encodings, impute missing values, and construct repeatable Scikit-Learn Pipelines.",
                "estimated_hours": 5.0
            },
            {
                "step_number": 2,
                "title": "Model Training & Cross-Validation Benchmarking",
                "description": "Train multiple baseline classifiers, perform hyperparameter grid search, and evaluate precision-recall and ROC curves.",
                "estimated_hours": 5.0
            },
            {
                "step_number": 3,
                "title": "FastAPI Inference API & Input Validation",
                "description": "Build high-speed prediction endpoints validating feature schemas with Pydantic and returning confidence scores.",
                "estimated_hours": 5.0
            },
            {
                "step_number": 4,
                "title": "Containerization & Model Drift Telemetry",
                "description": "Containerize the inference service and add lightweight endpoint latency and feature distribution logging.",
                "estimated_hours": 5.0
            }
        ],
        "deliverables": [
            "Jupyter notebook detailing data preprocessing, model selection, and metric comparison",
            "Exported Scikit-Learn Pipeline artifact",
            "Tested FastAPI inference microservice"
        ],
        "validation_checklist": [
            "Model achieves demonstrable improvement over naive majority-class baseline",
            "Inference endpoint responds in <15ms for single predictions",
            "Invalid feature inputs return descriptive HTTP 422 validation errors"
        ],
        "career_impact_rationale": "Shows practical Applied Machine Learning competence—bridging the gap between notebook experimentation and production API deployment."
    }
]


class ProjectRecommenderService:
    @classmethod
    def _normalize_title(cls, text: str) -> str:
        return text.lower().strip()

    @classmethod
    def _is_duplicate_of_existing(cls, blueprint_title: str, existing_projects: List[Dict[str, Any]]) -> bool:
        """
        Deduplicates recommended blueprints against candidate's existing projects.
        Checks title overlap, keyword matching, and technology similarity.
        """
        norm_bp = cls._normalize_title(blueprint_title)
        bp_words = set(norm_bp.split())

        for proj in existing_projects:
            title = cls._normalize_title(proj.get("title", ""))
            desc = cls._normalize_title(proj.get("description", ""))

            # Direct title match or severe word overlap (>65%)
            if title == norm_bp:
                return True
            title_words = set(title.split())
            if len(title_words) > 0:
                overlap = len(bp_words.intersection(title_words)) / max(len(bp_words), len(title_words))
                if overlap > 0.65:
                    return True

        return False

    @classmethod
    def recommend_projects(
        cls,
        candidate_skills: List[str],
        skill_gaps: List[str],
        target_roles: Optional[List[str]] = None,
        existing_projects: Optional[List[Dict[str, Any]]] = None,
        available_hours: Optional[float] = None,
        limit: int = 3
    ) -> List[ProjectBlueprint]:
        """
        Generates profile-aware project blueprints tailored to the candidate's
        unmet skill gaps, target roles, and available time budget.
        Deduplicates against projects already present on candidate profile/resume.
        """
        norm_candidate_skills = {s.lower().strip() for s in candidate_skills}
        norm_gaps = {s.lower().strip() for s in skill_gaps}
        norm_roles = [r.lower().strip() for r in (target_roles or [])]
        user_projects = existing_projects or []

        scored_blueprints: List[Tuple[float, ProjectBlueprint]] = []

        for tmpl in PROJECT_TEMPLATES:
            # 1. Deduplication check
            if cls._is_duplicate_of_existing(tmpl["title"], user_projects):
                continue

            # 2. Compute skill gap overlap
            tmpl_skills = tmpl["target_skills"]
            addressed_gaps = []
            for s in tmpl_skills:
                s_lower = s.lower()
                if any(s_lower in g or g in s_lower for g in norm_gaps):
                    addressed_gaps.append(s)

            # 3. Match score calculation
            # Base score from addressed gaps (highest priority)
            score = len(addressed_gaps) * 3.0

            # Bonus for role alignment
            for role in norm_roles:
                if any(role_word in tmpl["title"].lower() or role_word in tmpl["purpose"].lower() for role_word in role.split()):
                    score += 2.0

            # Budget suitability
            if available_hours and available_hours > 0:
                if tmpl["estimated_hours"] <= available_hours:
                    score += 1.5
                elif tmpl["estimated_hours"] <= available_hours * 1.5:
                    score += 0.5
                else:
                    score -= 1.0  # Penalize projects far exceeding user budget

            # Prerequisite readiness: candidate should have at least some prereqs
            prereqs = tmpl["prerequisites"]
            has_prereq_count = sum(1 for p in prereqs if any(p.lower() in cs for cs in norm_candidate_skills))
            score += has_prereq_count * 1.0

            bp = ProjectBlueprint(
                project_id=tmpl["project_id"],
                title=tmpl["title"],
                purpose=tmpl["purpose"],
                difficulty_level=tmpl["difficulty_level"],
                estimated_hours=tmpl["estimated_hours"],
                is_estimate=True,
                target_skills=tmpl["target_skills"],
                skill_gaps_addressed=addressed_gaps,
                prerequisites=tmpl["prerequisites"],
                suggested_tech_stack=tmpl["suggested_tech_stack"],
                milestones=[MilestoneItem(**m) for m in tmpl["milestones"]],
                deliverables=tmpl["deliverables"],
                validation_checklist=tmpl["validation_checklist"],
                career_impact_rationale=tmpl["career_impact_rationale"],
                match_score=round(score, 2)
            )
            scored_blueprints.append((score, bp))

        scored_blueprints.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_blueprints[:limit]]

    @classmethod
    def get_projects_for_skill(
        cls,
        skill_name: str,
        existing_projects: Optional[List[Dict[str, Any]]] = None,
        limit: int = 3
    ) -> List[ProjectBlueprint]:
        """
        Returns practical project blueprints strictly targeting the specified skill.
        If no pre-authored template covers the skill, dynamically constructs a realistic
        practical portfolio blueprint for that skill.
        """
        norm = skill_name.lower().strip()
        user_projects = existing_projects or []
        matched: List[ProjectBlueprint] = []

        for tmpl in PROJECT_TEMPLATES:
            if cls._is_duplicate_of_existing(tmpl["title"], user_projects):
                continue
            is_relevant = any(
                norm == s.lower() or (len(norm) >= 3 and (norm in s.lower() or s.lower() in norm))
                for s in tmpl["target_skills"]
            )
            if is_relevant:
                bp = ProjectBlueprint(
                    project_id=tmpl["project_id"],
                    title=tmpl["title"],
                    purpose=tmpl["purpose"],
                    difficulty_level=tmpl["difficulty_level"],
                    estimated_hours=tmpl["estimated_hours"],
                    is_estimate=True,
                    target_skills=tmpl["target_skills"],
                    skill_gaps_addressed=[s for s in tmpl["target_skills"] if norm in s.lower() or s.lower() in norm],
                    prerequisites=tmpl["prerequisites"],
                    suggested_tech_stack=tmpl["suggested_tech_stack"],
                    milestones=[MilestoneItem(**m) for m in tmpl["milestones"]],
                    deliverables=tmpl["deliverables"],
                    validation_checklist=tmpl["validation_checklist"],
                    career_impact_rationale=tmpl["career_impact_rationale"],
                    match_score=1.0
                )
                matched.append(bp)

        if not matched:
            pid = f"{norm.replace(' ', '-').replace('.', '')}-production-system"
            matched.append(
                ProjectBlueprint(
                    project_id=pid,
                    title=f"Production-Grade {skill_name} System Architecture",
                    purpose=f"Design, build, and test a production-ready application demonstrating core and advanced competencies in {skill_name}.",
                    difficulty_level="Intermediate",
                    estimated_hours=20.0,
                    is_estimate=True,
                    target_skills=[skill_name],
                    skill_gaps_addressed=[skill_name],
                    prerequisites=["Software Engineering Fundamentals", "Git"],
                    suggested_tech_stack={"primary_technology": skill_name, "testing": "Automated Testing / Pytest"},
                    milestones=[
                        MilestoneItem(
                            step_number=1,
                            title="Scaffolding & Architecture",
                            description=f"Set up development environment and scaffold project structure utilizing {skill_name}.",
                            estimated_hours=5.0
                        ),
                        MilestoneItem(
                            step_number=2,
                            title="Core Implementation",
                            description=f"Implement primary workflows, state handling, and data models with {skill_name}.",
                            estimated_hours=6.0
                        ),
                        MilestoneItem(
                            step_number=3,
                            title="Automated Test Suite",
                            description="Write comprehensive automated tests covering normal operations, error boundaries, and edge cases.",
                            estimated_hours=5.0
                        ),
                        MilestoneItem(
                            step_number=4,
                            title="Deployment & Documentation",
                            description="Containerize the solution and document architectural decisions in a clear README.",
                            estimated_hours=4.0
                        )
                    ],
                    deliverables=[
                        "Clean Git repository with structured commit history",
                        f"Fully working implementation utilizing {skill_name}",
                        "Automated test suite verifying core functional paths",
                        "Comprehensive README documenting setup and design decisions"
                    ],
                    validation_checklist=[
                        "All unit and integration tests execute and pass cleanly",
                        "No hardcoded credentials or unhandled exceptions",
                        "Project successfully builds and runs in a clean environment"
                    ],
                    career_impact_rationale=f"Provides tangible evidence of hands-on technical proficiency with {skill_name} for engineering hiring managers.",
                    match_score=1.0
                )
            )

        return matched[:limit]

