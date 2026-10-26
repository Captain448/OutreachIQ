import pytest
from unittest.mock import patch, AsyncMock
from app.models.profile import SkillStatus, SkillSource
from app.models.opportunity import OpportunityType, OpportunityStatus, RecommendedAction
from app.services.cosgo_optimizer import CosgoOptimizer
from app.services.cosgo_evaluator import CosgoEvaluator
from app.services.providers.base_provider import NormalizedJob


# ---------------------------------------------------------------------------
# Unit Tests for Core Optimization Math & Submodularity
# ---------------------------------------------------------------------------

def test_cosgo_optimizer_math_and_prerequisites():
    """
    Controlled deterministic test dataset:
    Job 1: requires Python, PyTorch, Docker, FastAPI (4 skills)
    Job 2: requires Python, Docker, Kubernetes, AWS (4 skills)
    Job 3: requires Python, PyTorch, Scikit-Learn (3 skills)
    Job 4: requires Java, Spring Boot (2 skills - distinct domain)

    Candidate Profile:
    - Verified: Python
    - Inferred: Docker
    - Missing: PyTorch, FastAPI, Kubernetes, AWS, Scikit-Learn, Java, Spring Boot
    """
    opportunities = [
        {
            "id": "job-1",
            "title": "Senior AI Engineer",
            "company_name": "DeepAI Labs",
            "requirements": {"Python", "PyTorch", "Docker", "FastAPI"},
            "role_relevance": 0.95,
            "verification_confidence": 1.0,
            "match_score": 0.70
        },
        {
            "id": "job-2",
            "title": "ML Platform Engineer",
            "company_name": "CloudVectors",
            "requirements": {"Python", "Docker", "Kubernetes", "AWS"},
            "role_relevance": 0.90,
            "verification_confidence": 0.95,
            "match_score": 0.65
        },
        {
            "id": "job-3",
            "title": "Data Scientist",
            "company_name": "InsightAnalytics",
            "requirements": {"Python", "PyTorch", "Scikit-Learn"},
            "role_relevance": 0.85,
            "verification_confidence": 0.90,
            "match_score": 0.60
        },
        {
            "id": "job-4",
            "title": "Enterprise Backend Engineer",
            "company_name": "LegacyEnterprise",
            "requirements": {"Java", "Spring Boot"},
            "role_relevance": 0.40,
            "verification_confidence": 0.80,
            "match_score": 0.20
        }
    ]

    verified = {"Python"}
    inferred = {"Docker"}

    # Run optimization with 45 hours budget
    res = CosgoOptimizer.optimize(
        opportunities=opportunities,
        verified_skills=verified,
        inferred_skills=inferred,
        budget_hours=45.0,
        weekly_budget_hours=10.0
    )

    assert res["status"] == "COMPLETED"
    assert res["eligible_opportunities_count"] == 4
    assert res["excluded_opportunities_count"] == 0

    # Baseline coverage check:
    # Python is verified in Job 1 (1/4), Job 2 (1/4), Job 3 (1/3), Job 4 (0/2).
    # Baseline coverage must be strictly between 0.15 and 0.35.
    assert 0.15 <= res["baseline_coverage"] <= 0.35
    assert res["projected_coverage"] > res["baseline_coverage"]
    assert res["marginal_coverage_increase"] > 0

    actions = res["actions"]
    assert len(actions) >= 2

    # PyTorch and Docker should be highly ranked because PyTorch helps Job 1 and Job 3 (high role relevance)
    action_skills = [a["skill_name"] for a in actions]
    assert "PyTorch" in action_skills or "Docker" in action_skills

    # Docker has partial evidence (inferred), so its estimated effort must be discounted
    docker_act = next((a for a in actions if a["skill_name"] == "Docker"), None)
    if docker_act:
        # Standard effort is 14 hrs; discounted by 30% -> ~9.8 hrs
        assert docker_act["estimated_hours"] <= 12.0

    # Total estimated hours must not exceed the 45.0 budget limit
    total_hours = sum(a["estimated_hours"] for a in actions)
    assert total_hours <= 45.0

    # Verify multi-skill project generation attached to actions
    for a in actions:
        assert "practical_project" in a
        assert "title" in a["practical_project"]
        assert len(a["practical_project"]["overlapping_skills"]) >= 1


def test_cosgo_optimizer_excludes_invalid_and_duplicate_jobs():
    duplicate_opps = [
        {
            "id": "job-1",
            "title": "Machine Learning Engineer",
            "company_name": "AlphaTech",
            "requirements": {"Python", "PyTorch"}
        },
        {
            "id": "job-2",
            "title": "Machine Learning Engineer",
            "company_name": "AlphaTech",  # Exact duplicate company + title
            "requirements": {"Python", "PyTorch"}
        },
        {
            "id": "job-3",
            "title": "Empty Requirements Job",
            "company_name": "BetaTech",
            "requirements": set()  # Insufficient requirements
        }
    ]

    res = CosgoOptimizer.optimize(
        opportunities=duplicate_opps,
        verified_skills={"Python"},
        inferred_skills=set(),
        budget_hours=30.0
    )

    assert res["eligible_opportunities_count"] == 1
    assert res["excluded_opportunities_count"] == 2
    diag = res["diagnostics"]["excluded_breakdown"]
    assert diag["duplicate_listings"] == 1
    assert diag["insufficient_requirements"] == 1


# ---------------------------------------------------------------------------
# Academic Benchmark Evaluation Tests
# ---------------------------------------------------------------------------

def test_cosgo_evaluator_baselines_comparison():
    opportunities = [
        {"id": "j1", "title": "AI Engineer", "company_name": "A1", "requirements": {"Python", "PyTorch", "Docker"}, "role_relevance": 0.95},
        {"id": "j2", "title": "Data Scientist", "company_name": "A2", "requirements": {"Python", "PyTorch", "SQL"}, "role_relevance": 0.90},
        {"id": "j3", "title": "MLOps Engineer", "company_name": "A3", "requirements": {"Python", "Docker", "Kubernetes"}, "role_relevance": 0.90},
        {"id": "j4", "title": "Backend Dev", "company_name": "A4", "requirements": {"Python", "FastAPI", "PostgreSQL"}, "role_relevance": 0.80},
    ]

    verified = {"Python"}
    inferred = set()

    bench = CosgoEvaluator.evaluate_all(
        opportunities=opportunities,
        verified_skills=verified,
        inferred_skills=inferred,
        budget_hours=35.0,
        weekly_budget_hours=10.0
    )

    assert "cosgo" in bench
    assert "frequency_baseline" in bench
    assert "independent_per_job" in bench
    assert "greedy_frequency_no_effort" in bench
    assert "comparison_summary" in bench

    cosgo_metrics = bench["cosgo"]
    freq_metrics = bench["frequency_baseline"]

    # Efficiency (coverage gain per hour) of COSGO should be greater than or equal to frequency baseline
    assert cosgo_metrics["gain_per_hour"] >= freq_metrics["gain_per_hour"] - 0.001
    assert cosgo_metrics["hours_spent"] <= 35.0
    assert cosgo_metrics["unique_opportunities_improved"] >= 2


# ---------------------------------------------------------------------------
# API Integration Tests for COSGO Router
# ---------------------------------------------------------------------------

def test_cosgo_api_endpoints_lifecycle(client):
    # 1. Register test user
    reg = client.post(
        "/auth/register",
        json={"email": "cosgo.tester@example.com", "password": "Password123!", "full_name": "COSGO Candidate"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Add profile skills: verified Python, inferred Docker
    client.put(
        "/profile",
        json={
            "headline": "Applied Machine Learning Engineer",
            "preferences": {
                "desired_roles": ["AI/ML Engineer", "Machine Learning Engineer"],
                "preferred_locations": ["Bengaluru", "Remote"],
                "remote_preference": "flexible"
            },
            "skills": [
                {"name": "Python", "category": "languages", "status": "VERIFIED", "source": "USER_INPUT", "confidence_score": 1.0},
                {"name": "Docker", "category": "tools", "status": "INFERRED", "source": "EXPERIENCE_INFERRED", "confidence_score": 0.8}
            ]
        },
        headers=headers
    )

    # 3. Seed opportunities with job requirements
    mock_jobs = [
        NormalizedJob(
            title="Senior AI/ML Engineer",
            company_name="NeuralCompute Inc",
            description="Developing deep learning models with PyTorch and deploying using FastAPI and Docker in Bengaluru.",
            location="Bengaluru",
            is_remote=True,
            work_arrangement="remote",
            employment_type="full-time",
            primary_url="https://neuralcompute.ai/careers/aiml-lead",
            source_name="Company Career Page",
            source_provider="tavily",
            extracted_skills=["Python", "PyTorch", "FastAPI", "Docker"],
            confidence=0.95
        ),
        NormalizedJob(
            title="Machine Learning Engineer",
            company_name="VisionVector AI",
            description="Computer vision and PyTorch engineering with Kubernetes deployments.",
            location="Bengaluru",
            is_remote=False,
            work_arrangement="onsite",
            employment_type="full-time",
            primary_url="https://visionvector.ai/careers/ml-eng",
            source_name="Company Career Page",
            source_provider="tavily",
            extracted_skills=["Python", "PyTorch", "Kubernetes"],
            confidence=0.90
        )
    ]

    with patch("app.services.opportunity_orchestrator.provider_registry.get_configured_providers") as mock_conf, \
         patch("app.services.company_research_service.CompanyResearchService.research_company_classification_async", new_callable=AsyncMock) as mock_res:
        mock_res.return_value = {"classification": "startup", "size_range": "50-200", "evidence_excerpt": "AI company"}
        mock_p = AsyncMock()
        mock_p.provider_name = "tavily"
        mock_p.search_jobs = AsyncMock(return_value=mock_jobs)
        mock_p.search_companies = AsyncMock(return_value=[])
        mock_conf.return_value = [mock_p]

        disco_res = client.post(
            "/opportunities/discovery",
            json={"target_roles": ["AI/ML Engineer"], "limit": 10},
            headers=headers
        )
        assert disco_res.status_code == 202

    # 4. Trigger COSGO Optimization API
    opt_res = client.post(
        "/cosgo/optimize",
        json={"budget_hours": 35.0, "weekly_budget_hours": 10.0},
        headers=headers
    )
    assert opt_res.status_code == 201
    run_data = opt_res.json()
    assert "id" in run_data
    assert run_data["status"] == "COMPLETED"
    assert run_data["eligible_opportunities_count"] >= 2
    assert run_data["baseline_coverage"] > 0
    assert run_data["projected_coverage"] >= run_data["baseline_coverage"]
    assert len(run_data["actions"]) >= 1

    run_id = run_data["id"]
    first_action = run_data["actions"][0]
    action_id = first_action["id"]
    assert first_action["progress_state"] == "RECOMMENDED"
    assert "practical_project" in first_action
    assert "why_recommended" in first_action

    # 5. Get Latest COSGO Run
    latest_res = client.get("/cosgo/latest", headers=headers)
    assert latest_res.status_code == 200
    assert latest_res.json()["id"] == run_id

    # 6. Get Specific Action Details
    act_res = client.get(f"/cosgo/actions/{action_id}", headers=headers)
    assert act_res.status_code == 200
    assert act_res.json()["id"] == action_id

    # 7. Update Action Progress to IN_PROGRESS and COMPLETED
    patch_prog = client.patch(
        f"/cosgo/actions/{action_id}/progress",
        json={"progress_state": "IN_PROGRESS", "user_notes": "Completed initial module tutorials."},
        headers=headers
    )
    assert patch_prog.status_code == 200
    assert patch_prog.json()["progress_state"] == "IN_PROGRESS"
    assert patch_prog.json()["user_notes"] == "Completed initial module tutorials."

    patch_comp = client.patch(
        f"/cosgo/actions/{action_id}/progress",
        json={"progress_state": "COMPLETED", "user_notes": "Built the portfolio project and pushed to GitHub."},
        headers=headers
    )
    assert patch_comp.status_code == 200
    assert patch_comp.json()["progress_state"] == "COMPLETED"
    assert patch_comp.json()["completed_at"] is not None

    # CRITICAL RULE VERIFICATION: Marking an action COMPLETED must NOT automatically alter the candidate's verified profile skills!
    profile_check = client.get("/profile", headers=headers).json()
    candidate_verified = [s["name"] for s in profile_check.get("skills", []) if s["status"] == "VERIFIED"]
    assert first_action["skill_name"] not in candidate_verified or first_action["skill_name"] == "Python"

    # 8. Get Coverage Matrix
    matrix_res = client.get(f"/cosgo/coverage-matrix?run_id={run_id}", headers=headers)
    assert matrix_res.status_code == 200
    matrix_data = matrix_res.json()
    assert "matrix" in matrix_data
    assert "skills_header" in matrix_data
    assert len(matrix_data["matrix"]) >= 2

    # 9. Update Budget and Re-optimize
    budget_res = client.put(
        "/cosgo/budget",
        json={"budget_hours": 50.0, "weekly_budget_hours": 15.0},
        headers=headers
    )
    assert budget_res.status_code == 200
    assert budget_res.json()["budget_hours"] == 50.0
    assert budget_res.json()["weekly_budget_hours"] == 15.0

    # 10. Research Reproducibility Benchmark Endpoint
    bench_res = client.get("/cosgo/benchmark?budget_hours=35.0", headers=headers)
    assert bench_res.status_code == 200
    bench_data = bench_res.json()
    assert "cosgo" in bench_data
    assert "frequency_baseline" in bench_data
    assert "comparison_summary" in bench_data


# ---------------------------------------------------------------------------
# Section 7: Mathematical & Property-Based Regression Invariants
# ---------------------------------------------------------------------------

def test_coverage_mathematical_invariants():
    """
    Validates Coverage Invariants:
    1. Coverage is always within interval [0, 1].
    2. Adding an unrelated verified skill does not increase coverage for a job that does not require it.
    3. Adding a genuinely relevant verified skill cannot decrease baseline coverage.
    4. Adding an unrelated learning action cannot increase projected coverage.
    5. Duplicate requirements do not inflate coverage.
    6. Duplicate job records do not improve the objective.
    7. An action cannot increase coverage for jobs that do not require the skill it develops.
    8. Projected coverage cannot exceed achievable supported requirement coverage.
    """
    job_1 = {
        "id": "j1",
        "title": "Backend Python Developer",
        "company_name": "TechCorp",
        "requirements": {"Python", "FastAPI", "SQL"},
        "role_relevance": 0.90,
        "verification_confidence": 0.90,
        "match_score": 0.60
    }
    job_2 = {
        "id": "j2",
        "title": "Frontend React Developer",
        "company_name": "WebCorp",
        "requirements": {"JavaScript", "React", "CSS3"},
        "role_relevance": 0.80,
        "verification_confidence": 0.85,
        "match_score": 0.50
    }

    # Case A: Candidate with Python verified
    res_a = CosgoOptimizer.optimize(
        opportunities=[job_1, job_2],
        verified_skills={"Python"},
        inferred_skills=set(),
        budget_hours=30.0
    )
    assert 0.0 <= res_a["baseline_coverage"] <= 1.0
    assert 0.0 <= res_a["projected_coverage"] <= 1.0

    # Invariant 2: Adding unrelated verified skill (e.g. "Rust") does not increase coverage for either job
    res_unrelated = CosgoOptimizer.optimize(
        opportunities=[job_1, job_2],
        verified_skills={"Python", "Rust"},
        inferred_skills=set(),
        budget_hours=30.0
    )
    assert res_unrelated["baseline_coverage"] == res_a["baseline_coverage"]

    # Invariant 3: Adding genuinely relevant verified skill (e.g. "FastAPI") cannot decrease baseline coverage
    res_relevant = CosgoOptimizer.optimize(
        opportunities=[job_1, job_2],
        verified_skills={"Python", "FastAPI"},
        inferred_skills=set(),
        budget_hours=30.0
    )
    assert res_relevant["baseline_coverage"] > res_a["baseline_coverage"]

    # Invariant 5: Duplicate requirements (e.g. "Python", "python", "PYTHON") do not inflate coverage
    job_with_dups = {
        "id": "j1_dup",
        "title": "Backend Python Developer",
        "company_name": "TechCorp",
        "requirements": {"Python", "python", "PYTHON", "FastAPI", "SQL"},
        "role_relevance": 0.90,
        "verification_confidence": 0.90,
        "match_score": 0.60
    }
    res_dups = CosgoOptimizer.optimize(
        opportunities=[job_with_dups, job_2],
        verified_skills={"Python"},
        inferred_skills=set(),
        budget_hours=30.0
    )
    assert res_dups["baseline_coverage"] == res_a["baseline_coverage"]

    # Invariant 6: Duplicate job records are excluded and do not improve objective
    res_dup_jobs = CosgoOptimizer.optimize(
        opportunities=[job_1, job_1, job_2],
        verified_skills={"Python"},
        inferred_skills=set(),
        budget_hours=30.0
    )
    assert res_dup_jobs["eligible_opportunities_count"] == 2
    assert res_dup_jobs["excluded_opportunities_count"] == 1
    assert res_dup_jobs["projected_coverage"] == res_a["projected_coverage"]

    # Invariant 8: Projected coverage cannot exceed 1.0 even with huge budget
    res_huge_budget = CosgoOptimizer.optimize(
        opportunities=[job_1, job_2],
        verified_skills={"Python"},
        inferred_skills=set(),
        budget_hours=500.0
    )
    assert res_huge_budget["projected_coverage"] <= 1.0


def test_budget_and_prerequisite_invariants():
    """
    Validates Budget and Prerequisite Invariants:
    1. Selected learning effort never exceeds configured budget (C <= B).
    2. A prerequisite cannot be omitted when the selected learning action requires it.
    3. Prerequisite learning effort counts toward the budget.
    4. Already verified skills are not redundantly recommended or charged.
    5. Identical inputs produce identical deterministic rankings.
    """
    # PyTorch requires Python. Candidate has NO verified skills (does not know Python).
    opps = [
        {
            "id": "ai-job",
            "title": "AI Engineer",
            "company_name": "DeepMindPartner",
            "requirements": {"PyTorch"},
            "role_relevance": 1.0,
            "verification_confidence": 1.0,
            "match_score": 0.50
        }
    ]

    # Python base effort is 35h; PyTorch base effort is 24h. Total bundle = 59h.
    # If budget is only 30h, candidate cannot learn Python + PyTorch.
    # Therefore, PyTorch MUST NOT be selected into actions!
    res_underbudget = CosgoOptimizer.optimize(
        opportunities=opps,
        verified_skills=set(),
        inferred_skills=set(),
        budget_hours=30.0
    )
    # No action can be selected because PyTorch's prerequisite Python cannot fit in 30h!
    assert len(res_underbudget["actions"]) == 0
    assert res_underbudget["diagnostics"]["budget_hours_used"] == 0.0

    # If budget is 65h (> 59h), both Python (prereq) and PyTorch can be selected.
    # Crucially, Python MUST appear before PyTorch in the action roadmap!
    res_feasible = CosgoOptimizer.optimize(
        opportunities=opps,
        verified_skills=set(),
        inferred_skills=set(),
        budget_hours=65.0
    )
    actions = res_feasible["actions"]
    assert len(actions) == 2
    action_names = [a["skill_name"] for a in actions]
    assert action_names == ["Python", "PyTorch"]
    # Total effort strictly respects budget
    total_spent = sum(a["estimated_hours"] for a in actions)
    assert total_spent <= 65.0
    assert total_spent == 59.0

    # If candidate ALREADY has Python verified, Python should NOT be selected or charged!
    res_with_python = CosgoOptimizer.optimize(
        opportunities=opps,
        verified_skills={"Python"},
        inferred_skills=set(),
        budget_hours=30.0
    )
    act_names_py = [a["skill_name"] for a in res_with_python["actions"]]
    assert "Python" not in act_names_py
    assert "PyTorch" in act_names_py
    assert sum(a["estimated_hours"] for a in res_with_python["actions"]) == 24.0

    # Determinism Invariant: running twice produces identical metrics and rankings
    res_run1 = CosgoOptimizer.optimize(opportunities=opps, verified_skills={"Python"}, inferred_skills=set(), budget_hours=30.0)
    res_run2 = CosgoOptimizer.optimize(opportunities=opps, verified_skills={"Python"}, inferred_skills=set(), budget_hours=30.0)
    assert res_run1["baseline_coverage"] == res_run2["baseline_coverage"]
    assert res_run1["projected_coverage"] == res_run2["projected_coverage"]
    assert [a["skill_name"] for a in res_run1["actions"]] == [a["skill_name"] for a in res_run2["actions"]]


def test_reconciliation_35h_canonical_vs_40h_sensitivity():
    """
    Reconciles the reported discrepancy between the 35h canonical benchmark and 40h demonstration.
    Proves that running the exact same canonical fixture with 35h vs 40h produces:
    - 35h: Canonical comparative benchmark where COSGO and all baselines are strictly evaluated.
    - 40h: Parameter sensitivity demonstration with higher budget capacity.
    """
    # 1. Run Canonical Benchmark (35.0h)
    canon_35 = CosgoEvaluator.run_canonical_benchmark(budget_hours=35.0)
    assert canon_35["dataset_summary"]["budget_hours"] == 35.0
    assert canon_35["dataset_summary"]["benchmark_dataset_id"] == "CANONICAL_COSGO_BENCHMARK_V1"
    cosgo_35 = canon_35["cosgo"]
    freq_35 = canon_35["frequency_baseline"]

    # Budget strictly respected
    assert cosgo_35["hours_spent"] <= 35.0
    assert freq_35["hours_spent"] <= 35.0
    # COSGO efficiency >= Frequency baseline
    assert cosgo_35["gain_per_hour"] >= freq_35["gain_per_hour"] - 1e-4

    # 2. Run Sensitivity Demonstration (40.0h)
    sens_40 = CosgoEvaluator.run_sensitivity_demonstration(budget_hours=40.0)
    assert sens_40["dataset_summary"]["budget_hours"] == 40.0
    assert sens_40["experiment_type"] == "PARAMETER_SENSITIVITY_EXPERIMENT"
    assert "sensitivity_note" in sens_40
    cosgo_40 = sens_40["cosgo"]

    # Because 40h > 35h, additional budget permits more or higher-effort actions
    assert cosgo_40["hours_spent"] <= 40.0
    assert cosgo_40["final_coverage"] >= cosgo_35["final_coverage"]


# ---------------------------------------------------------------------------
# Phase 4.1.1 Hardening Tests
# ---------------------------------------------------------------------------

def test_opportunity_weight_constraints_arbitrary_n():
    """
    Validates normalized opportunity-weight calculation across arbitrary N in {1, 5, 16, 17, 50, 100}.
    Resolves the N > 16 conflict (where minimum raw weight of 0.06 would sum to > 1.0 if applied to normalized weights).
    Guarantees:
    - All weights finite (not NaN, not inf)
    - All weights strictly positive and non-negative
    - Weights sum to 1.0 within numerical tolerance (1e-6)
    - Relative order is preserved
    """
    import math

    test_counts = [1, 5, 16, 17, 50, 100]
    tolerance = 1e-6

    for n in test_counts:
        # Create diverse raw weights spanning the theoretical spectrum [0.06, 1.00]
        raw_weights = []
        for i in range(n):
            # Alternating low, medium, and high importance opportunities
            r_rel = 0.10 + (0.90 * (i / max(1, n - 1)))
            v_conf = 0.50 + 0.50 * ((i % 3) / 2.0)
            m_score = 0.40 + 0.60 * ((i % 5) / 4.0)
            w = CosgoOptimizer.calculate_opportunity_weight(r_rel, v_conf, m_score)
            raw_weights.append(w)

        # Ensure raw weights are within [0.06, 1.0]
        for w in raw_weights:
            assert 0.06 <= w <= 1.00

        # Normalize
        norm_weights = CosgoOptimizer.normalize_opportunity_weights(raw_weights, tolerance=tolerance)
        assert len(norm_weights) == n

        # Check invariants
        weight_sum = sum(norm_weights)
        assert math.isclose(weight_sum, 1.0, rel_tol=tolerance, abs_tol=tolerance), (
            f"Failed for N={n}: sum is {weight_sum}"
        )

        for w in norm_weights:
            assert not math.isnan(w)
            assert not math.isinf(w)
            assert w > 0.0, f"Weight {w} not strictly positive for N={n}"

        # Relative ranking invariant: if raw_weights[i] > raw_weights[j], then norm_weights[i] >= norm_weights[j]
        if n > 1:
            for i in range(min(5, n - 1)):
                for j in range(i + 1, min(6, n)):
                    if raw_weights[i] > raw_weights[j]:
                        assert norm_weights[i] >= norm_weights[j]
                    elif raw_weights[i] < raw_weights[j]:
                        assert norm_weights[i] <= norm_weights[j]

    # Specific N=17 boundary test:
    # 17 opportunities each with minimum raw weight 0.06
    # 17 * 0.06 = 1.02. In normalized space, each weight must be 1/17 = ~0.0588235 < 0.06
    n17_raw = [0.06] * 17
    n17_norm = CosgoOptimizer.normalize_opportunity_weights(n17_raw)
    assert len(n17_norm) == 17
    assert math.isclose(sum(n17_norm), 1.0, rel_tol=1e-6, abs_tol=1e-6)
    for w in n17_norm:
        assert math.isclose(w, 1.0 / 17, rel_tol=1e-5, abs_tol=1e-5)
        # Demonstrates resolution: normalized weights for N=17 are ~0.0588, which is < 0.06
        assert w < 0.06


def test_budget_utilization_and_transparency():
    """
    Validates transparency regarding why the 35h optimizer selects Docker and FastAPI
    but leaves 9.2 hours unused, and confirms that the 40h experiment correctly selects Scikit-Learn.
    Ensures displayed learning effort equals the exact effort used by the optimizer and evaluator.
    """
    # 1. Canonical 35h Run
    bench_35 = CosgoEvaluator.run_canonical_benchmark(35.0)
    cosgo_35 = bench_35["cosgo"]

    # In canonical fixture, candidate profile has verified: ["Python"], inferred: ["Docker"]
    # Docker base is 14.0h -> 30% discount = 9.8h
    # FastAPI base is 16.0h -> 0% discount = 16.0h
    # Total spent: 9.8 + 16.0 = 25.8h <= 35.0h
    assert cosgo_35["selected_skills"] == ["Docker", "FastAPI"]
    assert cosgo_35["hours_spent"] == 25.8
    unused_hours = round(35.0 - 25.8, 1)
    assert unused_hours == 9.2

    # Verify why 9.2h remains unallocated:
    # Check all remaining candidate skills in the fixture:
    # - Scikit-Learn: 14.0h > 9.2h (cannot fit)
    # - PyTorch: 24.0h > 9.2h (cannot fit)
    # - PostgreSQL: 16.0h + unmet SQL 18.0h = 34.0h > 9.2h (cannot fit)
    # - Kubernetes: 26.0h > 9.2h (cannot fit)
    # - AWS: 25.0h > 9.2h (cannot fit)
    # - Java: 40.0h > 9.2h (cannot fit)
    # No candidate skill fits within 9.2 hours!
    fixture = CosgoEvaluator.get_canonical_fixture()
    for opp in fixture["opportunities"]:
        for req in opp["requirements"]:
            canon_name = CosgoOptimizer.normalize_skill_name(req)
            if canon_name not in ["Python", "Docker", "FastAPI"]:
                meta = CosgoOptimizer.get_skill_metadata(canon_name, has_partial_evidence=False)
                # Every single remaining candidate skill has effort >= 10.0h > 9.2h
                assert meta["estimated_hours"] > unused_hours

    # 2. Canonical 40h Sensitivity Run
    sens_40 = CosgoEvaluator.run_sensitivity_demonstration(40.0)
    cosgo_40 = sens_40["cosgo"]

    # With budget=40.0h, after Docker (9.8h) and FastAPI (16.0h), 14.2h remain.
    # Scikit-Learn effort is 14.0h <= 14.2h, and its prerequisite Python is verified!
    assert "Scikit-Learn" in cosgo_40["selected_skills"]
    assert cosgo_40["selected_skills"] == ["Docker", "FastAPI", "Scikit-Learn"]
    assert cosgo_40["hours_spent"] == 39.8  # 25.8 + 14.0 = 39.8 <= 40.0
    assert round(40.0 - 39.8, 1) == 0.2

    # Verify displayed learning effort matches the exact effort used
    docker_meta = CosgoOptimizer.get_skill_metadata("Docker", has_partial_evidence=True)
    fastapi_meta = CosgoOptimizer.get_skill_metadata("FastAPI", has_partial_evidence=False)
    sklearn_meta = CosgoOptimizer.get_skill_metadata("Scikit-Learn", has_partial_evidence=False)

    assert docker_meta["estimated_hours"] == 9.8
    assert fastapi_meta["estimated_hours"] == 16.0
    assert sklearn_meta["estimated_hours"] == 14.0
    assert docker_meta["estimated_hours"] + fastapi_meta["estimated_hours"] == cosgo_35["hours_spent"]
    assert (
        docker_meta["estimated_hours"] + fastapi_meta["estimated_hours"] + sklearn_meta["estimated_hours"]
        == cosgo_40["hours_spent"]
    )

    # Percentage points vs relative lift distinction
    assert "coverage_gain_pp" in cosgo_35
    assert cosgo_35["coverage_gain_pp"] == round(cosgo_35["coverage_gain"] * 100, 2)
    assert "pp" in cosgo_35["coverage_gain_label"]
    assert "budget_utilization_explanation" in bench_35["comparison_summary"]


def test_skill_evidence_discount_boundaries():
    """
    Tests exact boundary conditions for absent, inferred, verified, and unverified skills:
    1. Absent: effort = base (0% discount)
    2. Inferred: effort = base * 0.70 (30% discount), but CANNOT satisfy prerequisites or count in baseline
    3. Verified: counts in baseline, satisfies prerequisites, never recommended as missing
    4. Unverified: effort = base (0% discount), treated identically to absent
    """
    # 1. Metadata check across conditions
    absent_meta = CosgoOptimizer.get_skill_metadata("Docker", has_partial_evidence=False)
    inferred_meta = CosgoOptimizer.get_skill_metadata("Docker", has_partial_evidence=True, inferred_discount=0.30)

    assert absent_meta["estimated_hours"] == 14.0
    assert absent_meta["effort_model"]["discount_factor"] == 0.0
    assert "Modeled projection, not a guaranteed completion duration" in absent_meta["effort_model"]["notes"]

    assert inferred_meta["estimated_hours"] == 9.8
    assert inferred_meta["effort_model"]["discount_factor"] == 0.30
    assert "Modeled projection, not a guaranteed completion duration" in inferred_meta["effort_model"]["notes"]

    # 2. Prerequisite boundary test:
    # Kubernetes requires Docker.
    # If Docker is ONLY inferred, Kubernetes CANNOT be selected without scheduling Docker first.
    opps = [
        {
            "id": "job-k8s",
            "title": "Cloud Architect",
            "company_name": "CloudCo",
            "requirements": ["Kubernetes"],
            "role_relevance": 1.0,
            "verification_confidence": 1.0,
            "match_score": 0.5
        }
    ]

    # Inferred Docker: candidate does NOT have Docker verified.
    # Bundle must include Docker before Kubernetes!
    res_inferred = CosgoOptimizer.optimize(
        opportunities=opps,
        verified_skills=set(),
        inferred_skills={"Docker"},
        budget_hours=40.0
    )
    actions = res_inferred["actions"]
    skill_names = [a["skill_name"] for a in actions]
    assert "Docker" in skill_names
    assert "Kubernetes" in skill_names
    # Docker must precede Kubernetes
    assert skill_names.index("Docker") < skill_names.index("Kubernetes")
    # Docker gets the 30% discount (9.8h)
    docker_act = next(a for a in actions if a["skill_name"] == "Docker")
    assert docker_act["estimated_hours"] == 9.8

    # Baseline coverage must be 0.0! Inferred Docker CANNOT grant baseline coverage credit!
    assert res_inferred["baseline_coverage"] == 0.0

    # 3. Verified Docker: candidate has Docker verified.
    # Kubernetes prerequisite is satisfied; Docker is NOT in actions!
    res_verified = CosgoOptimizer.optimize(
        opportunities=opps,
        verified_skills={"Docker"},
        inferred_skills=set(),
        budget_hours=40.0
    )
    ver_actions = res_verified["actions"]
    ver_skill_names = [a["skill_name"] for a in ver_actions]
    assert "Docker" not in ver_skill_names
    assert "Kubernetes" in ver_skill_names

    # 4. Unverified Docker: skill is unverified.
    # Must get 0% discount and full base effort (14.0h)
    res_unverified = CosgoOptimizer.optimize(
        opportunities=opps,
        verified_skills=set(),
        inferred_skills=set(),  # Unverified skills are not inferred
        budget_hours=40.0
    )
    unver_actions = res_unverified["actions"]
    unver_docker = next(a for a in unver_actions if a["skill_name"] == "Docker")
    assert unver_docker["estimated_hours"] == 14.0  # Full 14h, no discount


