from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DocResource(BaseModel):
    skill_name: str
    title: str
    url: str
    official_domain: str
    category: str
    description: str
    topics: List[str] = Field(default_factory=list)
    is_official: bool = True


# Comprehensive curated catalog of verified official documentation
OFFICIAL_DOC_CATALOG: Dict[str, DocResource] = {
    "python": DocResource(
        skill_name="Python",
        title="Official Python 3 Documentation",
        url="https://docs.python.org/3/",
        official_domain="python.org",
        category="Programming Language",
        description="Comprehensive reference for Python standard library, language specification, and tutorial.",
        topics=["Language Reference", "Standard Library", "Asyncio", "Data Structures", "Type Hinting"]
    ),
    "fastapi": DocResource(
        skill_name="FastAPI",
        title="FastAPI Official Documentation",
        url="https://fastapi.tiangolo.com/",
        official_domain="fastapi.tiangolo.com",
        category="Backend Framework",
        description="High performance, easy to learn, fast to code, ready for production API framework.",
        topics=["Dependency Injection", "Pydantic Schemas", "Async Endpoints", "Security & OAuth2", "OpenAPI"]
    ),
    "django": DocResource(
        skill_name="Django",
        title="Django Project Documentation",
        url="https://docs.djangoproject.com/en/stable/",
        official_domain="djangoproject.com",
        category="Backend Framework",
        description="The web framework for perfectionists with deadlines.",
        topics=["ORM", "Migrations", "Authentication", "Admin Panel", "REST Framework Integration"]
    ),
    "flask": DocResource(
        skill_name="Flask",
        title="Flask Official User Guide",
        url="https://flask.palletsprojects.com/",
        official_domain="palletsprojects.com",
        category="Backend Framework",
        description="Lightweight WSGI web application framework in Python.",
        topics=["Routing", "Blueprints", "Request Context", "Jinja2 Templates", "Extensions"]
    ),
    "docker": DocResource(
        skill_name="Docker",
        title="Docker Documentation & Guides",
        url="https://docs.docker.com/",
        official_domain="docker.com",
        category="DevOps & Containers",
        description="Official manuals for Docker Engine, Dockerfiles, Docker Compose, and container networking.",
        topics=["Dockerfiles", "Multi-stage Builds", "Compose", "Volumes", "Container Networking"]
    ),
    "kubernetes": DocResource(
        skill_name="Kubernetes",
        title="Kubernetes Production Grade Container Orchestration",
        url="https://kubernetes.io/docs/home/",
        official_domain="kubernetes.io",
        category="DevOps & Containers",
        description="Official architectural guide and API reference for Kubernetes clusters.",
        topics=["Pods", "Deployments", "Services", "Ingress", "ConfigMaps & Secrets", "StatefulSets"]
    ),
    "typescript": DocResource(
        skill_name="TypeScript",
        title="TypeScript Handbook",
        url="https://www.typescriptlang.org/docs/",
        official_domain="typescriptlang.org",
        category="Programming Language",
        description="Official handbook covering static types, interfaces, generics, and compiler options.",
        topics=["Type Inference", "Interfaces", "Generics", "Utility Types", "tsconfig.json"]
    ),
    "javascript": DocResource(
        skill_name="JavaScript",
        title="MDN Web Docs: JavaScript Reference",
        url="https://developer.mozilla.org/en-US/docs/Web/JavaScript",
        official_domain="developer.mozilla.org",
        category="Programming Language",
        description="Authoritative reference for modern ECMAScript standards, Web APIs, and asynchronous JS.",
        topics=["ES6+ Syntax", "Promises & Async/Await", "Closures", "Event Loop", "DOM Manipulation"]
    ),
    "angular": DocResource(
        skill_name="Angular",
        title="Angular Documentation (Next-Gen)",
        url="https://angular.dev/",
        official_domain="angular.dev",
        category="Frontend Framework",
        description="The web development framework for building modern web applications.",
        topics=["Signals", "Standalone Components", "Dependency Injection", "RxJS", "Routing", "Forms"]
    ),
    "react": DocResource(
        skill_name="React",
        title="React Official Documentation",
        url="https://react.dev/",
        official_domain="react.dev",
        category="Frontend Framework",
        description="The library for web and native user interfaces.",
        topics=["Components", "Hooks", "State Management", "Server Components", "Performance"]
    ),
    "vue": DocResource(
        skill_name="Vue.js",
        title="Vue.js Guide & API",
        url="https://vuejs.org/guide/introduction.html",
        official_domain="vuejs.org",
        category="Frontend Framework",
        description="An accessible, performant and versatile framework for building web user interfaces.",
        topics=["Composition API", "Reactivity", "Single-File Components", "Pinia", "Vue Router"]
    ),
    "postgresql": DocResource(
        skill_name="PostgreSQL",
        title="PostgreSQL Official Documentation",
        url="https://www.postgresql.org/docs/",
        official_domain="postgresql.org",
        category="Database",
        description="The world's most advanced open source relational database.",
        topics=["Indexing (B-Tree, GIN, GiST)", "Transactions & ACID", "JSONB", "Query Optimization", "Replication"]
    ),
    "redis": DocResource(
        skill_name="Redis",
        title="Redis Documentation",
        url="https://redis.io/docs/",
        official_domain="redis.io",
        category="Database",
        description="In-memory data store used as a database, cache, streaming engine, and message broker.",
        topics=["Data Structures", "Pub/Sub", "Cache Invalidation", "Persistence (RDB/AOF)", "Clustering"]
    ),
    "mongodb": DocResource(
        skill_name="MongoDB",
        title="MongoDB Manual & Developer Guides",
        url="https://www.mongodb.com/docs/",
        official_domain="mongodb.com",
        category="Database",
        description="Document database designed for flexibility and rapid development.",
        topics=["Aggregation Pipeline", "Indexing", "Replica Sets", "Sharding", "Schema Design"]
    ),
    "scikit-learn": DocResource(
        skill_name="Scikit-Learn",
        title="Scikit-Learn User Guide & API",
        url="https://scikit-learn.org/stable/user_guide.html",
        official_domain="scikit-learn.org",
        category="Data Science & ML",
        description="Machine learning in Python: simple and efficient tools for predictive data analysis.",
        topics=["Supervised Learning", "Unsupervised Learning", "Model Selection & Cross-Validation", "Pipelines"]
    ),
    "pytorch": DocResource(
        skill_name="PyTorch",
        title="PyTorch Documentation",
        url="https://pytorch.org/docs/stable/index.html",
        official_domain="pytorch.org",
        category="Data Science & ML",
        description="An open source machine learning framework that accelerates the path from research prototyping to production.",
        topics=["Tensors", "Autograd", "Neural Networks (nn.Module)", "DataLoader", "CUDA Acceleration"]
    ),
    "tensorflow": DocResource(
        skill_name="TensorFlow",
        title="TensorFlow Core Guide",
        url="https://www.tensorflow.org/guide",
        official_domain="tensorflow.org",
        category="Data Science & ML",
        description="An end-to-end open source platform for machine learning.",
        topics=["Keras API", "TensorFlow Data", "SavedModel", "Distributed Training", "TF Lite"]
    ),
    "aws": DocResource(
        skill_name="Amazon Web Services",
        title="AWS Documentation Portal",
        url="https://docs.aws.amazon.com/",
        official_domain="aws.amazon.com",
        category="Cloud Computing",
        description="Comprehensive guides for compute, storage, networking, security, and databases on AWS.",
        topics=["EC2", "S3", "Lambda", "IAM", "VPC", "ECS/EKS", "RDS"]
    ),
    "gcp": DocResource(
        skill_name="Google Cloud Platform",
        title="Google Cloud Documentation",
        url="https://cloud.google.com/docs",
        official_domain="cloud.google.com",
        category="Cloud Computing",
        description="Guides, tutorials, and code samples for Google Cloud services.",
        topics=["Cloud Run", "Compute Engine", "GKE", "BigQuery", "Cloud Storage", "Vertex AI"]
    ),
    "azure": DocResource(
        skill_name="Microsoft Azure",
        title="Azure Documentation Center",
        url="https://learn.microsoft.com/en-us/azure/",
        official_domain="microsoft.com",
        category="Cloud Computing",
        description="Official learning paths and architectural documentation for Azure cloud services.",
        topics=["Azure App Services", "Virtual Machines", "Azure SQL", "Cosmos DB", "AKS", "Entra ID"]
    ),
    "git": DocResource(
        skill_name="Git",
        title="Git Official Reference Manual",
        url="https://git-scm.com/doc",
        official_domain="git-scm.com",
        category="Developer Tools",
        description="The reference guide for distributed version control.",
        topics=["Branching", "Merging & Rebasing", "Commit History", "Interactive Rebase", "Stashing"]
    ),
    "ci/cd": DocResource(
        skill_name="CI/CD & GitHub Actions",
        title="GitHub Actions Documentation",
        url="https://docs.github.com/en/actions",
        official_domain="github.com",
        category="DevOps & Containers",
        description="Automate, customize, and execute your software development workflows right in your repository.",
        topics=["Workflows", "Jobs & Steps", "Runners", "Matrix Builds", "Secrets Management"]
    ),
    "linux": DocResource(
        skill_name="Linux",
        title="The Linux Kernel & GNU Documentation",
        url="https://www.kernel.org/doc/html/latest/",
        official_domain="kernel.org",
        category="Operating Systems",
        description="Core architecture, system administration, and shell scripting documentation.",
        topics=["Process Management", "File Permissions", "Bash Scripting", "Systemd", "Networking CLI"]
    ),
    "terraform": DocResource(
        skill_name="Terraform",
        title="Terraform Documentation & HashiCorp Learn",
        url="https://developer.hashicorp.com/terraform/docs",
        official_domain="hashicorp.com",
        category="DevOps & Containers",
        description="Infrastructure as Code for provisioning and managing any cloud, infrastructure, or service.",
        topics=["HCL Syntax", "State Management", "Modules", "Providers", "Terraform Plan/Apply"]
    ),
    "langchain": DocResource(
        skill_name="LangChain & LangGraph",
        title="LangChain Python Documentation",
        url="https://python.langchain.com/docs/",
        official_domain="langchain.com",
        category="AI Engineering",
        description="Build context-aware, reasoning applications with LangChain and LangGraph agent runtimes.",
        topics=["Chains", "Prompt Templates", "Tool Calling", "LangGraph StateGraph", "Retrieval (RAG)"]
    ),
    "sql": DocResource(
        skill_name="SQL",
        title="SQL Reference Guide (PostgreSQL Standard)",
        url="https://www.postgresql.org/docs/current/sql.html",
        official_domain="postgresql.org",
        category="Database",
        description="Standard Structured Query Language reference.",
        topics=["SELECT Queries", "JOINs", "Window Functions", "Common Table Expressions (CTEs)", "Transactions"]
    )
}

# Alias resolution mapping for common skill variations
SKILL_ALIASES: Dict[str, str] = {
    "py": "python",
    "python3": "python",
    "fast-api": "fastapi",
    "django-rest-framework": "django",
    "drf": "django",
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "ts": "typescript",
    "js": "javascript",
    "es6": "javascript",
    "ecmascript": "javascript",
    "ng": "angular",
    "angular2+": "angular",
    "reactjs": "react",
    "react.js": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "postgres": "postgresql",
    "psql": "postgresql",
    "sklearn": "scikit-learn",
    "scikit_learn": "scikit-learn",
    "google-cloud": "gcp",
    "google_cloud": "gcp",
    "google cloud": "gcp",
    "amazon-web-services": "aws",
    "amazon web services": "aws",
    "github-actions": "ci/cd",
    "github actions": "ci/cd",
    "cicd": "ci/cd",
    "ci-cd": "ci/cd",
    "lang-chain": "langchain",
    "langgraph": "langchain"
}


class DocCatalogService:
    @classmethod
    def normalize_skill(cls, skill: str) -> str:
        s = skill.lower().strip().replace(" ", "-").replace("_", "-")
        return SKILL_ALIASES.get(s, s)

    @classmethod
    def resolve_documentation(cls, skill_name: str) -> Optional[DocResource]:
        """
        Resolves a skill to its verified official documentation page.
        """
        key = cls.normalize_skill(skill_name)
        if key in OFFICIAL_DOC_CATALOG:
            return OFFICIAL_DOC_CATALOG[key]

        # Check case-insensitive direct match
        for k, doc in OFFICIAL_DOC_CATALOG.items():
            if k == key or doc.skill_name.lower() == skill_name.lower():
                return doc
        return None

    @classmethod
    def search_documentation(cls, query: str, limit: int = 10) -> List[DocResource]:
        """
        Searches the curated official documentation catalog by keyword, topic, or category.
        """
        q = query.lower().strip()
        matched: List[DocResource] = []

        # 1. Exact or alias match
        norm = cls.normalize_skill(q)
        if norm in OFFICIAL_DOC_CATALOG:
            matched.append(OFFICIAL_DOC_CATALOG[norm])

        # 2. Substring matching across title, category, topics
        for k, doc in OFFICIAL_DOC_CATALOG.items():
            if doc in matched:
                continue
            if (
                q in doc.skill_name.lower() or
                q in doc.title.lower() or
                q in doc.category.lower() or
                any(q in t.lower() for t in doc.topics)
            ):
                matched.append(doc)

        return matched[:limit]

    @classmethod
    def get_all_documentation(cls) -> List[DocResource]:
        return list(OFFICIAL_DOC_CATALOG.values())
