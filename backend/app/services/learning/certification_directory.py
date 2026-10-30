from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field


class CertificationEntry(BaseModel):
    id: str
    name: str
    issuing_organization: str
    official_url: str
    relevant_skills: List[str]
    target_roles: List[str]
    prerequisites: Optional[str] = None
    exam_cost_status: str  # PAID, FREE, NOT_VERIFIED
    exam_fee_estimate: Optional[str] = None
    learning_material_free_status: str  # FREE, PARTIAL, PAID
    last_verified_date: str = "2026-10-28"
    description: str


OFFICIAL_CERTIFICATIONS: List[CertificationEntry] = [
    CertificationEntry(
        id="aws-solutions-architect-assoc",
        name="AWS Certified Solutions Architect – Associate",
        issuing_organization="Amazon Web Services (AWS)",
        official_url="https://aws.amazon.com/certification/certified-solutions-architect-associate/",
        relevant_skills=["AWS", "Cloud Computing", "Docker", "DevOps", "PostgreSQL"],
        target_roles=["Cloud Architect", "Backend Engineer", "DevOps Engineer", "Solutions Architect"],
        prerequisites="Foundational cloud knowledge; 1 year hands-on designing AWS systems recommended.",
        exam_cost_status="PAID",
        exam_fee_estimate="$150 USD (Verified vendor exam fee)",
        learning_material_free_status="FREE",
        description="Validates technical expertise in designing and deploying scalable, highly available, and fault-tolerant systems on AWS. Official AWS documentation and digital training are free; proctored exam is paid."
    ),
    CertificationEntry(
        id="gcp-associate-cloud-engineer",
        name="Google Cloud Certified Associate Cloud Engineer",
        issuing_organization="Google Cloud",
        official_url="https://cloud.google.com/learn/certification/cloud-engineer",
        relevant_skills=["Google Cloud", "Kubernetes", "Docker", "Linux", "DevOps"],
        target_roles=["Cloud Engineer", "DevOps Engineer", "Site Reliability Engineer (SRE)", "Backend Developer"],
        prerequisites="6+ months hands-on experience with Google Cloud recommended.",
        exam_cost_status="PAID",
        exam_fee_estimate="$125 USD (Verified Google Cloud exam fee)",
        learning_material_free_status="FREE",
        description="Assesses ability to deploy applications, monitor operations, and manage enterprise solutions on Google Cloud infrastructure."
    ),
    CertificationEntry(
        id="azure-developer-az204",
        name="Microsoft Certified: Azure Developer Associate (AZ-204)",
        issuing_organization="Microsoft",
        official_url="https://learn.microsoft.com/en-us/credentials/certifications/azure-developer/",
        relevant_skills=["Azure", "TypeScript", "Python", "Docker", "SQL"],
        target_roles=["Azure Developer", "Cloud Developer", "Full Stack Developer"],
        prerequisites="1-2 years professional development experience with Microsoft Azure.",
        exam_cost_status="PAID",
        exam_fee_estimate="$165 USD (Verified Microsoft exam fee)",
        learning_material_free_status="FREE",
        description="Measures proficiency in designing, building, testing, and maintaining cloud applications and services on Microsoft Azure. All Microsoft Learn modules are 100% free."
    ),
    CertificationEntry(
        id="cka-kubernetes-administrator",
        name="Certified Kubernetes Administrator (CKA)",
        issuing_organization="Cloud Native Computing Foundation (CNCF) / Linux Foundation",
        official_url="https://www.cncf.io/certification/cka/",
        relevant_skills=["Kubernetes", "Docker", "Linux", "DevOps", "CI/CD"],
        target_roles=["DevOps Engineer", "Kubernetes Administrator", "Platform Engineer", "SRE"],
        prerequisites="Comfortable with Linux command line and container concepts.",
        exam_cost_status="PAID",
        exam_fee_estimate="$395 USD (Verified CNCF exam fee)",
        learning_material_free_status="PARTIAL",
        description="Hands-on performance-based exam testing the skills to configure, secure, and manage production Kubernetes clusters. Kubernetes documentation is open and free."
    ),
    CertificationEntry(
        id="terraform-associate",
        name="HashiCorp Certified: Terraform Associate (003)",
        issuing_organization="HashiCorp",
        official_url="https://developer.hashicorp.com/terraform/tutorials/certification-003",
        relevant_skills=["Terraform", "AWS", "Google Cloud", "DevOps", "CI/CD"],
        target_roles=["DevOps Engineer", "Infrastructure Engineer", "Cloud Architect"],
        prerequisites="Basic cloud architecture understanding and command line familiarity.",
        exam_cost_status="PAID",
        exam_fee_estimate="$70.50 USD (Verified HashiCorp exam fee)",
        learning_material_free_status="FREE",
        description="Validates foundational Infrastructure as Code concepts, Terraform Cloud, state management, and module development. HashiCorp Developer Tutorials are 100% free."
    ),
    CertificationEntry(
        id="pcap-python-associate",
        name="PCAP – Certified Associate in Python Programming",
        issuing_organization="Python Institute / OpenEDG",
        official_url="https://pythoninstitute.org/pcap",
        relevant_skills=["Python", "Object-Oriented Programming", "Data Structures"],
        target_roles=["Junior Python Developer", "Software Engineer", "Backend Developer"],
        prerequisites="Completion of Python Essentials 1 and 2 (free via Cisco Networking Academy / OpenEDG).",
        exam_cost_status="PAID",
        exam_fee_estimate="$295 USD (Verified OpenEDG exam fee)",
        learning_material_free_status="FREE",
        description="Demonstrates proficiency in Python syntax, semantics, and object-oriented programming conventions. Official Python Institute courseware is free online."
    ),
    CertificationEntry(
        id="github-actions-cert",
        name="GitHub Actions Certification",
        issuing_organization="GitHub",
        official_url="https://resources.github.com/learn/certifications/",
        relevant_skills=["CI/CD", "Git", "DevOps", "Docker"],
        target_roles=["DevOps Engineer", "Software Engineer", "Release Engineer"],
        prerequisites="Experience writing and maintaining GitHub Actions workflows.",
        exam_cost_status="PAID",
        exam_fee_estimate="$99 USD (Verified GitHub exam fee)",
        learning_material_free_status="FREE",
        description="Tests expertise in workflow automation, custom actions, self-hosted runners, and secure CI/CD pipelines on GitHub. Official GitHub Skills and Microsoft Learn paths are free."
    ),
    CertificationEntry(
        id="meta-backend-developer",
        name="Meta Back-End Developer Professional Certificate",
        issuing_organization="Meta / Coursera",
        official_url="https://www.coursera.org/professional-certificates/meta-back-end-developer",
        relevant_skills=["Python", "Django", "SQL", "Git", "FastAPI"],
        target_roles=["Backend Developer", "Junior Python Developer"],
        prerequisites="None required.",
        exam_cost_status="PAID",
        exam_fee_estimate="Coursera Subscription ($49/month after trial)",
        learning_material_free_status="PARTIAL",
        description="Comprehensive 9-course program created by Meta teaching Python, Django web framework, databases, and APIs. Can be audited for free without certificate; verified certificate requires payment."
    )
]


class CertificationDirectoryService:
    @classmethod
    def get_all_certifications(cls) -> List[CertificationEntry]:
        return OFFICIAL_CERTIFICATIONS

    @classmethod
    def get_certifications_for_skill(cls, skill_name: str, limit: int = 4) -> List[CertificationEntry]:
        """
        Returns official vendor certifications that strictly validate or test the specified skill.
        If no official certification tests this skill, returns an empty list (honest empty state).
        """
        norm = skill_name.lower().strip()
        matched: List[CertificationEntry] = []
        for cert in OFFICIAL_CERTIFICATIONS:
            is_relevant = any(
                norm == s.lower() or (len(norm) >= 3 and (norm in s.lower() or s.lower() in norm))
                for s in cert.relevant_skills
            )
            if is_relevant:
                matched.append(cert)
        return matched[:limit]

    @classmethod
    def find_certifications_for_skills_and_roles(
        cls,
        skills: List[str],
        roles: Optional[List[str]] = None,
        limit: int = 6
    ) -> List[CertificationEntry]:
        norm_skills = [s.lower().strip() for s in skills]
        norm_roles = [r.lower().strip() for r in (roles or [])]

        scored: List[Tuple[int, CertificationEntry]] = []
        for cert in OFFICIAL_CERTIFICATIONS:
            score = 0
            for s in cert.relevant_skills:
                if any(s.lower() in ns or ns in s.lower() for ns in norm_skills):
                    score += 2
            for r in cert.target_roles:
                if any(r.lower() in nr or nr in r.lower() for nr in norm_roles):
                    score += 3
            if score > 0:
                scored.append((score, cert))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]
