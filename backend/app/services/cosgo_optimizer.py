import math
import re
from typing import List, Dict, Any, Set, Tuple, Optional


# Authoritative skills taxonomy with category, default effort (hours), uncertainty, and prerequisites
SKILL_TAXONOMY: Dict[str, Dict[str, Any]] = {
    # Programming Languages
    "python": {"canonical": "Python", "category": "languages", "effort": 35.0, "range": (25.0, 45.0), "prereqs": []},
    "javascript": {"canonical": "JavaScript", "category": "languages", "effort": 30.0, "range": (20.0, 40.0), "prereqs": []},
    "typescript": {"canonical": "TypeScript", "category": "languages", "effort": 20.0, "range": (14.0, 26.0), "prereqs": ["javascript"]},
    "java": {"canonical": "Java", "category": "languages", "effort": 40.0, "range": (30.0, 50.0), "prereqs": []},
    "c++": {"canonical": "C++", "category": "languages", "effort": 45.0, "range": (35.0, 55.0), "prereqs": []},
    "go": {"canonical": "Go", "category": "languages", "effort": 25.0, "range": (18.0, 32.0), "prereqs": []},
    "rust": {"canonical": "Rust", "category": "languages", "effort": 40.0, "range": (30.0, 50.0), "prereqs": []},
    "sql": {"canonical": "SQL", "category": "databases", "effort": 18.0, "range": (12.0, 24.0), "prereqs": []},
    "bash": {"canonical": "Bash / Shell", "category": "tools", "effort": 12.0, "range": (8.0, 16.0), "prereqs": []},

    # AI / Machine Learning Frameworks
    "pytorch": {"canonical": "PyTorch", "category": "ai_ml", "effort": 24.0, "range": (18.0, 30.0), "prereqs": ["python"]},
    "tensorflow": {"canonical": "TensorFlow", "category": "ai_ml", "effort": 25.0, "range": (18.0, 32.0), "prereqs": ["python"]},
    "scikit-learn": {"canonical": "Scikit-Learn", "category": "ai_ml", "effort": 14.0, "range": (10.0, 18.0), "prereqs": ["python"]},
    "pandas": {"canonical": "Pandas", "category": "ai_ml", "effort": 12.0, "range": (8.0, 16.0), "prereqs": ["python"]},
    "numpy": {"canonical": "NumPy", "category": "ai_ml", "effort": 10.0, "range": (6.0, 14.0), "prereqs": ["python"]},
    "huggingface": {"canonical": "HuggingFace Transformers", "category": "ai_ml", "effort": 18.0, "range": (12.0, 24.0), "prereqs": ["python", "pytorch"]},
    "langchain": {"canonical": "LangChain", "category": "ai_ml", "effort": 15.0, "range": (10.0, 20.0), "prereqs": ["python"]},
    "mlops": {"canonical": "MLOps", "category": "ai_ml", "effort": 22.0, "range": (16.0, 28.0), "prereqs": ["docker", "python"]},
    "nlp": {"canonical": "Natural Language Processing (NLP)", "category": "ai_ml", "effort": 20.0, "range": (15.0, 26.0), "prereqs": ["python"]},
    "computer vision": {"canonical": "Computer Vision", "category": "ai_ml", "effort": 22.0, "range": (16.0, 28.0), "prereqs": ["python"]},

    # Backend Frameworks
    "fastapi": {"canonical": "FastAPI", "category": "frameworks", "effort": 16.0, "range": (12.0, 20.0), "prereqs": ["python"]},
    "django": {"canonical": "Django", "category": "frameworks", "effort": 22.0, "range": (16.0, 28.0), "prereqs": ["python"]},
    "flask": {"canonical": "Flask", "category": "frameworks", "effort": 14.0, "range": (10.0, 18.0), "prereqs": ["python"]},
    "node.js": {"canonical": "Node.js", "category": "frameworks", "effort": 20.0, "range": (15.0, 25.0), "prereqs": ["javascript"]},
    "spring boot": {"canonical": "Spring Boot", "category": "frameworks", "effort": 28.0, "range": (20.0, 36.0), "prereqs": ["java"]},

    # Frontend Frameworks
    "react": {"canonical": "React", "category": "frontend", "effort": 22.0, "range": (16.0, 28.0), "prereqs": ["javascript"]},
    "angular": {"canonical": "Angular", "category": "frontend", "effort": 26.0, "range": (20.0, 32.0), "prereqs": ["typescript"]},
    "vue": {"canonical": "Vue.js", "category": "frontend", "effort": 18.0, "range": (12.0, 24.0), "prereqs": ["javascript"]},
    "html": {"canonical": "HTML5", "category": "frontend", "effort": 10.0, "range": (6.0, 14.0), "prereqs": []},
    "css": {"canonical": "CSS3", "category": "frontend", "effort": 12.0, "range": (8.0, 16.0), "prereqs": []},

    # Tools, Cloud & Infrastructure
    "docker": {"canonical": "Docker", "category": "tools", "effort": 14.0, "range": (10.0, 18.0), "prereqs": []},
    "kubernetes": {"canonical": "Kubernetes", "category": "tools", "effort": 26.0, "range": (20.0, 34.0), "prereqs": ["docker"]},
    "aws": {"canonical": "Amazon Web Services (AWS)", "category": "cloud", "effort": 25.0, "range": (18.0, 32.0), "prereqs": []},
    "gcp": {"canonical": "Google Cloud Platform (GCP)", "category": "cloud", "effort": 24.0, "range": (18.0, 30.0), "prereqs": []},
    "azure": {"canonical": "Microsoft Azure", "category": "cloud", "effort": 24.0, "range": (18.0, 30.0), "prereqs": []},
    "git": {"canonical": "Git / GitHub", "category": "tools", "effort": 8.0, "range": (5.0, 12.0), "prereqs": []},
    "ci/cd": {"canonical": "CI/CD Pipelines", "category": "tools", "effort": 14.0, "range": (10.0, 18.0), "prereqs": ["git"]},
    "linux": {"canonical": "Linux Administration", "category": "tools", "effort": 16.0, "range": (12.0, 22.0), "prereqs": []},

    # Databases & Big Data
    "postgresql": {"canonical": "PostgreSQL", "category": "databases", "effort": 16.0, "range": (12.0, 22.0), "prereqs": ["sql"]},
    "mongodb": {"canonical": "MongoDB", "category": "databases", "effort": 14.0, "range": (10.0, 18.0), "prereqs": []},
    "redis": {"canonical": "Redis", "category": "databases", "effort": 10.0, "range": (7.0, 14.0), "prereqs": []},
    "spark": {"canonical": "Apache Spark", "category": "data_engineering", "effort": 24.0, "range": (18.0, 30.0), "prereqs": ["python"]},
    "kafka": {"canonical": "Apache Kafka", "category": "data_engineering", "effort": 20.0, "range": (15.0, 26.0), "prereqs": []},
}

# Verifiable public documentation and tutorial URLs (Official sources only)
VERIFIED_RESOURCES: Dict[str, List[Dict[str, Any]]] = {
    "python": [
        {"title": "The Python Tutorial", "url": "https://docs.python.org/3/tutorial/", "provider": "Python Software Foundation", "is_verified": True, "resource_type": "Official Tutorial"}
    ],
    "pytorch": [
        {"title": "PyTorch Learn the Basics", "url": "https://pytorch.org/tutorials/beginner/basics/intro.html", "provider": "PyTorch Foundation", "is_verified": True, "resource_type": "Official Interactive Guide"}
    ],
    "fastapi": [
        {"title": "FastAPI Tutorial - User Guide", "url": "https://fastapi.tiangolo.com/tutorial/", "provider": "FastAPI Official Documentation", "is_verified": True, "resource_type": "Official Guide"}
    ],
    "docker": [
        {"title": "Docker Hands-On Getting Started Guide", "url": "https://docs.docker.com/get-started/", "provider": "Docker Inc.", "is_verified": True, "resource_type": "Official Documentation"}
    ],
    "kubernetes": [
        {"title": "Learn Kubernetes Basics", "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/", "provider": "Cloud Native Computing Foundation (CNCF)", "is_verified": True, "resource_type": "Official Interactive Tutorial"}
    ],
    "react": [
        {"title": "React: Quick Start & Describing the UI", "url": "https://react.dev/learn", "provider": "React Team (Meta)", "is_verified": True, "resource_type": "Official Documentation"}
    ],
    "angular": [
        {"title": "Angular Official First App Tutorial", "url": "https://angular.dev/tutorials/first-app", "provider": "Google Angular Team", "is_verified": True, "resource_type": "Official Hands-on Tutorial"}
    ],
    "typescript": [
        {"title": "TypeScript for JavaScript Programmers", "url": "https://www.typescriptlang.org/docs/handbook/typescript-in-5-minutes.html", "provider": "Microsoft", "is_verified": True, "resource_type": "Official Handbook"}
    ],
    "postgresql": [
        {"title": "PostgreSQL Tutorial", "url": "https://www.postgresql.org/docs/current/tutorial.html", "provider": "PostgreSQL Global Development Group", "is_verified": True, "resource_type": "Official Documentation"}
    ],
    "sql": [
        {"title": "SQL Tutorial and Language Reference", "url": "https://www.postgresql.org/docs/current/tutorial-sql.html", "provider": "PostgreSQL Official Docs", "is_verified": True, "resource_type": "Official Reference"}
    ],
    "scikit-learn": [
        {"title": "An Introduction to Machine Learning with scikit-learn", "url": "https://scikit-learn.org/stable/tutorial/basic/tutorial.html", "provider": "scikit-learn Developers", "is_verified": True, "resource_type": "Official Tutorial"}
    ],
    "redis": [
        {"title": "Get Started with Redis", "url": "https://redis.io/docs/latest/develop/get-started/", "provider": "Redis Ltd.", "is_verified": True, "resource_type": "Official Documentation"}
    ],
    "aws": [
        {"title": "AWS Cloud Foundations and Tutorials", "url": "https://aws.amazon.com/getting-started/", "provider": "Amazon Web Services", "is_verified": True, "resource_type": "Official Getting Started Guide"}
    ],
    "langchain": [
        {"title": "Introduction to LangChain", "url": "https://python.langchain.com/docs/get_started/introduction", "provider": "LangChain Official Docs", "is_verified": True, "resource_type": "Official Documentation"}
    ]
}

# Authoritative algorithm version identifier
COSGO_ALGORITHM_VERSION = "cosgo-v1.2-audited"

# Curated alias dictionary mapping variations to taxonomy keys
SKILL_ALIASES: Dict[str, str] = {
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "reactjs": "react",
    "react.js": "react",
    "react": "react",
    "angularjs": "angular",
    "angular.js": "angular",
    "angular": "angular",
    "nodejs": "node.js",
    "node.js": "node.js",
    "node": "node.js",
    "golang": "go",
    "go": "go",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "aws services": "aws",
    "amazon web services": "aws",
    "amazon web services (aws)": "aws",
    "aws": "aws",
    "gcp services": "gcp",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "google cloud platform (gcp)": "gcp",
    "gcp": "gcp",
    "azure cloud": "azure",
    "ms azure": "azure",
    "microsoft azure": "azure",
    "azure": "azure",
    "python3": "python",
    "python 3": "python",
    "python": "python",
    "ci cd": "ci/cd",
    "cicd": "ci/cd",
    "ci/cd": "ci/cd",
    "ci/cd pipelines": "ci/cd",
    "shell": "bash",
    "sh": "bash",
    "bash": "bash",
    "bash / shell": "bash",
    "hugging face": "huggingface",
    "huggingface": "huggingface",
    "huggingface transformers": "huggingface",
    "nlp": "nlp",
    "natural language processing": "nlp",
    "natural language processing (nlp)": "nlp",
    "vue.js": "vue",
    "vuejs": "vue",
    "vue": "vue",
    "html5": "html",
    "html": "html",
    "css3": "css",
    "css": "css",
    "git / github": "git",
    "git / git hub": "git",
    "github": "git",
    "git": "git",
    "linux administration": "linux",
    "linux": "linux",
    "apache spark": "spark",
    "spark": "spark",
    "apache kafka": "kafka",
    "kafka": "kafka",
    "scikit-learn": "scikit-learn",
    "scikitlearn": "scikit-learn",
    "sklearn": "scikit-learn",
    "spring": "spring boot",
    "springboot": "spring boot",
    "spring boot": "spring boot",
    "fast api": "fastapi",
    "fastapi": "fastapi",
    "mongo": "mongodb",
    "mongodb": "mongodb",
    "pytorch": "pytorch",
    "tensorflow": "tensorflow",
    "pandas": "pandas",
    "numpy": "numpy",
    "langchain": "langchain",
    "mlops": "mlops",
    "computer vision": "computer vision",
    "cv": "computer vision",
    "django": "django",
    "flask": "flask",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "java": "java",
    "c++": "c++",
    "cpp": "c++",
    "rust": "rust",
    "sql": "sql",
    "redis": "redis",
}

# Prebuilt bidirectional lookup index:
# Maps taxonomy keys, canonical display names (lowercase), and aliases -> taxonomy key
_TAXONOMY_LOOKUP: Dict[str, str] = {}
for _k, _entry in SKILL_TAXONOMY.items():
    _TAXONOMY_LOOKUP[_k.lower()] = _k
    _TAXONOMY_LOOKUP[_entry["canonical"].lower()] = _k
for _alias, _target_key in SKILL_ALIASES.items():
    if _target_key in SKILL_TAXONOMY:
        _TAXONOMY_LOOKUP[_alias.lower()] = _target_key


class CosgoOptimizer:
    r"""
    Cross-Opportunity Skill Gap Optimization (COSGO) Engine.

    MATHEMATICAL FORMULATION & RESEARCH SPECIFICATION:
    Let J be the set of eligible target opportunities. For each opportunity j in J:
    - R_j is the non-empty set of canonical required skills.
    - w_j in [0, 1] is the normalized opportunity importance weight (sum_{j in J} w_j == 1.0 within 1e-6).
    - V is the candidate's verified skill set.
    - M_j = R_j \setminus V is the set of unmet/missing skills for opportunity j.

    For an acquired skill selection S subseteq U \setminus V:
    The requirement coverage for opportunity j is:
        Cov(j, S) = |(V union S) cap R_j| / |R_j| = |V cap R_j| / |R_j| + |S cap M_j| / |R_j|

    The global weighted coverage objective is:
        f(S) = sum_{j in J} w_j * Cov(j, S) = BaselineCoverage(V) + sum_{s in S} c_s
    where the marginal coverage coefficient for skill s is:
        c_s = sum_{j in J : s in M_j} (w_j / |R_j|)

    MATHEMATICAL CLASSIFICATION:
    1. Modular Objective: Over independent skill selections, f(S) is modular (additive).
    2. Precedence Constraints: Skills have directed prerequisite dependencies; a valid selection
       must be prerequisite-closed: for all s in S, prereqs(s) subseteq V union S.
    3. Knapsack Budget Constraint: Total modeled learning effort sum_{s in S} e_s <= B.
    COSGO solves this Precedence-Constrained Knapsack problem via an explainable greedy
    prerequisite-bundling heuristic with strict tie-breaking.
    """

    @staticmethod
    def find_taxonomy_key(skill_name: str) -> Optional[str]:
        """
        Resolves a skill name, canonical title, or alias to its authoritative taxonomy key.
        Handles casing, whitespace, punctuation variants, and canonical display names.
        """
        if not skill_name:
            return None
        clean = skill_name.strip().lower()
        if clean in _TAXONOMY_LOOKUP:
            return _TAXONOMY_LOOKUP[clean]
        # Punctuation-tolerant fallback
        simplified = re.sub(r'[^a-z0-9+#/.]+', ' ', clean).strip()
        if simplified in _TAXONOMY_LOOKUP:
            return _TAXONOMY_LOOKUP[simplified]
        return None

    @staticmethod
    def normalize_skill_name(raw_name: str) -> str:
        """
        Standardizes skill casing, aliases, and naming to its canonical taxonomy form.
        If skill is not present in the authoritative taxonomy, formats using title casing.
        """
        clean = (raw_name or "").strip()
        if not clean:
            return ""
        tax_key = CosgoOptimizer.find_taxonomy_key(clean)
        if tax_key and tax_key in SKILL_TAXONOMY:
            return SKILL_TAXONOMY[tax_key]["canonical"]
        return clean.title()

    @staticmethod
    def get_all_prerequisites(skill_name: str) -> List[str]:
        """
        Recursively retrieves all prerequisites in strict topological order (foundations first).
        Resolves prerequisite names whether passed as keys, aliases, or canonical display names.
        Guarantees that every dependency appears before the dependent skill and detects cycles.
        """
        tax_key = CosgoOptimizer.find_taxonomy_key(skill_name)
        if not tax_key or tax_key not in SKILL_TAXONOMY:
            return []

        ordered: List[str] = []
        visited: Set[str] = set()
        visiting: Set[str] = set()

        def dfs(curr_key: str):
            if curr_key in visiting:
                return  # Cycle prevention
            visiting.add(curr_key)
            entry = SKILL_TAXONOMY.get(curr_key)
            if entry:
                for p in entry.get("prereqs", []):
                    p_key = CosgoOptimizer.find_taxonomy_key(p)
                    if p_key and p_key not in visited:
                        dfs(p_key)
                        p_canonical = SKILL_TAXONOMY[p_key]["canonical"]
                        if p_canonical not in ordered:
                            ordered.append(p_canonical)
                        visited.add(p_key)
            visiting.remove(curr_key)

        dfs(tax_key)
        return ordered

    @staticmethod
    def get_skill_metadata(
        skill_name: str,
        has_partial_evidence: bool = False,
        inferred_discount: float = 0.30
    ) -> Dict[str, Any]:
        """
        Retrieves canonical name, category, estimated hours, uncertainty, and prerequisites.
        Resolves skills whether passed as canonical names, taxonomy keys, or aliases.
        Applies documented, explicit discount if candidate has partial evidence (e.g. INFERRED status).

        Exact Applicability Conditions:
        1. Condition 1 (Absent or Unverified Background):
           has_partial_evidence == False.
           Discount factor = 0.0. Full standard curriculum effort is required.
        2. Condition 2 (Inferred Evidence):
           has_partial_evidence == True (e.g. skill in inferred_skills).
           Discount factor = inferred_discount (default 0.30, bounded in [0.0, 0.60]).
           Adjusted effort = round(base_effort * (1.0 - discount_factor), 1).
           CRITICAL VERIFICATION BOUNDARY:
           Inferred status represents documented conceptual familiarity, lowering the modeled learning
           hours to achieve mastery. However, inferred skills CANNOT satisfy prerequisite requirements
           for dependent skills, and CANNOT count towards baseline coverage.
        3. Explicit Modeled Estimation:
           All effort hours represent conditional modeled curriculum projections,
           not guaranteed completion durations or empirical trial hours.
        """
        tax_key = CosgoOptimizer.find_taxonomy_key(skill_name)
        if tax_key and tax_key in SKILL_TAXONOMY:
            tax = SKILL_TAXONOMY[tax_key]
            canonical = tax["canonical"]
            category = tax["category"]
            base_effort = float(tax["effort"])
            r_min, r_max = tax["range"]
            prereqs = [
                SKILL_TAXONOMY[CosgoOptimizer.find_taxonomy_key(p)]["canonical"]
                for p in tax.get("prereqs", [])
                if CosgoOptimizer.find_taxonomy_key(p)
            ]
            is_known = True
        else:
            canonical = CosgoOptimizer.normalize_skill_name(skill_name)
            category = "technical"
            base_effort = 16.0
            r_min, r_max = (10.0, 22.0)
            prereqs = []
            is_known = False

        # Explicit discounted effort model for candidate skills with partial or inferred background
        discount_factor = max(0.0, min(0.60, inferred_discount)) if has_partial_evidence else 0.0
        adjusted_effort = round(base_effort * (1.0 - discount_factor), 1)
        adjusted_min = round(r_min * (1.0 - discount_factor), 1)
        adjusted_max = round(r_max * (1.0 - discount_factor), 1)

        if not is_known:
            uncertainty_note = f"Modeled estimate for uncataloged skill: Conservative default curriculum baseline ({adjusted_effort}h). Not in authoritative taxonomy."
        elif has_partial_evidence:
            uncertainty_note = (
                f"Modeled curriculum estimate with {round(discount_factor * 100)}% partial-evidence discount. "
                f"Discount applies consistently to base effort ({base_effort}h -> {adjusted_effort}h) and "
                f"modeled uncertainty bounds ([{r_min}h, {r_max}h] -> [{adjusted_min}h, {adjusted_max}h]). "
                "Modeled projection, not a guaranteed completion duration. Inferred conceptual exposure lowers "
                "modeled study hours but does NOT constitute verified proficiency or satisfy prerequisites."
            )
        else:
            uncertainty_note = "Standard curriculum modeled estimate based on comprehensive competency mastery. Modeled projection, not a guaranteed completion duration."

        return {
            "canonical": canonical,
            "category": category,
            "estimated_hours": adjusted_effort,
            "is_known_in_taxonomy": is_known,
            "uncertainty_range": {
                "min_hours": adjusted_min,
                "max_hours": adjusted_max,
                "base_min_hours": r_min,
                "base_max_hours": r_max,
                "base_range": (r_min, r_max),
                "discounted_range": (adjusted_min, adjusted_max),
                "is_discounted": has_partial_evidence,
                "discount_factor": discount_factor,
                "range_interpretation": "POST_DISCOUNT_SCALED" if has_partial_evidence else "STANDARD_PRE_DISCOUNT",
                "point_estimate_in_range": adjusted_min <= adjusted_effort <= adjusted_max,
                "confidence": "moderate" if is_known else "low",
                "notes": uncertainty_note
            },
            "prerequisites": prereqs,
            "all_prerequisites": CosgoOptimizer.get_all_prerequisites(canonical),
            "effort_model": {
                "base_hours": base_effort,
                "base_range": (r_min, r_max),
                "has_partial_evidence": has_partial_evidence,
                "discount_factor": discount_factor,
                "discounted_hours": adjusted_effort,
                "adjusted_hours": adjusted_effort,
                "discounted_range": (adjusted_min, adjusted_max),
                "point_estimate_in_discounted_range": adjusted_min <= adjusted_effort <= adjusted_max,
                "is_known_in_taxonomy": is_known,
                "effort_nature": "CURRICULUM_MODELED_PROJECTION",
                "verification_semantic": "INFERRED_SKILL_PARTIAL_EVIDENCE_DISCOUNT_ONLY" if has_partial_evidence else "STANDARD_FULL_EFFORT",
                "notes": uncertainty_note
            }
        }

    @staticmethod
    def calculate_opportunity_weight(
        role_relevance: Optional[float] = None,
        verification_confidence: Optional[float] = None,
        match_score: Optional[float] = None
    ) -> float:
        """
        Calibrated, bounded raw opportunity importance score s_j in [0.06, 1.0].
        s_j = role_relevance * (0.60 + 0.20 * verification_confidence + 0.20 * match_score)
        
        Where:
        - role_relevance in [0.10, 1.0] (defaults to 0.50)
        - verification_confidence in [0.0, 1.0] (defaults to 0.85)
        - match_score in [0.0, 1.0] (defaults to 0.50)
        
        Theoretical raw bounds:
        min: 0.10 * (0.60 + 0.0 + 0.0) = 0.06
        max: 1.00 * (0.60 + 0.20 + 0.20) = 1.00
        """
        r_val = 0.50 if role_relevance is None else float(role_relevance)
        v_val = 0.85 if verification_confidence is None else float(verification_confidence)
        m_val = 0.50 if match_score is None else float(match_score)

        r_rel = max(0.10, min(1.0, r_val))
        v_conf = max(0.0, min(1.0, v_val))
        m_score = max(0.0, min(1.0, m_val))

        weight = r_rel * (0.60 + 0.20 * v_conf + 0.20 * m_score)
        return round(weight, 4)

    @staticmethod
    def normalize_opportunity_weights(
        raw_weights: List[float],
        tolerance: float = 1e-6
    ) -> List[float]:
        """
        Mathematically valid, deterministic simplex normalization for arbitrary opportunity counts N >= 1.
        
        Mathematical Formulation:
        Let s_j in [0.06, 1.0] be the raw importance score of opportunity j in {1, ..., N}.
        The normalized opportunity weight \\bar{w}_j is:
            \\bar{w}_j = s_j / \\sum_{k=1}^N s_k
            
        Properties across arbitrary opportunity counts N:
        1. Universal domain: Valid for any N >= 1 (e.g. 1, 5, 16, 17, 100, 1000+).
        2. Nonnegativity & Positivity: Since s_j >= 0.06 > 0, every \\bar{w}_j > 0 strictly.
        3. Partition of unity: \\sum_{j=1}^N \\bar{w}_j == 1.0 within numerical tolerance (<= 1e-6).
        4. Invariant relative priority: If s_A / s_B = c, then \\bar{w}_A / \\bar{w}_B = c for all N.
        5. Resolution of the N > 16 incompatibility:
           The constant lower bound 0.06 applies strictly to raw importance scores s_j in [0.06, 1.00].
           Imposing \\bar{w}_j >= 0.06 on normalized weights is mathematically impossible for N >= 17
           (17 * 0.06 = 1.02 > 1.0). The exact lower bound for normalized weights is:
               \\bar{w}_j >= s_min / \\sum s_k >= 0.06 / (N * 1.0) = 0.06 / N > 0.
        """
        if not raw_weights:
            return []
            
        # Ensure finite and non-negative
        clean_weights = []
        for w in raw_weights:
            val = float(w) if (w is not None and not (isinstance(w, float) and (math.isnan(w) or math.isinf(w)))) else 0.06
            clean_weights.append(max(0.0001, val))
            
        total = sum(clean_weights)
        if total <= 0:
            n = len(clean_weights)
            return [round(1.0 / n, 7)] * n
            
        normalized = [round(w / total, 7) for w in clean_weights]
        
        # Ensure exact sum to 1.0 within tolerance by adjusting the residual onto the largest weight
        diff = round(1.0 - sum(normalized), 7)
        if abs(diff) > 0:
            max_idx = clean_weights.index(max(clean_weights))
            normalized[max_idx] = round(normalized[max_idx] + diff, 7)
            
        # Final sanity assertion
        assert abs(sum(normalized) - 1.0) <= tolerance, f"Normalized weights sum {sum(normalized)} violates tolerance {tolerance}"
        return normalized


    @staticmethod
    def make_opportunity_signature(opp: Dict[str, Any]) -> str:
        """
        Generates robust opportunity signature to eliminate duplicate listings
        without erroneously collapsing distinct jobs across locations or requisition IDs.
        """
        req_id = (opp.get("requisition_id") or opp.get("req_id") or "").strip().lower()
        url = (opp.get("primary_url") or opp.get("url") or "").strip().lower()
        if url:
            url_clean = re.sub(r'[?#].*$', '', url).rstrip('/')
        else:
            url_clean = ""

        title = (opp.get("title") or "").strip().lower()
        company = (opp.get("company_name") or opp.get("company") or "").strip().lower()
        location = (opp.get("location") or opp.get("city") or "").strip().lower()

        # Priority 1: Explicit requisition ID
        if req_id:
            return f"req::{company}::{req_id}"
        # Priority 2: Canonical URL
        if url_clean:
            return f"url::{url_clean}"
        # Priority 3: Title + Company + Location
        if location:
            return f"loc::{company}::{title}::{location}"
        # Priority 4: Fallback to Title + Company
        return f"basic::{company}::{title}"

    @staticmethod
    def evaluate_coverage_metrics(
        eligible_jobs: List[Dict[str, Any]],
        selected_skills: List[str],
        verified_canonical: Set[str]
    ) -> Dict[str, Any]:
        """
        Authoritative shared coverage and gain scoring function across COSGO,
        all heuristic baselines, and the exact optimization oracle.

        Guarantees:
        1. Full double-precision internal calculation across opportunity requirement sets.
        2. Inferred skills do NOT count toward baseline coverage (only verified skills).
        3. Identical inputs and identical selected skills obtain identical baseline coverage,
           final coverage, and marginal gain across all algorithms.
        4. Output values are rounded only for display to 4 decimal places (0.01% precision),
           with exact reconciliation: ProjectedCoverage == BaselineCoverage + MarginalGain.
        """
        selected_set = {CosgoOptimizer.normalize_skill_name(s).lower() for s in selected_skills if s and s.strip()}
        verified_set = {s.lower() for s in verified_canonical if s and s.strip()}
        mastered_set = verified_set.union(selected_set)

        raw_base_cov = 0.0
        raw_final_cov = 0.0
        qualifying_base_count = 0
        qualifying_final_count = 0
        improved_opps_count = 0

        # Check if normalized weights are already present; if not, calculate deterministically
        has_weights = all("normalized_weight" in j for j in eligible_jobs) if eligible_jobs else False
        if not has_weights and eligible_jobs:
            raw_weights = [
                CosgoOptimizer.calculate_opportunity_weight(
                    j.get("role_relevance"), j.get("verification_confidence"), j.get("match_score")
                )
                for j in eligible_jobs
            ]
            norm_weights = CosgoOptimizer.normalize_opportunity_weights(raw_weights)
        else:
            norm_weights = [j["normalized_weight"] for j in eligible_jobs]

        for idx, j in enumerate(eligible_jobs):
            reqs = [r.lower() for r in j["requirements"]]
            w = norm_weights[idx]
            req_len = len(reqs)
            if req_len == 0:
                continue

            base_matches = sum(1 for r in reqs if r in verified_set)
            final_matches = sum(1 for r in reqs if r in mastered_set)

            base_frac = base_matches / req_len
            final_frac = final_matches / req_len

            raw_base_cov += w * base_frac
            raw_final_cov += w * final_frac

            if base_frac >= 0.75:
                qualifying_base_count += 1
            if final_frac >= 0.75:
                qualifying_final_count += 1
            if final_matches > base_matches:
                improved_opps_count += 1

        raw_gain = max(0.0, raw_final_cov - raw_base_cov)

        disp_base = round(raw_base_cov, 4)
        disp_final = round(raw_final_cov, 4)
        disp_gain = round(disp_final - disp_base, 4)

        return {
            "raw_baseline_coverage": raw_base_cov,
            "raw_final_coverage": raw_final_cov,
            "raw_marginal_gain": raw_gain,
            "baseline_coverage": disp_base,
            "final_coverage": disp_final,
            "marginal_coverage_increase": disp_gain,
            "coverage_gain": disp_gain,
            "coverage_gain_pp": round(disp_gain * 100, 2),
            "qualifying_count_baseline": qualifying_base_count,
            "qualifying_count_final": qualifying_final_count,
            "unique_opportunities_improved": improved_opps_count,
        }

    @staticmethod
    def optimize(
        opportunities: List[Dict[str, Any]],
        verified_skills: Set[str],
        inferred_skills: Set[str],
        budget_hours: float = 40.0,
        weekly_budget_hours: float = 10.0,
        inferred_discount: float = 0.30
    ) -> Dict[str, Any]:
        """
        Executes COSGO explainable greedy maximum coverage algorithm with:
        1. Exact canonical requirement deduplication.
        2. Strict hierarchical prerequisite bundling (no action scheduled before prerequisites).
        3. Strict budget adherence (total effort <= budget).
        4. Honest verification boundaries (unverified/inferred skills never silently count in baseline).
        5. Unrelated verified skills do not award credit to jobs that do not require them.
        """
        # Canonicalize candidate skills
        verified_canonical = {CosgoOptimizer.normalize_skill_name(s) for s in verified_skills if s and s.strip()}
        verified_lower = {s.lower() for s in verified_canonical}

        inferred_canonical = {
            CosgoOptimizer.normalize_skill_name(s) for s in inferred_skills
            if s and s.strip() and CosgoOptimizer.normalize_skill_name(s).lower() not in verified_lower
        }
        inferred_lower = {s.lower() for s in inferred_canonical}

        # 1. Dataset Validation & Accounting
        eligible_jobs: List[Dict[str, Any]] = []
        excluded_jobs: List[Dict[str, Any]] = []
        seen_job_signatures = set()

        for opp in opportunities:
            opp_id = opp.get("id")
            title = (opp.get("title") or "").strip()
            company = (opp.get("company_name") or "").strip()
            sig = CosgoOptimizer.make_opportunity_signature(opp)

            # Deduplication
            if sig in seen_job_signatures:
                excluded_jobs.append({"id": opp_id, "title": title, "reason": "DUPLICATE_LISTING"})
                continue
            seen_job_signatures.add(sig)

            # Check validity & Canonicalize requirements
            raw_reqs = opp.get("requirements") or set()
            canon_reqs: Set[str] = set()
            for r in raw_reqs:
                if isinstance(r, str) and len(r.strip()) > 1:
                    canon_name = CosgoOptimizer.normalize_skill_name(r)
                    if canon_name:
                        canon_reqs.add(canon_name)

            if not canon_reqs:
                excluded_jobs.append({"id": opp_id, "title": title, "reason": "INSUFFICIENT_REQUIREMENTS"})
                continue

            r_rel = opp.get("role_relevance")
            v_conf = opp.get("verification_confidence")
            m_score = opp.get("match_score")
            w_j = CosgoOptimizer.calculate_opportunity_weight(r_rel, v_conf, m_score)

            # Demonstrated verified skills strictly present in this job's requirements
            demonstrated = {r for r in canon_reqs if r.lower() in verified_lower}
            # Missing requirements
            missing = canon_reqs - demonstrated
            # Inferred partial overlap (for curriculum discount, never for baseline coverage)
            partial = {r for r in missing if r.lower() in inferred_lower}

            eligible_jobs.append({
                "id": opp_id,
                "title": title,
                "company_name": company,
                "primary_url": opp.get("primary_url", ""),
                "requirements": canon_reqs,
                "demonstrated": demonstrated,
                "partial": partial,
                "missing": missing,
                "weight": w_j,
                "role_relevance": float(r_rel) if r_rel is not None else 0.50,
                "match_score": float(m_score) if m_score is not None else 0.50
            })

        total_weight = sum(j["weight"] for j in eligible_jobs)
        if not eligible_jobs or total_weight <= 0:
            return {
                "status": "INSUFFICIENT_DATA",
                "message": "Insufficient eligible opportunities with structured requirements for optimization.",
                "total_opportunities_analyzed": len(opportunities),
                "eligible_opportunities_count": 0,
                "excluded_opportunities_count": len(excluded_jobs),
                "excluded_details": excluded_jobs,
                "actions": [],
                "baseline_coverage": 0.0,
                "projected_coverage": 0.0,
                "marginal_coverage_increase": 0.0,
                "opportunities_at_threshold_baseline": 0,
                "opportunities_at_threshold_projected": 0,
                "coverage_matrix": {"total_skills_count": 0, "skills_header": [], "matrix": [], "skill_frequency": {}},
                "opportunity_weights_used": {},
                "diagnostics": {
                    "excluded_breakdown": {
                        "duplicate_listings": sum(1 for e in excluded_jobs if e["reason"] == "DUPLICATE_LISTING"),
                        "insufficient_requirements": sum(1 for e in excluded_jobs if e["reason"] == "INSUFFICIENT_REQUIREMENTS"),
                    },
                    "total_candidate_verified_skills": len(verified_canonical),
                    "total_candidate_inferred_skills": len(inferred_canonical),
                    "budget_hours_requested": budget_hours,
                    "budget_hours_used": 0.0,
                    "budget_hours_remaining": budget_hours,
                    "weekly_budget_hours": weekly_budget_hours,
                    "study_pace_weeks": round(budget_hours / weekly_budget_hours, 1) if weekly_budget_hours > 0 else 1.0,
                    "inferred_discount_factor": inferred_discount,
                    "prerequisite_enforcement": "STRICT_HIERARCHICAL_BUNDLING",
                    "algorithm_version": COSGO_ALGORITHM_VERSION,
                    "mathematical_model": "Precedence-Constrained Knapsack with Modular Coverage Benefit",
                    "effort_nature": "CURRICULUM_MODELED_PROJECTION",
                    "is_employment_guarantee": False,
                    "modeled_projection_note": "Coverage figures are conditional modeled projections assuming full demonstration and mastery of recommended actions. They do not constitute an offer, employment guarantee, or interview commitment."
                }
            }

        # Compute normalized weights using deterministic simplex normalization (sum = 1.0 within tolerance)
        raw_weights = [j["weight"] for j in eligible_jobs]
        norm_weights = CosgoOptimizer.normalize_opportunity_weights(raw_weights)
        for idx, j in enumerate(eligible_jobs):
            j["normalized_weight"] = norm_weights[idx]

        weights_used_map = {
            str(j["id"] or f"job-{idx}"): j["normalized_weight"]
            for idx, j in enumerate(eligible_jobs)
        }

        # 2. Baseline Coverage Calculation
        # Coverage(j, \emptyset) = |Demonstrated_j| / |Requirements_j| = |R_j \cap V| / |R_j|
        baseline_weighted_sum = 0.0
        baseline_qualifying_count = 0
        for j in eligible_jobs:
            req_count = len(j["requirements"])
            base_cov = len(j["demonstrated"]) / req_count if req_count > 0 else 0.0
            j["baseline_coverage"] = round(base_cov, 4)
            baseline_weighted_sum += j["normalized_weight"] * base_cov
            if base_cov >= 0.75:
                baseline_qualifying_count += 1

        baseline_coverage_overall = baseline_weighted_sum

        # 3. Action Candidate Pool Construction
        # S = union of all missing requirements across eligible jobs
        all_missing_skills: Set[str] = set()
        for j in eligible_jobs:
            all_missing_skills.update(j["missing"])

        # Precompute skill metadata for all missing skills and their recursive prerequisites
        skill_info: Dict[str, Dict[str, Any]] = {}
        skills_to_inspect = set(all_missing_skills)
        while skills_to_inspect:
            s_name = skills_to_inspect.pop()
            if s_name not in skill_info:
                is_partial = s_name.lower() in inferred_lower
                info = CosgoOptimizer.get_skill_metadata(s_name, is_partial, inferred_discount)
                skill_info[s_name] = info
                # Also ensure all prerequisites are in skill_info
                for p in info.get("all_prerequisites", []):
                    if p not in skill_info:
                        skills_to_inspect.add(p)

        # 4. Strict Prerequisite-Enforced Budgeted Greedy Algorithm
        selected_actions: List[Dict[str, Any]] = []
        action_unrounded_gains: List[float] = []
        covered_skills: Set[str] = set(verified_canonical)
        remaining_budget = float(budget_hours)
        current_cumulative_coverage = baseline_coverage_overall
        rank = 1

        while remaining_budget > 0:
            best_bundle = None
            best_efficiency = -1.0
            best_bundle_gain = 0.0
            best_bundle_effort = 0.0

            # Evaluate each missing skill not yet covered
            uncovered_candidates = sorted([s for s in all_missing_skills if s not in covered_skills])
            if not uncovered_candidates:
                break

            for s_cand in uncovered_candidates:
                # Determine all unmet prerequisites for s_cand
                all_prereqs = skill_info[s_cand].get("all_prerequisites", [])
                unmet_prereqs = [p for p in all_prereqs if p not in covered_skills]

                # Full candidate bundle in dependency order: prerequisites first, then s_cand
                bundle = unmet_prereqs + [s_cand]
                bundle_effort = sum(skill_info[k]["estimated_hours"] for k in bundle)

                # Budget constraint check
                if bundle_effort > remaining_budget or bundle_effort <= 0:
                    continue

                # Compute marginal coverage gain of adding this bundle
                # For each job j, coverage gain is |(M_j \setminus covered) \cap bundle| / |R_j|
                bundle_set = set(bundle)
                bundle_gain = 0.0
                for j in eligible_jobs:
                    newly_satisfied_in_j = sum(
                        1 for k in bundle_set
                        if k in j["missing"] and k not in covered_skills
                    )
                    if newly_satisfied_in_j > 0:
                        bundle_gain += j["normalized_weight"] * (newly_satisfied_in_j / len(j["requirements"]))

                if bundle_gain <= 0:
                    continue

                efficiency = bundle_gain / bundle_effort

                # Deterministic selection with tie-breaking
                if efficiency > best_efficiency + 1e-9:
                    best_efficiency = efficiency
                    best_bundle = bundle
                    best_bundle_gain = bundle_gain
                    best_bundle_effort = bundle_effort
                elif abs(efficiency - best_efficiency) <= 1e-9:
                    # Tie-break 1: higher bundle gain
                    if bundle_gain > best_bundle_gain + 1e-9:
                        best_efficiency = efficiency
                        best_bundle = bundle
                        best_bundle_gain = bundle_gain
                        best_bundle_effort = bundle_effort
                    elif abs(bundle_gain - best_bundle_gain) <= 1e-9:
                        # Tie-break 2: lower effort
                        if bundle_effort < best_bundle_effort:
                            best_efficiency = efficiency
                            best_bundle = bundle
                            best_bundle_gain = bundle_gain
                            best_bundle_effort = bundle_effort
                        elif bundle_effort == best_bundle_effort:
                            # Tie-break 3: alphabetical order of candidate skill
                            if best_bundle is None or s_cand < best_bundle[-1]:
                                best_efficiency = efficiency
                                best_bundle = bundle
                                best_bundle_gain = bundle_gain
                                best_bundle_effort = bundle_effort

            if not best_bundle or best_bundle_gain <= 0:
                # No feasible skill or bundle remaining within budget that provides marginal coverage gain
                break

            # Execute selection: add each skill in best_bundle in topological order
            for skill_in_bundle in best_bundle:
                if skill_in_bundle in covered_skills:
                    continue

                info = skill_info[skill_in_bundle]
                effort = info["estimated_hours"]
                remaining_budget -= effort
                covered_skills.add(skill_in_bundle)

                # Compute exact individual marginal gain for this skill
                skill_gain = 0.0
                jobs_helped = []
                for j in eligible_jobs:
                    if skill_in_bundle in j["missing"]:
                        req_count = len(j["requirements"])
                        gain_j = j["normalized_weight"] * (1.0 / req_count)
                        skill_gain += gain_j
                        jobs_helped.append(j)

                current_cumulative_coverage += skill_gain
                action_unrounded_gains.append(skill_gain)

                # Why recommended narrative
                if jobs_helped:
                    why_msg = f"Directly qualifies for {len(jobs_helped)} target opportunities, providing +{round(skill_gain * 100, 1)} percentage points (+{round(skill_gain * 100, 1)} pp) of weighted requirement coverage."
                else:
                    why_msg = f"Essential foundational prerequisite enabling advanced target competencies in your learning roadmap."

                selected_actions.append({
                    "skill_name": skill_in_bundle,
                    "category": info["category"],
                    "priority_rank": rank,
                    "estimated_hours": effort,
                    "effort_uncertainty_range": info["uncertainty_range"],
                    "effort_model": info.get("effort_model", {}),
                    "marginal_coverage_gain": round(skill_gain, 4),
                    "cumulative_coverage": round(current_cumulative_coverage, 4),
                    "opportunities_count": len(jobs_helped),
                    "target_opportunity_ids": [j["id"] for j in jobs_helped if j["id"]],
                    "target_opportunities_summary": [
                        {
                            "id": j["id"],
                            "title": j["title"],
                            "company_name": j["company_name"],
                            "match_score": j["match_score"],
                            "primary_url": j["primary_url"]
                        }
                        for j in jobs_helped
                    ],
                    "prerequisites": info.get("prerequisites", []),
                    "all_prerequisites": info.get("all_prerequisites", []),
                    "why_recommended": why_msg,
                    "practical_project": {},
                    "learning_resources": VERIFIED_RESOURCES.get(skill_in_bundle.lower(), []),
                    "progress_state": "RECOMMENDED"
                })
                rank += 1

        # 5. Exact Mathematical Reconciliation of Coverage and Gains
        # Use authoritative shared evaluation for complete precision and consistency
        selected_skill_names = [a["skill_name"] for a in selected_actions]
        metrics = CosgoOptimizer.evaluate_coverage_metrics(eligible_jobs, selected_skill_names, verified_canonical)

        baseline_coverage_val = metrics["baseline_coverage"]
        final_projected_coverage = metrics["final_coverage"]
        marginal_increase_val = metrics["marginal_coverage_increase"]

        if selected_actions:
            # Reconcile individual rounded action gains so their sum equals marginal_increase_val exactly
            sum_rounded_gains = sum(a["marginal_coverage_gain"] for a in selected_actions)
            gain_residual = round(marginal_increase_val - sum_rounded_gains, 4)
            if abs(gain_residual) > 0:
                # Adjust residual onto the action with the largest marginal gain
                max_gain_idx = max(range(len(selected_actions)), key=lambda i: selected_actions[i]["marginal_coverage_gain"])
                selected_actions[max_gain_idx]["marginal_coverage_gain"] = round(
                    selected_actions[max_gain_idx]["marginal_coverage_gain"] + gain_residual, 4
                )

            # Recompute cumulative coverage sequence to guarantee strict monotonic additive identity
            running_cum = baseline_coverage_val
            for act in selected_actions:
                running_cum = round(running_cum + act["marginal_coverage_gain"], 4)
                act["cumulative_coverage"] = running_cum

        # 6. Project Qualification Threshold Recalculation
        projected_qualifying_count = 0
        for j in eligible_jobs:
            req_count = len(j["requirements"])
            job_covered = j["requirements"].intersection(covered_skills)
            proj_cov = len(job_covered) / req_count if req_count > 0 else 0.0
            j["projected_coverage"] = round(proj_cov, 4)
            if proj_cov >= 0.75:
                projected_qualifying_count += 1

        # 6. Synthesize Multi-Skill Practical Projects across selected actions
        selected_skill_names = [a["skill_name"] for a in selected_actions]
        projects = CosgoOptimizer.synthesize_portfolio_projects(selected_skill_names)

        # Attach appropriate project to each action
        for act in selected_actions:
            s_name = act["skill_name"]
            matched_project = next(
                (p for p in projects if s_name in p["overlapping_skills"]),
                None
            )
            if not matched_project:
                matched_project = CosgoOptimizer.generate_individual_project(s_name, act["category"])
            act["practical_project"] = matched_project

        # 7. Construct Coverage Matrix Data for Visualization
        matrix_items = []
        for j in eligible_jobs:
            req_list = sorted(list(j["requirements"]))
            v_skills = sorted(list(j["demonstrated"]))
            inf_skills = sorted(list(j["partial"]))
            covered_actions_for_job = sorted([
                r for r in j["missing"] if r in covered_skills
            ])
            rem_gaps = sorted([
                r for r in j["missing"] if r not in covered_skills
            ])

            matrix_items.append({
                "opportunity_id": j["id"] or "",
                "job_title": j["title"],
                "company_name": j["company_name"],
                "match_score": round(j["match_score"], 2),
                "role_relevance": round(j["role_relevance"], 2),
                "requirements": req_list,
                "verified_skills": v_skills,
                "inferred_skills": inf_skills,
                "actions_covering": covered_actions_for_job,
                "remaining_gaps": rem_gaps,
                "baseline_coverage": j["baseline_coverage"],
                "projected_coverage": j["projected_coverage"]
            })

        # Calculate skill frequency across all eligible jobs
        freq_map: Dict[str, int] = {}
        for j in eligible_jobs:
            for r in j["requirements"]:
                freq_map[r] = freq_map.get(r, 0) + 1

        sorted_top_skills = sorted(freq_map.keys(), key=lambda k: freq_map[k], reverse=True)[:15]

        return {
            "status": "COMPLETED",
            "total_opportunities_analyzed": len(opportunities),
            "eligible_opportunities_count": len(eligible_jobs),
            "excluded_opportunities_count": len(excluded_jobs),
            "diagnostics": {
                "excluded_breakdown": {
                    "duplicate_listings": sum(1 for e in excluded_jobs if e["reason"] == "DUPLICATE_LISTING"),
                    "insufficient_requirements": sum(1 for e in excluded_jobs if e["reason"] == "INSUFFICIENT_REQUIREMENTS"),
                },
                "total_candidate_verified_skills": len(verified_canonical),
                "total_candidate_inferred_skills": len(inferred_canonical),
                "total_distinct_job_skills_found": len(all_missing_skills),
                "budget_hours_requested": budget_hours,
                "budget_hours_used": round(budget_hours - remaining_budget, 1),
                "budget_hours_remaining": round(remaining_budget, 1),
                "weekly_budget_hours": weekly_budget_hours,
                "study_pace_weeks": round(budget_hours / weekly_budget_hours, 1) if weekly_budget_hours > 0 else 1.0,
                "estimated_weeks_to_complete": round((budget_hours - remaining_budget) / weekly_budget_hours, 1) if weekly_budget_hours > 0 else 1.0,
                "inferred_discount_factor": inferred_discount,
                "prerequisite_enforcement": "STRICT_HIERARCHICAL_BUNDLING",
                "algorithm_version": COSGO_ALGORITHM_VERSION,
                "mathematical_model": "Precedence-Constrained Knapsack with Modular Coverage Benefit",
                "effort_nature": "CURRICULUM_MODELED_PROJECTION",
                "coverage_definition": "Weighted sum of proportion of required canonical skills satisfied by verified profile and successfully completed actions",
                "is_employment_guarantee": False,
                "modeled_projection_note": "Coverage figures are conditional modeled projections assuming full demonstration and mastery of recommended actions. They do not constitute an offer, employment guarantee, or interview commitment."
            },
            "baseline_coverage": baseline_coverage_val,
            "projected_coverage": final_projected_coverage,
            "marginal_coverage_increase": marginal_increase_val,
            "opportunities_at_threshold_baseline": baseline_qualifying_count,
            "opportunities_at_threshold_projected": projected_qualifying_count,
            "actions": selected_actions,
            "opportunity_weights_used": weights_used_map,
            "coverage_matrix": {
                "total_skills_count": len(sorted_top_skills),
                "skills_header": sorted_top_skills,
                "matrix": matrix_items,
                "skill_frequency": freq_map
            }
        }

    @staticmethod
    def synthesize_portfolio_projects(selected_skills: List[str]) -> List[Dict[str, Any]]:
        """
        Synthesizes practical portfolio projects that integrate 2-3 overlapping skills together,
        ensuring the projects are concrete and demonstrate demonstrable software outcomes.
        """
        projects = []
        skills_set = {s.lower() for s in selected_skills}

        # Template 1: ML Deployment Pipeline
        if any(s in skills_set for s in ["pytorch", "tensorflow", "scikit-learn"]) and ("docker" in skills_set or "fastapi" in skills_set):
            overlapping = [s for s in selected_skills if s.lower() in ["pytorch", "tensorflow", "fastapi", "docker", "python"]]
            projects.append({
                "title": "Containerized Real-Time Model Inference & Serving API",
                "description": "Develop and deploy an asynchronous inference microservice packaging your trained machine learning model with automated health probes, batch prediction, and containerization.",
                "overlapping_skills": overlapping,
                "deliverables": [
                    "Modular model prediction pipeline with data preprocessing",
                    "FastAPI asynchronous REST API with Swagger documentation",
                    "Multi-stage Dockerfile optimized for lean production image size",
                    "Automated integration tests verifying payload parsing and latency"
                ],
                "difficulty_level": "Intermediate / Advanced"
            })

        # Template 2: Microservices & Data Platform
        if any(s in skills_set for s in ["fastapi", "django", "node.js", "python"]) and any(s in skills_set for s in ["postgresql", "redis", "sql"]):
            overlapping = [s for s in selected_skills if s.lower() in ["fastapi", "django", "node.js", "postgresql", "redis", "sql", "docker"]]
            projects.append({
                "title": "Scalable Relational Microservice with Redis Query Caching",
                "description": "Construct a robust backend service using SQL migrations, connection pooling, and sub-millisecond Redis caching for high-concurrency read operations.",
                "overlapping_skills": overlapping,
                "deliverables": [
                    "Relational schema with Alembic / Liquibase migrations and indexes",
                    "Write-through or cache-aside Redis caching layer",
                    "Pytest suite with in-memory database integration tests",
                    "Docker Compose orchestration for DB, Redis, and API service"
                ],
                "difficulty_level": "Intermediate"
            })

        # Template 3: Modern Frontend & Reactive Architecture
        if any(s in skills_set for s in ["angular", "react", "vue"]) and any(s in skills_set for s in ["typescript", "javascript"]):
            overlapping = [s for s in selected_skills if s.lower() in ["angular", "react", "vue", "typescript", "javascript", "docker"]]
            projects.append({
                "title": "Reactive Single-Page Application with State Management",
                "description": "Build a responsive candidate-facing dashboard with modular components, typed observables, route guards, and accessible design systems.",
                "overlapping_skills": overlapping,
                "deliverables": [
                    "Component architecture with strict TypeScript interfaces",
                    "Reactive state management using RxJS observables or state store",
                    "Clean responsive styling with semantic HTML5 and CSS grid",
                    "Unit test suite achieving >80% code coverage on core components"
                ],
                "difficulty_level": "Intermediate"
            })

        # Template 4: Cloud & DevOps Automation
        if any(s in skills_set for s in ["kubernetes", "aws", "ci/cd", "docker"]):
            overlapping = [s for s in selected_skills if s.lower() in ["kubernetes", "aws", "docker", "ci/cd", "linux"]]
            projects.append({
                "title": "Automated Cloud CI/CD Deployment with Kubernetes Manifests",
                "description": "Create an automated GitHub Actions CI/CD deployment pipeline packaging containers and deploying to a managed Kubernetes cluster with rolling updates.",
                "overlapping_skills": overlapping,
                "deliverables": [
                    "GitHub Actions workflow for automated test, build, and container push",
                    "Declarative Kubernetes Deployment, Service, and Ingress manifests",
                    "ConfigMap and Secret management for isolated environments",
                    "Zero-downtime rolling update configuration with health checks"
                ],
                "difficulty_level": "Advanced"
            })

        return projects

    @staticmethod
    def generate_individual_project(skill_name: str, category: str) -> Dict[str, Any]:
        """Fallback practical project tailored specifically to an individual skill."""
        return {
            "title": f"Practical Demonstration Project: {skill_name}",
            "description": f"Design and implement a standalone, verifiable module applying {skill_name} following production best practices and automated testing.",
            "overlapping_skills": [skill_name],
            "deliverables": [
                f"Working implementation demonstrating core {skill_name} capabilities",
                "Comprehensive README explaining architectural choices and setup",
                "Automated test suite verifying critical functionality and edge cases"
            ],
            "difficulty_level": "Intermediate"
        }
