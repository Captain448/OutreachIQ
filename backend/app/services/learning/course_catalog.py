import enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AccessType(str, enum.Enum):
    FREE_COURSE = "100% Free (Includes Certificate)"
    FREE_TO_AUDIT = "Free to Audit (Certificate Requires Payment)"
    FREE_OPEN_ACCESS = "Free Open Access (No Certificate)"
    PAID_COURSE = "Paid Course"
    PRICING_NOT_VERIFIED = "Pricing Not Verified"


class CourseItem(BaseModel):
    id: str
    title: str
    provider_name: str
    organization: str
    url: str
    covered_skills: List[str]
    difficulty_level: str  # Beginner, Intermediate, Advanced
    access_type: AccessType
    certificate_included: bool
    estimated_hours: float
    is_verified: bool = True
    last_verified_date: str = "2026-10-31"
    description: str


# Authoritative, curated catalog of verified free and free-to-audit courses
VERIFIED_COURSE_CATALOG: List[CourseItem] = [
    CourseItem(
        id="fcc-docker",
        title="Docker Training Course for Beginners",
        provider_name="freeCodeCamp",
        organization="freeCodeCamp.org",
        url="https://www.freecodecamp.org/news/docker-training-tutorial-for-beginners/",
        covered_skills=["Docker", "Linux", "DevOps", "Containers"],
        difficulty_level="Beginner",
        access_type=AccessType.FREE_COURSE,
        certificate_included=True,
        estimated_hours=15.0,
        description="Comprehensive hands-on container training covering Docker Engine, Dockerfiles, Compose, and multi-container architectures."
    ),
    CourseItem(
        id="fcc-fastapi",
        title="FastAPI Tutorial for Beginners: Build High-Performance REST APIs",
        provider_name="freeCodeCamp",
        organization="freeCodeCamp.org",
        url="https://www.freecodecamp.org/news/fastapi-quickstart/",
        covered_skills=["FastAPI", "Python", "SQLAlchemy", "Pydantic", "REST APIs"],
        difficulty_level="Intermediate",
        access_type=AccessType.FREE_OPEN_ACCESS,
        certificate_included=False,
        estimated_hours=12.0,
        description="Interactive tutorial series teaching async FastAPI endpoints, Pydantic data schemas, SQLAlchemy ORM, and JWT authentication."
    ),
    CourseItem(
        id="fcc-python",
        title="Scientific Computing with Python Certification",
        provider_name="freeCodeCamp",
        organization="freeCodeCamp.org",
        url="https://www.freecodecamp.org/learn/scientific-computing-with-python/",
        covered_skills=["Python", "Data Structures", "Algorithms", "Object-Oriented Programming"],
        difficulty_level="Beginner",
        access_type=AccessType.FREE_COURSE,
        certificate_included=True,
        estimated_hours=30.0,
        description="Learn Python fundamentals, data structures, and build 5 required algorithmic projects to earn a verified zero-cost certificate."
    ),
    CourseItem(
        id="fcc-relational-db",
        title="Relational Database Certification (PostgreSQL & Bash)",
        provider_name="freeCodeCamp",
        organization="freeCodeCamp.org",
        url="https://www.freecodecamp.org/learn/relational-database/",
        covered_skills=["PostgreSQL", "SQL", "Linux", "Git", "Databases"],
        difficulty_level="Intermediate",
        access_type=AccessType.FREE_COURSE,
        certificate_included=True,
        estimated_hours=40.0,
        description="Interactive Linux container environment teaching PostgreSQL, SQL queries, Bash scripting, and Git repository management."
    ),
    CourseItem(
        id="redis-ru101",
        title="RU101: Introduction to Redis Data Structures",
        provider_name="Redis University",
        organization="Redis",
        url="https://university.redis.io/courses/ru101/",
        covered_skills=["Redis", "Caching", "Databases", "Distributed Systems"],
        difficulty_level="Beginner",
        access_type=AccessType.FREE_COURSE,
        certificate_included=True,
        estimated_hours=15.0,
        description="Official zero-cost certification course from Redis covering key-value data structures, hashing, TTLs, and caching design patterns."
    ),
    CourseItem(
        id="aws-skill-builder-cloud",
        title="AWS Cloud Practitioner Essentials",
        provider_name="AWS Skill Builder",
        organization="Amazon Web Services",
        url="https://explore.skillbuilder.aws/learn/course/external/view/elearning/134/aws-cloud-practitioner-essentials",
        covered_skills=["AWS", "Cloud Computing", "DevOps", "Infrastructure"],
        difficulty_level="Beginner",
        access_type=AccessType.FREE_OPEN_ACCESS,
        certificate_included=False,
        estimated_hours=12.0,
        description="Official interactive self-paced digital course directly from Amazon Web Services covering core AWS compute, storage, security, and architectural fundamentals."
    ),
    CourseItem(
        id="edx-k8s-intro",
        title="Introduction to Kubernetes (LFS158x)",
        provider_name="edX / Linux Foundation",
        organization="The Linux Foundation",
        url="https://www.edx.org/learn/kubernetes/the-linux-foundation-introduction-to-kubernetes",
        covered_skills=["Kubernetes", "Docker", "DevOps", "Containers"],
        difficulty_level="Beginner",
        access_type=AccessType.FREE_TO_AUDIT,
        certificate_included=False,
        estimated_hours=20.0,
        description="Official introductory course from the Linux Foundation covering Kubernetes architecture, Pods, Deployments, and cluster services."
    ),
    CourseItem(
        id="helsinki-fullstack",
        title="Full Stack Open (Modern Web Development with React & TypeScript)",
        provider_name="University of Helsinki",
        organization="University of Helsinki / Houston Inc.",
        url="https://fullstackopen.com/en/",
        covered_skills=["React", "TypeScript", "Node.js", "JavaScript", "GraphQL", "CI/CD"],
        difficulty_level="Intermediate",
        access_type=AccessType.FREE_COURSE,
        certificate_included=True,
        estimated_hours=60.0,
        description="Deep dive into modern JavaScript-based web development focusing on single page applications with React, REST APIs with Node.js, TypeScript, and CI/CD."
    ),
    CourseItem(
        id="angular-dev-tutorials",
        title="Official Angular Interactive Tutorials",
        provider_name="Angular Team",
        organization="Google",
        url="https://angular.dev/tutorials",
        covered_skills=["Angular", "TypeScript", "JavaScript", "Frontend"],
        difficulty_level="Intermediate",
        access_type=AccessType.FREE_OPEN_ACCESS,
        certificate_included=False,
        estimated_hours=14.0,
        description="In-browser hands-on interactive tutorials covering standalone components, Angular Signals, reactive forms, routing, and HTTP communication."
    ),
    CourseItem(
        id="ms-learn-ts",
        title="Build JavaScript Applications Using TypeScript",
        provider_name="Microsoft Learn",
        organization="Microsoft",
        url="https://learn.microsoft.com/en-us/training/paths/build-javascript-applications-typescript/",
        covered_skills=["TypeScript", "JavaScript"],
        difficulty_level="Intermediate",
        access_type=AccessType.FREE_OPEN_ACCESS,
        certificate_included=False,
        estimated_hours=12.0,
        description="Hands-on interactive path covering interfaces, classes, generics, and declaration files for TypeScript."
    ),
    CourseItem(
        id="hashicorp-terraform-tutorials",
        title="HashiCorp Terraform Developer Tutorials",
        provider_name="HashiCorp Learn",
        organization="HashiCorp",
        url="https://developer.hashicorp.com/terraform/tutorials",
        covered_skills=["Terraform", "Infrastructure as Code", "DevOps", "AWS"],
        difficulty_level="Intermediate",
        access_type=AccessType.FREE_OPEN_ACCESS,
        certificate_included=False,
        estimated_hours=16.0,
        description="Official guided labs and interactive tutorials teaching declarative infrastructure as code, state files, and cloud providers."
    ),
    CourseItem(
        id="scikit-learn-mooc",
        title="Machine Learning in Python with Scikit-Learn",
        provider_name="INRIA / France Université Numérique",
        organization="INRIA",
        url="https://www.inria.fr/en/scikit-learn-mooc",
        covered_skills=["Scikit-Learn", "Python", "Machine Learning", "Data Science"],
        difficulty_level="Intermediate",
        access_type=AccessType.FREE_OPEN_ACCESS,
        certificate_included=False,
        estimated_hours=24.0,
        description="Official MOOC built by the core developers of Scikit-Learn covering predictive modeling, pipelines, cross-validation, and hyperparameter tuning."
    ),
    CourseItem(
        id="linux-foundation-lfs101",
        title="Introduction to Linux (LFS101x)",
        provider_name="edX / Linux Foundation",
        organization="The Linux Foundation",
        url="https://www.edx.org/learn/linux/the-linux-foundation-introduction-to-linux",
        covered_skills=["Linux", "Git", "DevOps"],
        difficulty_level="Beginner",
        access_type=AccessType.FREE_TO_AUDIT,
        certificate_included=False,
        estimated_hours=25.0,
        description="Official introductory course from the Linux Foundation covering Linux command line, system architecture, and basic administration."
    ),
    CourseItem(
        id="harvard-cs50",
        title="CS50: Introduction to Computer Science",
        provider_name="edX / Harvard Online",
        organization="Harvard University",
        url="https://cs50.harvard.edu/x/",
        covered_skills=["C", "Python", "SQL", "Algorithms", "Data Structures"],
        difficulty_level="Beginner",
        access_type=AccessType.FREE_TO_AUDIT,
        certificate_included=False,
        estimated_hours=50.0,
        description="Harvard's introduction to computer science. Free access to all lectures, problem sets, and course materials."
    )
]


class BaseCourseProvider:
    """Provider interface for extensible course discovery sources."""
    def get_provider_name(self) -> str:
        raise NotImplementedError

    async def search_courses(self, skill: str, limit: int = 10) -> List[CourseItem]:
        raise NotImplementedError


class CuratedCourseProvider(BaseCourseProvider):
    def get_provider_name(self) -> str:
        return "curated_official_catalog"

    async def search_courses(self, skill: str, limit: int = 10) -> List[CourseItem]:
        norm = skill.lower().strip()
        matched = []
        for course in VERIFIED_COURSE_CATALOG:
            skill_match = any(norm == s.lower() or (len(norm) >= 4 and norm in s.lower()) for s in course.covered_skills)
            title_match = norm in course.title.lower()
            if skill_match or title_match:
                matched.append(course)
        return matched[:limit]


class CourseCatalogService:
    _providers: List[BaseCourseProvider] = [CuratedCourseProvider()]

    @classmethod
    def get_all_courses(cls) -> List[CourseItem]:
        return VERIFIED_COURSE_CATALOG

    @classmethod
    def get_courses_for_skill(cls, skill_name: str, limit: int = 4) -> List[CourseItem]:
        """
        Returns courses that strictly teach or support the specified skill.
        Strict relevance check: skill must match covered_skills or course title explicitly.
        """
        norm = skill_name.lower().strip()
        matched: List[CourseItem] = []
        for course in VERIFIED_COURSE_CATALOG:
            is_skill_covered = any(
                norm == s.lower() or (len(norm) >= 4 and norm in s.lower())
                for s in course.covered_skills
            )
            is_title_relevant = norm in course.title.lower()
            if is_skill_covered or is_title_relevant:
                matched.append(course)
        return matched[:limit]

    @classmethod
    async def find_courses_for_skills(
        cls,
        skills: List[str],
        access_type_filter: Optional[str] = None,
        difficulty_filter: Optional[str] = None,
        limit_per_skill: int = 3
    ) -> List[CourseItem]:
        results: Dict[str, CourseItem] = {}
        for skill in skills:
            found = cls.get_courses_for_skill(skill, limit=limit_per_skill)
            for item in found:
                if access_type_filter and item.access_type.name != access_type_filter and item.access_type.value != access_type_filter:
                    continue
                if difficulty_filter and item.difficulty_level.lower() != difficulty_filter.lower():
                    continue
                results[item.id] = item

        return list(results.values())
