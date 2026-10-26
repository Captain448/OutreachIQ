import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.user import User
from app.models.profile import Profile, Skill, SkillStatus
from app.models.opportunity import Opportunity, OpportunityStatus, OpportunityType
from app.models.job import Job, JobRequirement
from app.models.cosgo import CosgoRun, CosgoAction, CosgoProgressState
from app.services.cosgo_optimizer import CosgoOptimizer, COSGO_ALGORITHM_VERSION
from app.services.cosgo_evaluator import CosgoEvaluator
from app.services.matching_service import MatchingService
from app.services.opportunity_normalizer import OpportunityNormalizer

logger = logging.getLogger(__name__)


class CosgoService:
    @staticmethod
    def get_candidate_skills(user_id: str, db: Session) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        Retrieves verified, inferred, and unverified skill sets from candidate's profile.
        Strictly preserves factual status without fabricating claims.
        """
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        if not profile:
            return set(), set(), set()

        skills = db.query(Skill).filter(Skill.profile_id == profile.id).all()
        verified = {s.name for s in skills if s.status == SkillStatus.VERIFIED}
        inferred = {s.name for s in skills if s.status == SkillStatus.INFERRED}
        unverified = {s.name for s in skills if s.status == SkillStatus.UNVERIFIED}

        return verified, inferred, unverified

    @staticmethod
    def extract_user_opportunity_dataset(
        user_id: str,
        db: Session,
        target_roles: Optional[List[str]] = None,
        min_relevance: float = 0.35
    ) -> List[Dict[str, Any]]:
        """
        Gathers trustworthy opportunity dataset for the authenticated user:
        - Excludes DISMISSED opportunities.
        - Excludes invalid, rejected, or expired listings.
        - Extracts structured requirements from JobRequirement and description text.
        - Applies semantic role relevance scoring against candidate target roles.
        """
        # Get candidate preferences
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        if not target_roles:
            if profile and profile.preferences and profile.preferences.desired_roles:
                target_roles = profile.preferences.desired_roles
            else:
                target_roles = ["Software Engineer"]

        # Retrieve user's persisted opportunities
        opps = db.query(Opportunity).filter(
            Opportunity.user_id == user_id,
            Opportunity.status != OpportunityStatus.DISMISSED
        ).all()

        dataset: List[Dict[str, Any]] = []

        for opp in opps:
            job = opp.job
            title = job.title if job else "Software Engineer"
            company_name = (job.company_name if job else (opp.company.name if opp.company else "Direct Employer"))
            primary_url = job.primary_url if job else ""

            # Verification status check: exclude expired or invalid vacancies
            if job and job.verification_status in ["LISTING_FOUND_STATUS_EXPIRED_OR_CLOSED", "EXPIRED_OR_CLOSED", "INVALID_OR_REJECTED"]:
                continue

            # Calculate semantic role relevance
            role_rel, _ = MatchingService.calculate_role_relevance(title, target_roles)
            if role_rel < min_relevance:
                continue

            # Extract requirements
            requirements: Set[str] = set()

            # 1. Check JobRequirement table
            if job and job.requirements:
                for r in job.requirements:
                    if r.description and len(r.description.strip()) > 1:
                        requirements.add(r.description.strip())

            # 2. Check matched + missing skills on Opportunity
            if opp.matched_skills:
                for s in opp.matched_skills:
                    clean_s = s.replace(" (Inferred)", "").strip()
                    if clean_s:
                        requirements.add(clean_s)

            if opp.missing_skills:
                for s in opp.missing_skills:
                    if s and len(s.strip()) > 1:
                        requirements.add(s.strip())

            # 3. Fallback extraction from job description text
            if not requirements and job and job.description:
                skills_from_desc = OpportunityNormalizer.extract_skills_from_text(job.description)
                requirements.update(skills_from_desc)

            verification_conf = opp.evidence_confidence or (0.95 if job and job.is_verified else 0.80)

            dataset.append({
                "id": opp.id,
                "title": title,
                "company_name": company_name,
                "primary_url": primary_url,
                "requirements": requirements,
                "role_relevance": role_rel,
                "verification_confidence": verification_conf,
                "match_score": opp.match_score or 0.50
            })

        return dataset

    @staticmethod
    def run_optimization(
        user_id: str,
        db: Session,
        budget_hours: float = 40.0,
        weekly_budget_hours: float = 10.0,
        target_roles: Optional[List[str]] = None,
        min_relevance: float = 0.35
    ) -> CosgoRun:
        """
        Executes complete COSGO analysis and persists run and actions to the database.
        """
        verified, inferred, unverified = CosgoService.get_candidate_skills(user_id, db)
        dataset = CosgoService.extract_user_opportunity_dataset(user_id, db, target_roles, min_relevance)

        # Run optimizer
        result = CosgoOptimizer.optimize(
            opportunities=dataset,
            verified_skills=verified,
            inferred_skills=inferred,
            budget_hours=budget_hours,
            weekly_budget_hours=weekly_budget_hours
        )

        now = datetime.now(timezone.utc)

        # Build snapshot for strict historical reproducibility
        diagnostics = dict(result.get("diagnostics", {}))
        diagnostics["historical_snapshot"] = {
            "verified_skills": sorted(list(verified)),
            "inferred_skills": sorted(list(inferred)),
            "unverified_skills": sorted(list(unverified)),
            "target_roles": target_roles or [],
            "coverage_matrix": result.get("coverage_matrix", {})
        }

        # Create persistent CosgoRun
        run = CosgoRun(
            user_id=user_id,
            budget_hours=budget_hours,
            weekly_budget_hours=weekly_budget_hours,
            target_roles=target_roles or [],
            algorithm_version=COSGO_ALGORITHM_VERSION,
            status=result["status"],
            total_opportunities_analyzed=result["total_opportunities_analyzed"],
            eligible_opportunities_count=result["eligible_opportunities_count"],
            excluded_opportunities_count=result["excluded_opportunities_count"],
            baseline_coverage=result["baseline_coverage"],
            projected_coverage=result["projected_coverage"],
            marginal_coverage_increase=result["marginal_coverage_increase"],
            opportunities_at_threshold_baseline=result.get("opportunities_at_threshold_baseline", 0),
            opportunities_at_threshold_projected=result.get("opportunities_at_threshold_projected", 0),
            diagnostics=diagnostics,
            opportunity_weights_used=result.get("opportunity_weights_used", {}),
            created_at=now,
            updated_at=now
        )
        db.add(run)
        db.flush()

        # Add actions
        for act in result.get("actions", []):
            action_row = CosgoAction(
                run_id=run.id,
                user_id=user_id,
                skill_name=act["skill_name"],
                category=act["category"],
                priority_rank=act["priority_rank"],
                estimated_hours=act["estimated_hours"],
                effort_uncertainty_range=act["effort_uncertainty_range"],
                marginal_coverage_gain=act["marginal_coverage_gain"],
                cumulative_coverage=act["cumulative_coverage"],
                opportunities_count=act["opportunities_count"],
                target_opportunity_ids=act["target_opportunity_ids"],
                target_opportunities_summary=act["target_opportunities_summary"],
                prerequisites=act["prerequisites"],
                why_recommended=act["why_recommended"],
                practical_project=act["practical_project"],
                learning_resources=act["learning_resources"],
                progress_state=CosgoProgressState.RECOMMENDED,
                created_at=now,
                updated_at=now
            )
            db.add(action_row)

        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def get_latest_run(user_id: str, db: Session) -> Optional[CosgoRun]:
        """Fetches latest persisted COSGO run for the user."""
        return db.query(CosgoRun).filter(CosgoRun.user_id == user_id).order_by(desc(CosgoRun.created_at)).first()

    @staticmethod
    def get_or_create_latest_run(
        user_id: str,
        db: Session,
        budget_hours: float = 40.0,
        weekly_budget_hours: float = 10.0
    ) -> CosgoRun:
        """Retrieves existing run or generates one on initial request."""
        run = CosgoService.get_latest_run(user_id, db)
        if not run:
            run = CosgoService.run_optimization(user_id, db, budget_hours, weekly_budget_hours)
        return run

    @staticmethod
    def update_action_progress(
        action_id: str,
        user_id: str,
        progress_state: str,
        user_notes: Optional[str],
        db: Session
    ) -> Optional[CosgoAction]:
        """
        Updates action progress state with user confirmation.
        Note: Does NOT automatically fabricate or alter verified profile skills.
        """
        action = db.query(CosgoAction).filter(
            CosgoAction.id == action_id,
            CosgoAction.user_id == user_id
        ).first()

        if not action:
            return None

        # Validate state
        valid_states = [s.value for s in CosgoProgressState]
        if progress_state not in valid_states:
            raise ValueError(f"Invalid progress state '{progress_state}'. Must be one of: {valid_states}")

        action.progress_state = CosgoProgressState(progress_state)
        if user_notes is not None:
            action.user_notes = user_notes

        now = datetime.now(timezone.utc)
        if progress_state == CosgoProgressState.COMPLETED.value:
            action.completed_at = now
        elif progress_state != CosgoProgressState.COMPLETED.value:
            action.completed_at = None

        action.updated_at = now
        db.commit()
        db.refresh(action)
        return action

    @staticmethod
    def get_coverage_matrix(run_id: str, user_id: str, db: Session) -> Dict[str, Any]:
        """
        Retrieves dynamic coverage matrix for a specific run.
        Guarantees strict historical reproducibility using immutable snapshot if available.
        """
        run = db.query(CosgoRun).filter(CosgoRun.id == run_id, CosgoRun.user_id == user_id).first()
        if not run:
            return {"error": "Run not found"}

        # Priority 1: Check persisted snapshot in run diagnostics
        if run.diagnostics and "historical_snapshot" in run.diagnostics:
            snapshot_matrix = run.diagnostics["historical_snapshot"].get("coverage_matrix")
            if snapshot_matrix and snapshot_matrix.get("matrix"):
                return {
                    "run_id": run.id,
                    "total_skills_count": snapshot_matrix.get("total_skills_count", 0),
                    "skills_header": snapshot_matrix.get("skills_header", []),
                    "matrix": snapshot_matrix.get("matrix", []),
                    "skill_frequency": snapshot_matrix.get("skill_frequency", {}),
                    "is_historical_reproducible_snapshot": True
                }

        # Priority 2: Fallback reconstruction for legacy runs
        verified, inferred, _ = CosgoService.get_candidate_skills(user_id, db)
        dataset = CosgoService.extract_user_opportunity_dataset(user_id, db, run.target_roles)

        opt_result = CosgoOptimizer.optimize(
            opportunities=dataset,
            verified_skills=verified,
            inferred_skills=inferred,
            budget_hours=run.budget_hours,
            weekly_budget_hours=run.weekly_budget_hours
        )

        matrix_data = opt_result.get("coverage_matrix", {})
        return {
            "run_id": run.id,
            "total_skills_count": matrix_data.get("total_skills_count", 0),
            "skills_header": matrix_data.get("skills_header", []),
            "matrix": matrix_data.get("matrix", []),
            "skill_frequency": matrix_data.get("skill_frequency", {})
        }
        return {
            "run_id": run.id,
            "total_skills_count": matrix_data.get("total_skills_count", 0),
            "skills_header": matrix_data.get("skills_header", []),
            "matrix": matrix_data.get("matrix", []),
            "skill_frequency": matrix_data.get("skill_frequency", {})
        }

    @staticmethod
    def evaluate_benchmarks(
        user_id: str,
        db: Session,
        budget_hours: float = 35.0,
        weekly_budget_hours: float = 10.0
    ) -> Dict[str, Any]:
        """Runs reproducibility benchmark suite on user's current opportunity set or canonical benchmark."""
        verified, inferred, _ = CosgoService.get_candidate_skills(user_id, db)
        dataset = CosgoService.extract_user_opportunity_dataset(user_id, db)

        if len(dataset) < 2:
            return CosgoEvaluator.run_canonical_benchmark(budget_hours=budget_hours)

        return CosgoEvaluator.evaluate_all(
            opportunities=dataset,
            verified_skills=verified,
            inferred_skills=inferred,
            budget_hours=budget_hours,
            weekly_budget_hours=weekly_budget_hours
        )


# Type alias helper
Tuple_Skills = Tuple[Set[str], Set[str], Set[str]]
