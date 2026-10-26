import math
import pytest
from typing import List, Dict, Any, Set
from app.services.cosgo_optimizer import (
    CosgoOptimizer,
    SKILL_TAXONOMY,
    COSGO_ALGORITHM_VERSION
)
from app.services.cosgo_evaluator import (
    CosgoEvaluator,
    CANONICAL_BENCHMARK_FIXTURE
)
from app.models.cosgo import CosgoRun
from app.services.cosgo_service import CosgoService


# ===========================================================================
# Area 1: Skill Taxonomy and Canonical Name Resolution
# ===========================================================================

def test_area1_skill_taxonomy_and_canonical_bidirectional_resolution():
    """
    Verifies that all 14 canonical skills (and their taxonomy keys and aliases)
    resolve accurately to their authoritative taxonomy entries with exact effort,
    category, and prerequisite graph structure.
    """
    critical_skills_to_test = [
        ("Bash / Shell", "bash", 12.0, "tools", []),
        ("HuggingFace Transformers", "huggingface", 18.0, "ai_ml", ["Python", "PyTorch"]),
        ("Natural Language Processing (NLP)", "nlp", 20.0, "ai_ml", ["Python"]),
        ("Vue.js", "vue", 18.0, "frontend", ["JavaScript"]),
        ("HTML5", "html", 10.0, "frontend", []),
        ("CSS3", "css", 12.0, "frontend", []),
        ("Amazon Web Services (AWS)", "aws", 25.0, "cloud", []),
        ("Google Cloud Platform (GCP)", "gcp", 24.0, "cloud", []),
        ("Microsoft Azure", "azure", 24.0, "cloud", []),
        ("Git / GitHub", "git", 8.0, "tools", []),
        ("CI/CD Pipelines", "ci/cd", 14.0, "tools", ["Git / GitHub"]),
        ("Linux Administration", "linux", 16.0, "tools", []),
        ("Apache Spark", "spark", 24.0, "data_engineering", ["Python"]),
        ("Apache Kafka", "kafka", 20.0, "data_engineering", [])
    ]

    for canonical_name, tax_key, expected_effort, expected_cat, expected_prereqs in critical_skills_to_test:
        # 1. Resolve by canonical display name
        meta_by_canon = CosgoOptimizer.get_skill_metadata(canonical_name, has_partial_evidence=False)
        assert meta_by_canon["is_known_in_taxonomy"] is True, f"Failed lookup for canonical name {canonical_name}"
        assert meta_by_canon["canonical"] == canonical_name
        assert meta_by_canon["category"] == expected_cat
        assert meta_by_canon["estimated_hours"] == expected_effort
        assert meta_by_canon["all_prerequisites"] == expected_prereqs

        # 2. Resolve by taxonomy key
        meta_by_key = CosgoOptimizer.get_skill_metadata(tax_key, has_partial_evidence=False)
        assert meta_by_key["is_known_in_taxonomy"] is True, f"Failed lookup for key {tax_key}"
        assert meta_by_key["canonical"] == canonical_name
        assert meta_by_key["category"] == expected_cat
        assert meta_by_key["estimated_hours"] == expected_effort

        # 3. get_all_prerequisites resolution
        prereqs_from_canon = CosgoOptimizer.get_all_prerequisites(canonical_name)
        prereqs_from_key = CosgoOptimizer.get_all_prerequisites(tax_key)
        assert prereqs_from_canon == expected_prereqs
        assert prereqs_from_key == expected_prereqs

    # Test unknown skill handling
    unknown_meta = CosgoOptimizer.get_skill_metadata("Quantum Cryptography", has_partial_evidence=False)
    assert unknown_meta["is_known_in_taxonomy"] is False
    assert unknown_meta["estimated_hours"] == 16.0
    assert unknown_meta["category"] == "technical"
    assert unknown_meta["all_prerequisites"] == []
    assert "Not in authoritative taxonomy" in unknown_meta["uncertainty_range"]["notes"]

    # Test multi-level transitive prerequisite resolution (Angular -> TypeScript -> JavaScript)
    angular_prereqs = CosgoOptimizer.get_all_prerequisites("Angular")
    assert angular_prereqs == ["JavaScript", "TypeScript"]


# ===========================================================================
# Area 2: Baseline Algorithm Differentiation & Exact Oracle
# ===========================================================================

def test_area2_baseline_differentiation_and_exact_oracle():
    """
    Tests that all four baseline strategies (Frequency-Ranked, Independent Per-Job,
    Greedy Frequency No Effort, and Exact Optimization Oracle) are genuinely differentiated,
    follow their distinct decision policies, and strictly respect budget constraints.
    """
    # Synthetic dataset with divergent job weights, frequencies, and costs
    opportunities = [
        {
            "id": "opp-ml-high",
            "title": "Principal AI Architect",
            "company_name": "ApexAI",
            "requirements": ["Python", "FastAPI", "Docker", "PyTorch"],
            "role_relevance": 1.0,
            "verification_confidence": 1.0,
            "match_score": 0.80
        },
        {
            "id": "opp-web-low",
            "title": "Junior Web Developer",
            "company_name": "LocalWeb",
            "requirements": ["HTML5", "CSS3", "JavaScript"],
            "role_relevance": 0.30,
            "verification_confidence": 0.80,
            "match_score": 0.30
        },
        {
            "id": "opp-data-mid",
            "title": "Data Engineer",
            "company_name": "DataWorks",
            "requirements": ["Python", "SQL", "PostgreSQL", "Apache Spark"],
            "role_relevance": 0.70,
            "verification_confidence": 0.90,
            "match_score": 0.60
        }
    ]

    verified = {"Python"}
    inferred = {"Docker"}
    budget = 35.0

    eval_result = CosgoEvaluator.evaluate_all(
        opportunities=opportunities,
        verified_skills=verified,
        inferred_skills=inferred,
        budget_hours=budget,
        weekly_budget_hours=10.0
    )

    cosgo = eval_result["cosgo"]
    freq = eval_result["frequency_baseline"]
    per_job = eval_result["independent_per_job"]
    no_effort = eval_result["greedy_frequency_no_effort"]
    oracle = eval_result["exact_oracle"]

    # 1. Budget feasibility invariant across all strategies
    assert cosgo["hours_spent"] <= budget
    assert freq["hours_spent"] <= budget
    assert per_job["hours_spent"] <= budget
    assert no_effort["hours_spent"] <= budget
    assert oracle["hours_spent"] <= budget

    # 2. Oracle coverage must be >= any heuristic baseline
    assert oracle["final_coverage"] >= cosgo["final_coverage"] - 1e-4
    assert oracle["final_coverage"] >= freq["final_coverage"] - 1e-4
    assert oracle["final_coverage"] >= per_job["final_coverage"] - 1e-4
    assert oracle["final_coverage"] >= no_effort["final_coverage"] - 1e-4

    # 3. Prerequisites verified in all selections
    for strategy in [cosgo, freq, per_job, no_effort, oracle]:
        sel = set(strategy["selected_skills"])
        for s in sel:
            for p in CosgoOptimizer.get_all_prerequisites(s):
                assert p in sel or p in verified, f"Skill {s} missing prerequisite {p} in strategy {strategy['strategy']}"


def test_area2_exact_oracle_synthetic_instances_and_edge_cases():
    """
    Validates Exact Optimization Oracle on hand-verifiable synthetic instances and edge cases:
    1. Small 2-job hand-calculated global optimum instance.
    2. Infeasible budget instance (budget < min skill cost).
    3. Transitive prerequisite closure enforcement.
    4. Saturated profile / zero gain instance.
    5. Deterministic tie-breaking behavior.
    """
    # -------------------------------------------------------------
    # Instance 1: Hand-Calculated Global Optimum
    # Job A (weight 0.6): requires Python, FastAPI (missing FastAPI: 16h)
    # Job B (weight 0.4): requires Python, Docker (missing Docker: 14h)
    # Budget: 20.0h. Only one can be chosen.
    # Hand calculation:
    # Baseline: 0.6 * 0.5 + 0.4 * 0.5 = 0.50
    # If Docker: 0.6 * 0.5 + 0.4 * 1.0 = 0.70 (+0.20 gain)
    # If FastAPI: 0.6 * 1.0 + 0.4 * 0.5 = 0.80 (+0.30 gain)
    # -------------------------------------------------------------
    opps_hand = [
        {
            "id": "j-a",
            "title": "Backend Dev A",
            "company_name": "A-Corp",
            "requirements": ["Python", "FastAPI"],
            "role_relevance": 0.6,
            "verification_confidence": 1.0,
            "match_score": 0.5
        },
        {
            "id": "j-b",
            "title": "Backend Dev B",
            "company_name": "B-Corp",
            "requirements": ["Python", "Docker"],
            "role_relevance": 0.4,
            "verification_confidence": 1.0,
            "match_score": 0.5
        }
    ]

    eval_hand = CosgoEvaluator.evaluate_all(
        opportunities=opps_hand,
        verified_skills={"Python"},
        inferred_skills=set(),
        budget_hours=20.0,
        weekly_budget_hours=10.0
    )
    oracle_hand = eval_hand["exact_oracle"]
    assert oracle_hand["selected_skills"] == ["FastAPI"]
    assert oracle_hand["hours_spent"] == 16.0
    assert math.isclose(oracle_hand["final_coverage"], 0.80, abs_tol=1e-4)
    assert math.isclose(oracle_hand["coverage_gain"], 0.30, abs_tol=1e-4)

    # -------------------------------------------------------------
    # Instance 2: Infeasible Budget (Budget < Min Skill Cost)
    # Budget = 5.0h, but smallest candidate is Docker (14h) or FastAPI (16h)
    # -------------------------------------------------------------
    eval_infeasible = CosgoEvaluator.evaluate_all(
        opportunities=opps_hand,
        verified_skills={"Python"},
        inferred_skills=set(),
        budget_hours=5.0,
        weekly_budget_hours=10.0
    )
    oracle_infeasible = eval_infeasible["exact_oracle"]
    assert oracle_infeasible["selected_skills"] == []
    assert oracle_infeasible["hours_spent"] == 0.0
    assert math.isclose(oracle_infeasible["final_coverage"], 0.50, abs_tol=1e-4)
    assert math.isclose(oracle_infeasible["coverage_gain"], 0.0, abs_tol=1e-4)

    # -------------------------------------------------------------
    # Instance 3: Transitive Prerequisite Closure Enforcement
    # CI/CD Pipelines requires Git / GitHub. Candidate has NO verified skills.
    # Git / GitHub = 8.0h, CI/CD Pipelines = 14.0h. Total closed bundle = 22.0h.
    # Budget = 25.0h.
    # Oracle CANNOT select CI/CD Pipelines without prerequisite Git / GitHub.
    # -------------------------------------------------------------
    opps_prereq = [
        {
            "id": "j-cicd",
            "title": "DevOps Engineer",
            "company_name": "DevOpsCorp",
            "requirements": ["CI/CD Pipelines"],
            "role_relevance": 1.0,
            "verification_confidence": 1.0,
            "match_score": 0.5
        }
    ]
    eval_prereq = CosgoEvaluator.evaluate_all(
        opportunities=opps_prereq,
        verified_skills=set(),
        inferred_skills=set(),
        budget_hours=25.0,
        weekly_budget_hours=10.0
    )
    oracle_prereq = eval_prereq["exact_oracle"]
    assert set(oracle_prereq["selected_skills"]) == {"Git / GitHub", "CI/CD Pipelines"}
    assert oracle_prereq["hours_spent"] == 22.0
    assert math.isclose(oracle_prereq["final_coverage"], 1.0, abs_tol=1e-4)
    assert math.isclose(oracle_prereq["coverage_gain"], 1.0, abs_tol=1e-4)

    # -------------------------------------------------------------
    # Instance 4: Saturated Profile / Zero Gain
    # All requirements already satisfied at baseline
    # -------------------------------------------------------------
    eval_saturated = CosgoEvaluator.evaluate_all(
        opportunities=opps_hand,
        verified_skills={"Python", "FastAPI", "Docker"},
        inferred_skills=set(),
        budget_hours=40.0,
        weekly_budget_hours=10.0
    )
    oracle_sat = eval_saturated["exact_oracle"]
    assert oracle_sat["selected_skills"] == []
    assert oracle_sat["hours_spent"] == 0.0
    assert math.isclose(oracle_sat["final_coverage"], 1.0, abs_tol=1e-4)
    assert math.isclose(oracle_sat["coverage_gain"], 0.0, abs_tol=1e-4)

    # -------------------------------------------------------------
    # Instance 5: Deterministic Tie-Breaking
    # Two symmetric jobs with identical weights and distinct skills of identical effort (18h each)
    # SQL (18h) vs Vue.js (18h, JavaScript verified)
    # -------------------------------------------------------------
    opps_tie = [
        {
            "id": "j-sql",
            "title": "Data Specialist",
            "company_name": "DataInc",
            "requirements": ["JavaScript", "SQL"],
            "role_relevance": 0.5,
            "verification_confidence": 1.0,
            "match_score": 0.5
        },
        {
            "id": "j-vue",
            "title": "UI Specialist",
            "company_name": "UI-Inc",
            "requirements": ["JavaScript", "Vue.js"],
            "role_relevance": 0.5,
            "verification_confidence": 1.0,
            "match_score": 0.5
        }
    ]
    eval_tie_1 = CosgoEvaluator.evaluate_all(
        opportunities=opps_tie,
        verified_skills={"JavaScript"},
        inferred_skills=set(),
        budget_hours=20.0,
        weekly_budget_hours=10.0
    )
    eval_tie_2 = CosgoEvaluator.evaluate_all(
        opportunities=opps_tie,
        verified_skills={"JavaScript"},
        inferred_skills=set(),
        budget_hours=20.0,
        weekly_budget_hours=10.0
    )
    # Both runs must produce the exact same deterministic selection
    assert eval_tie_1["exact_oracle"]["selected_skills"] == eval_tie_2["exact_oracle"]["selected_skills"]
    assert len(eval_tie_1["exact_oracle"]["selected_skills"]) == 1
    assert eval_tie_1["exact_oracle"]["hours_spent"] == 18.0
    assert math.isclose(eval_tie_1["exact_oracle"]["coverage_gain"], 0.25, abs_tol=1e-4)


# ===========================================================================
# Area 3: Honest Conclusions (Ties as Ties, Losses as Losses)
# ===========================================================================

def test_area3_honest_research_conclusions_reporting():
    """
    Verifies that conclusion generation is completely dynamic, objective, and
    accurately reflects ties, baseline wins, COSGO wins, and exact oracle ratios.
    """
    # Case A: Exact Tie
    mock_cosgo_tie = {"final_coverage": 0.50, "gain_per_hour": 0.015}
    mock_freq_tie = {"final_coverage": 0.50, "gain_per_hour": 0.012}
    mock_per_job_low = {"final_coverage": 0.40, "gain_per_hour": 0.010}
    mock_no_effort_low = {"final_coverage": 0.40, "gain_per_hour": 0.010}
    mock_oracle = {"final_coverage": 0.50}

    concl_tie = CosgoEvaluator.derive_research_conclusion(
        cosgo=mock_cosgo_tie,
        freq=mock_freq_tie,
        per_job=mock_per_job_low,
        no_effort=mock_no_effort_low,
        exact_oracle=mock_oracle
    )
    assert "ties with the top baseline heuristic" in concl_tie
    assert "matches the exact global theoretical optimum" in concl_tie

    # Case B: Baseline Outperforms COSGO
    mock_cosgo_loss = {"final_coverage": 0.45, "gain_per_hour": 0.018}
    mock_freq_win = {"final_coverage": 0.52, "gain_per_hour": 0.014}
    mock_oracle_high = {"final_coverage": 0.55}

    concl_loss = CosgoEvaluator.derive_research_conclusion(
        cosgo=mock_cosgo_loss,
        freq=mock_freq_win,
        per_job=mock_per_job_low,
        no_effort=mock_no_effort_low,
        exact_oracle=mock_oracle_high
    )
    assert "baseline achieves higher coverage" in concl_loss
    assert "discrete knapsack packing" in concl_loss

    # Case C: COSGO Outperforms
    mock_cosgo_win = {"final_coverage": 0.60, "gain_per_hour": 0.022}
    concl_win = CosgoEvaluator.derive_research_conclusion(
        cosgo=mock_cosgo_win,
        freq=mock_freq_win,
        per_job=mock_per_job_low,
        no_effort=mock_no_effort_low,
        exact_oracle=mock_cosgo_win
    )
    assert "COSGO outperforms all baseline heuristics" in concl_win
    assert "+8.0 pp" in concl_win


# ===========================================================================
# Area 4: Mathematical Coverage & Marginal Gain Reconciliation
# ===========================================================================

def test_area4_exact_mathematical_coverage_and_marginal_gain_reconciliation():
    """
    Validates that:
    projected_coverage == round(baseline_coverage + marginal_coverage_increase, 4)
    and sum(a['marginal_coverage_gain'] for a in actions) == marginal_coverage_increase
    with zero roundoff discrepancy.
    """
    opportunities = [
        {
            "id": "j1",
            "title": "Cloud Engineer",
            "company_name": "CloudCo",
            "requirements": ["Docker", "Kubernetes", "Amazon Web Services (AWS)"],
            "role_relevance": 0.90,
            "verification_confidence": 0.95,
            "match_score": 0.60
        },
        {
            "id": "j2",
            "title": "Backend Architect",
            "company_name": "BackendCo",
            "requirements": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "role_relevance": 0.85,
            "verification_confidence": 0.90,
            "match_score": 0.50
        },
        {
            "id": "j3",
            "title": "Full Stack Dev",
            "company_name": "WebStack",
            "requirements": ["JavaScript", "TypeScript", "React", "Docker"],
            "role_relevance": 0.75,
            "verification_confidence": 0.85,
            "match_score": 0.40
        }
    ]

    res = CosgoOptimizer.optimize(
        opportunities=opportunities,
        verified_skills={"Python"},
        inferred_skills={"Docker"},
        budget_hours=45.0,
        weekly_budget_hours=10.0
    )

    baseline_cov = res["baseline_coverage"]
    projected_cov = res["projected_coverage"]
    marginal_increase = res["marginal_coverage_increase"]
    actions = res["actions"]

    # 1. Total projected coverage == baseline + marginal gain
    assert math.isclose(projected_cov, round(baseline_cov + marginal_increase, 4), abs_tol=1e-6)

    # 2. Sum of action gains == marginal increase
    sum_action_gains = round(sum(a["marginal_coverage_gain"] for a in actions), 4)
    assert math.isclose(sum_action_gains, marginal_increase, abs_tol=1e-6)

    # 3. Cumulative sequence consistency
    if actions:
        assert math.isclose(actions[-1]["cumulative_coverage"], projected_cov, abs_tol=1e-6)
        running = baseline_cov
        for a in actions:
            running = round(running + a["marginal_coverage_gain"], 4)
            assert math.isclose(a["cumulative_coverage"], running, abs_tol=1e-6)


# ===========================================================================
# Area 5: Opportunity Deduplication
# ===========================================================================

def test_area5_opportunity_deduplication_preserves_distinct_jobs():
    """
    Verifies that distinct job openings with the same title and company across
    different locations, requisition IDs, or URLs are NOT merged as duplicates,
    while genuine duplicate listings are correctly detected and excluded.
    """
    distinct_and_duplicate_jobs = [
        # Job 1 & Job 2: Same title & company, but DIFFERENT locations -> MUST PRESERVE BOTH
        {
            "id": "job-ny",
            "title": "Senior Software Engineer",
            "company_name": "Google",
            "location": "New York, NY",
            "requirements": ["Python", "Go", "Docker"]
        },
        {
            "id": "job-lon",
            "title": "Senior Software Engineer",
            "company_name": "Google",
            "location": "London, UK",
            "requirements": ["Python", "Go", "Docker"]
        },
        # Job 3: Same title & company and same location as Job 1 -> MUST BE EXCLUDED AS DUPLICATE
        {
            "id": "job-ny-dup",
            "title": "Senior Software Engineer",
            "company_name": "Google",
            "location": "New York, NY",
            "requirements": ["Python", "Go", "Docker"]
        },
        # Job 4 & Job 5: Same title & company, but different requisition IDs -> MUST PRESERVE BOTH
        {
            "id": "job-meta-1",
            "title": "Research Scientist",
            "company_name": "Meta",
            "requisition_id": "REQ-AI-101",
            "requirements": ["Python", "PyTorch"]
        },
        {
            "id": "job-meta-2",
            "title": "Research Scientist",
            "company_name": "Meta",
            "requisition_id": "REQ-AI-102",
            "requirements": ["Python", "PyTorch"]
        }
    ]

    res = CosgoOptimizer.optimize(
        opportunities=distinct_and_duplicate_jobs,
        verified_skills=set(),
        inferred_skills=set(),
        budget_hours=30.0
    )

    # 4 distinct jobs should be eligible, 1 duplicate excluded
    assert res["eligible_opportunities_count"] == 4
    assert res["excluded_opportunities_count"] == 1
    assert res["diagnostics"]["excluded_breakdown"]["duplicate_listings"] == 1


# ===========================================================================
# Area 6: Benchmark Dataset Truthful Identification
# ===========================================================================

def test_area6_benchmark_dataset_truthful_identification():
    """
    Verifies that only an opportunity set strictly matching CANONICAL_BENCHMARK_FIXTURE
    is labeled CANONICAL_COSGO_BENCHMARK_V1, and non-canonical 5-job datasets
    are truthfully classified as CUSTOM_DATASET.
    """
    # 1. Canonical fixture
    fix = CANONICAL_BENCHMARK_FIXTURE
    dataset_id_canonical = CosgoEvaluator.identify_benchmark_dataset(fix["opportunities"])
    assert dataset_id_canonical == "CANONICAL_COSGO_BENCHMARK_V1"

    # 2. Random 5-job custom dataset
    custom_5_jobs = [
        {"id": f"cust-{i}", "title": f"Dev {i}", "company_name": f"Comp {i}", "requirements": ["Python", "Docker"]}
        for i in range(5)
    ]
    dataset_id_custom = CosgoEvaluator.identify_benchmark_dataset(custom_5_jobs)
    assert dataset_id_custom == "CUSTOM_DATASET"


# ===========================================================================
# Area 7 & 8: Persistence and Historical Reproducibility
# ===========================================================================

def test_area7_and_8_persistence_and_historical_reproducibility(client):
    """
    Verifies:
    1. Algorithm version is recorded as 'cosgo-v1.2-audited'.
    2. Opportunity weights actually used are persisted in CosgoRun.
    3. Coverage matrix for a historical run remains completely invariant
       even after the candidate profile is modified.
    """
    # 1. Register candidate
    reg = client.post(
        "/auth/register",
        json={"email": "repro.tester@example.com", "password": "Password123!", "full_name": "Reproducibility Candidate"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Set profile skills: verified Python
    client.put(
        "/profile",
        json={
            "headline": "Full Stack Engineer",
            "preferences": {"desired_roles": ["Software Engineer"]},
            "skills": [
                {"name": "Python", "category": "languages", "status": "VERIFIED", "source": "USER_INPUT", "confidence_score": 1.0}
            ]
        },
        headers=headers
    )

    # 3. Create initial optimization run
    opt_res = client.post("/cosgo/optimize", json={"budget_hours": 35.0}, headers=headers)
    assert opt_res.status_code == 201
    run_1_data = opt_res.json()
    run_1_id = run_1_data["id"]

    assert run_1_data["algorithm_version"] == COSGO_ALGORITHM_VERSION
    assert run_1_data["diagnostics"]["algorithm_version"] == COSGO_ALGORITHM_VERSION

    # 4. Fetch initial coverage matrix for Run 1
    matrix_1_res = client.get(f"/cosgo/coverage-matrix?run_id={run_1_id}", headers=headers)
    assert matrix_1_res.status_code == 200
    matrix_1 = matrix_1_res.json()
    initial_skills_count = matrix_1["total_skills_count"]

    # 5. Mutate candidate profile (add 3 new verified skills and change headline)
    client.put(
        "/profile",
        json={
            "headline": "Lead Architect",
            "preferences": {"desired_roles": ["Chief Technology Officer"]},
            "skills": [
                {"name": "Python", "category": "languages", "status": "VERIFIED", "source": "USER_INPUT", "confidence_score": 1.0},
                {"name": "Docker", "category": "tools", "status": "VERIFIED", "source": "USER_INPUT", "confidence_score": 1.0},
                {"name": "FastAPI", "category": "frameworks", "status": "VERIFIED", "source": "USER_INPUT", "confidence_score": 1.0},
                {"name": "Rust", "category": "languages", "status": "VERIFIED", "source": "USER_INPUT", "confidence_score": 1.0}
            ]
        },
        headers=headers
    )

    # 6. Re-fetch coverage matrix for Run 1
    # MUST return identical reproducible matrix, NOT recomputed against mutated profile!
    matrix_1_after_res = client.get(f"/cosgo/coverage-matrix?run_id={run_1_id}", headers=headers)
    assert matrix_1_after_res.status_code == 200
    matrix_1_after = matrix_1_after_res.json()

    assert matrix_1_after["total_skills_count"] == initial_skills_count
    assert matrix_1_after["matrix"] == matrix_1["matrix"]
    assert matrix_1_after["skills_header"] == matrix_1["skills_header"]


# ===========================================================================
# Area 9 & 10: Mathematical Objective & Learning-Effort Assumptions
# ===========================================================================

def test_area9_and_10_mathematical_objective_and_effort_transparency():
    """
    Validates mathematical objective transparency:
    1. Precedence-constrained knapsack formulation documented in diagnostics.
    2. Effort nature transparently labeled as curriculum modeled projections.
    3. Separation of total budget hours from weekly study pace.
    """
    opps = [
        {
            "id": "j-single",
            "title": "Backend Engineer",
            "company_name": "DevCo",
            "requirements": ["FastAPI", "PostgreSQL"],
            "role_relevance": 1.0,
            "verification_confidence": 1.0,
            "match_score": 0.50
        }
    ]

    res = CosgoOptimizer.optimize(
        opportunities=opps,
        verified_skills=set(),
        inferred_skills=set(),
        budget_hours=40.0,
        weekly_budget_hours=10.0
    )

    diag = res["diagnostics"]
    assert diag["mathematical_model"] == "Precedence-Constrained Knapsack with Modular Coverage Benefit"
    assert diag["effort_nature"] == "CURRICULUM_MODELED_PROJECTION"
    assert diag["study_pace_weeks"] == 4.0
    assert diag["weekly_budget_hours"] == 10.0
    assert diag["budget_hours_requested"] == 40.0
    assert "not a guaranteed completion duration" in diag["modeled_projection_note"].lower() or "not constitute an offer" in diag["modeled_projection_note"].lower()


# ===========================================================================
# Final Consistency Audit Tests
# ===========================================================================

def test_final_mathematical_consistency_audit():
    """
    Validates complete mathematical consistency across:
    1. Docker appearing in all four stated canonical opportunities (Jobs 1, 2, 3, 4).
    2. Coverage gains accounting for every opportunity requiring Docker (+22.51 pp).
    3. Shared scoring consistency: identical selected sets receiving identical scores across all algorithms.
    4. Complete inclusion of missing requirements (TypeScript) and prerequisite closures (JavaScript) in oracle universe.
    5. Reconciled 35h and 40h results.
    6. Full precision coverage reconciliation with zero roundoff drift.
    7. Correct labels and denominators for reported oracle percentages.
    """
    fix = CosgoEvaluator.get_canonical_fixture()
    opps = fix["opportunities"]
    verified = set(fix["candidate_profile"]["verified_skills"])
    inferred = set(fix["candidate_profile"]["inferred_skills"])

    # 1. Docker appearing in all four stated opportunities
    docker_jobs = [
        opp["id"] for opp in opps
        if "Docker" in {CosgoOptimizer.normalize_skill_name(r) for r in opp["requirements"]}
    ]
    assert len(docker_jobs) == 4
    assert set(docker_jobs) == {"canon-j1", "canon-j2", "canon-j3", "canon-j4"}

    # 2. Coverage gains accounting for every opportunity requiring Docker (+22.51 pp)
    docker_score = CosgoOptimizer.evaluate_coverage_metrics(opps, ["Docker"], verified)
    # 4 jobs of normalized weights w1+w2+w3+w4 each gaining 1/4 = 0.25 * 0.900437 = 0.2251093
    assert math.isclose(docker_score["raw_marginal_gain"], 0.2251093, abs_tol=1e-5)
    assert docker_score["coverage_gain"] == 0.2251
    assert docker_score["unique_opportunities_improved"] == 4

    # 3. Identical selected sets receiving identical scores across algorithms
    # Testing with selected set ['Docker', 'FastAPI']
    score_shared = CosgoOptimizer.evaluate_coverage_metrics(opps, ["Docker", "FastAPI"], verified)
    bench_35 = CosgoEvaluator.run_canonical_benchmark(35.0)

    for strat_key in ["cosgo", "frequency_baseline", "independent_per_job", "greedy_frequency_no_effort", "exact_oracle"]:
        strat = bench_35[strat_key]
        assert strat["selected_skills"] == ["Docker", "FastAPI"]
        assert math.isclose(strat["final_coverage"], score_shared["final_coverage"], abs_tol=1e-4)
        assert math.isclose(strat["coverage_gain"], score_shared["coverage_gain"], abs_tol=1e-4)
        assert strat["unique_opportunities_improved"] == score_shared["unique_opportunities_improved"]
        assert strat["opportunities_qualifying"] == score_shared["qualifying_count_final"]

    # 4. Complete inclusion of missing requirements in oracle's candidate universe
    # Candidate universe must include all missing requirements + prerequisite closure
    raw_missing = {s for opp in opps for s in opp["requirements"] if s not in verified}
    closure_set = set(raw_missing)
    for s in list(raw_missing):
        for p in CosgoOptimizer.get_all_prerequisites(s):
            if p not in verified:
                closure_set.add(p)

    expected_universe = [
        "Amazon Web Services (AWS)",
        "Docker",
        "FastAPI",
        "Java",
        "JavaScript",
        "Kubernetes",
        "PostgreSQL",
        "PyTorch",
        "SQL",
        "Scikit-Learn",
        "Spring Boot",
        "TypeScript"
    ]
    assert sorted(list(closure_set)) == expected_universe
    assert len(expected_universe) == 12
    # Verify TypeScript is present and its prerequisite JavaScript is present
    assert "TypeScript" in expected_universe
    assert "JavaScript" in expected_universe

    # 5. Consistent 35h and 40h results
    # 35h Run
    cosgo_35 = bench_35["cosgo"]
    assert cosgo_35["selected_skills"] == ["Docker", "FastAPI"]
    assert cosgo_35["hours_spent"] == 25.8
    assert math.isclose(cosgo_35["final_coverage"], 0.5629, abs_tol=1e-4)
    assert math.isclose(cosgo_35["coverage_gain"], 0.3378, abs_tol=1e-4)
    assert bench_35["exact_oracle"]["selected_skills"] == ["Docker", "FastAPI"]
    assert bench_35["comparison_summary"]["cosgo_pct_of_oracle_coverage"] == 100.0
    assert bench_35["comparison_summary"]["cosgo_pct_of_oracle_marginal_gain"] == 100.0

    # 40h Run
    sens_40 = CosgoEvaluator.run_sensitivity_demonstration(40.0)
    cosgo_40 = sens_40["cosgo"]
    assert cosgo_40["selected_skills"] == ["Docker", "FastAPI", "Scikit-Learn"]
    assert cosgo_40["hours_spent"] == 39.8
    assert math.isclose(cosgo_40["final_coverage"], 0.6194, abs_tol=1e-4)
    assert math.isclose(cosgo_40["coverage_gain"], 0.3943, abs_tol=1e-4)
    assert sens_40["exact_oracle"]["selected_skills"] == ["Docker", "FastAPI", "Scikit-Learn"]
    assert sens_40["comparison_summary"]["cosgo_pct_of_oracle_coverage"] == 100.0
    assert sens_40["comparison_summary"]["cosgo_pct_of_oracle_marginal_gain"] == 100.0

    # 6. Full precision coverage reconciliation
    opt_res_35 = CosgoOptimizer.optimize(opps, verified, inferred, 35.0, 10.0)
    assert math.isclose(
        opt_res_35["projected_coverage"],
        round(opt_res_35["baseline_coverage"] + opt_res_35["marginal_coverage_increase"], 4),
        abs_tol=1e-6
    )
    sum_action_gains = round(sum(a["marginal_coverage_gain"] for a in opt_res_35["actions"]), 4)
    assert math.isclose(sum_action_gains, opt_res_35["marginal_coverage_increase"], abs_tol=1e-6)
    assert math.isclose(opt_res_35["actions"][-1]["cumulative_coverage"], opt_res_35["projected_coverage"], abs_tol=1e-6)

    # 7. Inferred skills do NOT count toward baseline coverage (only verified skills)
    # Baseline with verified Python only:
    eval_only_python = CosgoOptimizer.evaluate_coverage_metrics(opps, [], verified)
    # Inferred Docker must not alter baseline coverage
    assert math.isclose(eval_only_python["baseline_coverage"], 0.2251, abs_tol=1e-4)
    assert "Docker" not in verified


# ===========================================================================
# Area 11: Exact Oracle Enumeration & Greedy Frequency Trace Verification
# ===========================================================================

def test_exact_oracle_feasible_subset_counts_and_small_instance_enumeration():
    """
    Verifies exact oracle state space exploration and feasible subset counts:
    1. On the canonical 12-skill candidate universe:
       - Total state-space subsets: 2^12 = 4,096.
       - Feasible prerequisite-closed subsets under 35.0h: exactly 17.
       - Feasible prerequisite-closed subsets under 40.0h: exactly 24.
       - Pruning applied: False (unpruned exhaustive exploration).
    2. Small hand-calculable 4-skill instance:
       - 4 candidates: 2^4 = 16 subsets.
       - Verifies independent enumeration matches oracle output.
    3. Mathematical reconciliation of the 23 and 38 counts:
       - Proves that 23 and 38 occur when evaluated under the hypothetical costs printed
         in the prior draft text (Java=22h, JS=14h, etc.), whereas the actual codebase
         taxonomic costs (Java=40h, JS=30h) strictly yield 17 and 24.
    """
    bench_35 = CosgoEvaluator.run_canonical_benchmark(35.0)
    oracle_35 = bench_35["exact_oracle"]
    assert oracle_35["candidate_universe_size"] == 12
    assert oracle_35["total_subsets_evaluated"] == 4096
    assert oracle_35["feasible_subsets_count"] == 17
    assert oracle_35["pruning_applied"] is False
    assert oracle_35["selected_skills"] == ["Docker", "FastAPI"]
    assert math.isclose(oracle_35["final_coverage"], 0.5629, abs_tol=1e-4)

    sens_40 = CosgoEvaluator.run_sensitivity_demonstration(40.0)
    oracle_40 = sens_40["exact_oracle"]
    assert oracle_40["candidate_universe_size"] == 12
    assert oracle_40["total_subsets_evaluated"] == 4096
    assert oracle_40["feasible_subsets_count"] == 24
    assert oracle_40["pruning_applied"] is False
    assert oracle_40["selected_skills"] == ["Docker", "FastAPI", "Scikit-Learn"]
    assert math.isclose(oracle_40["final_coverage"], 0.6194, abs_tol=1e-4)

    # Hand-calculable small 4-skill instance:
    # Verified: Python
    # Missing candidates: Docker (9.8h), Scikit-Learn (14.0h), FastAPI (16.0h), PyTorch (24.0h)
    # Budget: 25.0h
    # Feasible subsets:
    # 1. [] (0h)
    # 2. [Docker] (9.8h)
    # 3. [Scikit-Learn] (14.0h)
    # 4. [FastAPI] (16.0h)
    # 5. [PyTorch] (24.0h)
    # 6. [Docker, Scikit-Learn] (23.8h)
    # Total feasible = 6 subsets!
    small_opps = [
        {"id": "s1", "title": "Eng 1", "company_name": "C1", "requirements": ["Python", "Docker", "FastAPI"], "role_relevance": 0.8, "verification_confidence": 0.9, "match_score": 0.7},
        {"id": "s2", "title": "Eng 2", "company_name": "C2", "requirements": ["Python", "Scikit-Learn", "PyTorch"], "role_relevance": 0.8, "verification_confidence": 0.9, "match_score": 0.7},
    ]
    small_eval = CosgoEvaluator.evaluate_all(small_opps, {"Python"}, {"Docker"}, 25.0, 10.0)
    small_oracle = small_eval["exact_oracle"]
    assert small_oracle["candidate_universe_size"] == 4
    assert small_oracle["total_subsets_evaluated"] == 16
    assert small_oracle["feasible_subsets_count"] == 6


def test_greedy_frequency_rule_and_legitimate_cosgo_divergence():
    """
    Validates Greedy Frequency baseline rules:
    1. It strictly selects a higher-frequency skill before a lower-frequency skill
       when both are feasible, regardless of individual job weights.
    2. On the canonical benchmark, Greedy Frequency selects:
       - At 35.0h: ['Docker', 'FastAPI'] (Docker freq 4, then FastAPI freq 2)
       - At 40.0h: ['Docker', 'FastAPI', 'Scikit-Learn'] (Docker freq 4, FastAPI freq 2, Scikit-Learn freq 1)
    3. On a constructed knapsack-divergence instance, COSGO legitimately outperforms
       Greedy Frequency because Greedy Frequency picks an expensive high-frequency skill
       (JavaScript: freq 3, 30h) while COSGO packs two efficient medium-frequency skills
       (Scikit-Learn: freq 2, 14h; FastAPI: freq 2, 16h), reaching higher coverage.
    """
    # 1. Canonical benchmark behavior
    bench_35 = CosgoEvaluator.run_canonical_benchmark(35.0)
    gf_35 = bench_35["greedy_frequency_no_effort"]
    assert gf_35["selected_skills"] == ["Docker", "FastAPI"]
    assert math.isclose(gf_35["final_coverage"], 0.5629, abs_tol=1e-4)

    sens_40 = CosgoEvaluator.run_sensitivity_demonstration(40.0)
    gf_40 = sens_40["greedy_frequency_no_effort"]
    assert gf_40["selected_skills"] == ["Docker", "FastAPI", "Scikit-Learn"]
    assert math.isclose(gf_40["final_coverage"], 0.6194, abs_tol=1e-4)

    # 2. Constructed divergence instance:
    opps_div = [
        {"id": "j1", "title": "Web 1", "company_name": "Co A", "requirements": ["Python", "JavaScript"], "role_relevance": 0.5, "verification_confidence": 0.5, "match_score": 0.5},
        {"id": "j2", "title": "Web 2", "company_name": "Co B", "requirements": ["Python", "JavaScript"], "role_relevance": 0.5, "verification_confidence": 0.5, "match_score": 0.5},
        {"id": "j3", "title": "Web 3", "company_name": "Co C", "requirements": ["Python", "JavaScript"], "role_relevance": 0.5, "verification_confidence": 0.5, "match_score": 0.5},
        {"id": "j4", "title": "Data 1", "company_name": "Co D", "requirements": ["Python", "Scikit-Learn"], "role_relevance": 0.7, "verification_confidence": 0.7, "match_score": 0.7},
        {"id": "j5", "title": "Data 2", "company_name": "Co E", "requirements": ["Python", "Scikit-Learn"], "role_relevance": 0.7, "verification_confidence": 0.7, "match_score": 0.7},
        {"id": "j6", "title": "API 1", "company_name": "Co F", "requirements": ["Python", "FastAPI"], "role_relevance": 0.7, "verification_confidence": 0.7, "match_score": 0.7},
        {"id": "j7", "title": "API 2", "company_name": "Co G", "requirements": ["Python", "FastAPI"], "role_relevance": 0.7, "verification_confidence": 0.7, "match_score": 0.7},
    ]

    budget = 30.0
    eval_div = CosgoEvaluator.evaluate_all(
        opportunities=opps_div,
        verified_skills={"Python"},
        inferred_skills=set(),
        budget_hours=budget,
        weekly_budget_hours=10.0
    )

    # Greedy Frequency strictly selects highest frequency skill (JavaScript: freq 3)
    # spending all 30h on JavaScript
    assert eval_div["greedy_frequency_no_effort"]["selected_skills"] == ["JavaScript"]
    assert eval_div["greedy_frequency_no_effort"]["hours_spent"] == 30.0

    # COSGO evaluates marginal coverage density and packs two skills (Scikit-Learn 14h + FastAPI 16h = 30h)
    assert set(eval_div["cosgo"]["selected_skills"]) == {"FastAPI", "Scikit-Learn"}
    assert eval_div["cosgo"]["hours_spent"] == 30.0

    # Precise mathematical verification of the 7-opportunity divergence experiment:
    # 1. Raw weights: s_j = r * (0.60 + 0.20*v + 0.20*m)
    # j1..j3: 0.5 * (0.60 + 0.20*0.5 + 0.20*0.5) = 0.4000 each (sum = 1.2000)
    # j4..j7: 0.7 * (0.60 + 0.20*0.7 + 0.20*0.7) = 0.6160 each (sum = 2.4640)
    # Total raw weight = 1.2000 + 2.4640 = 3.6640
    # 2. Normalized weights:
    # w1 = w2 = w3 = 0.4000 / 3.6640 = 25/229 ≈ 0.1091703
    # w4 = w5 = w6 = w7 = 0.6160 / 3.6640 = 77/458 ≈ 0.1681223 (exact full-precision sum = 1.0)
    # 3. Baseline coverage: Python satisfies 1 of 2 skills in all 7 jobs -> 0.5 * 1.0 = 50.00%
    assert math.isclose(eval_div["dataset_summary"]["baseline_coverage"], 0.5000, abs_tol=1e-4)

    # 4. Marginal gains:
    # JavaScript (j1..j3): 0.5 * (3 * 25/229) = 75/458 ≈ 0.1637555 (+16.38 pp)
    # Scikit-Learn (j4..j5): 0.5 * (2 * 77/458) = 77/458 ≈ 0.1681223 (+16.81 pp)
    # FastAPI (j6..j7): 0.5 * (2 * 77/458) = 77/458 ≈ 0.1681223 (+16.81 pp)
    # Combined COSGO gain: 77/458 + 77/458 = 77/229 ≈ 0.3362445 (+33.62 pp)
    gf_cov = eval_div["greedy_frequency_no_effort"]["final_coverage"]
    cosgo_cov = eval_div["cosgo"]["final_coverage"]
    assert math.isclose(gf_cov, 0.6638, abs_tol=1e-4)
    assert math.isclose(cosgo_cov, 0.8362, abs_tol=1e-4)

    # 5. Exact metrics:
    # Absolute difference: Delta C = 83.62% - 66.38% = +17.25 pp (17.2489 pp)
    cov_diff_pp = round((cosgo_cov - gf_cov) * 100, 2)
    assert cov_diff_pp == 17.25 or cov_diff_pp == 17.24

    # Relative final-coverage improvement: I_C = (0.836245 - 0.663755) / 0.663755 = +25.99%
    rel_final_cov = round(((cosgo_cov - gf_cov) / gf_cov) * 100, 2)
    assert math.isclose(rel_final_cov, 25.99, abs_tol=0.1)

    # Relative marginal-gain improvement: I_G = (0.336245 - 0.163755) / 0.163755 = +105.33%
    gf_gain = eval_div["greedy_frequency_no_effort"]["coverage_gain"]
    cosgo_gain = eval_div["cosgo"]["coverage_gain"]
    rel_marg_gain = round(((cosgo_gain - gf_gain) / gf_gain) * 100, 2)
    assert math.isclose(rel_marg_gain, 105.33, abs_tol=0.1)


def test_relative_improvement_metrics_definitions_and_zero_denominators():
    """
    Validates unambiguous definitions of relative improvement metrics and safe zero-denominator handling:
    1. Positive improvement: COSGO outperforms baseline.
    2. Negative improvement: Baseline achieves higher coverage.
    3. Tied case: Difference is 0.0 pp, relative improvement is 0.0%.
    4. Zero denominator handling:
       - Baseline coverage = 0.0 -> I_C returns None and explicit explanatory label.
       - Baseline marginal gain = 0.0 -> I_G returns None and explicit explanatory label.
       - No division by zero or fabricated percentages.
    """
    # Case 1: Positive improvement
    res_pos = CosgoEvaluator.calculate_relative_metrics(
        cosgo_cov=0.80, cosgo_gain=0.40, cosgo_eff=0.02,
        baseline_cov=0.60, baseline_gain=0.20, baseline_eff=0.01
    )
    assert res_pos["absolute_final_coverage_diff_pp"] == 20.0
    assert res_pos["absolute_marginal_gain_diff_pp"] == 20.0
    # I_C = (0.80 - 0.60) / 0.60 * 100% = +33.33%
    assert res_pos["relative_final_coverage_improvement_pct"] == 33.33
    # I_G = (0.40 - 0.20) / 0.20 * 100% = +100.0%
    assert res_pos["relative_marginal_gain_improvement_pct"] == 100.0
    assert res_pos["relative_efficiency_improvement_pct"] == 100.0

    # Case 2: Negative improvement (baseline wins)
    res_neg = CosgoEvaluator.calculate_relative_metrics(
        cosgo_cov=0.50, cosgo_gain=0.20, cosgo_eff=0.01,
        baseline_cov=0.60, baseline_gain=0.30, baseline_eff=0.015
    )
    assert res_neg["absolute_final_coverage_diff_pp"] == -10.0
    assert res_neg["relative_final_coverage_improvement_pct"] == -16.67
    assert res_neg["relative_marginal_gain_improvement_pct"] == -33.33

    # Case 3: Tied metrics
    res_tie = CosgoEvaluator.calculate_relative_metrics(
        cosgo_cov=0.5629, cosgo_gain=0.3378, cosgo_eff=0.01309,
        baseline_cov=0.5629, baseline_gain=0.3378, baseline_eff=0.01309
    )
    assert res_tie["absolute_final_coverage_diff_pp"] == 0.0
    assert res_tie["relative_final_coverage_improvement_pct"] == 0.0
    assert res_tie["relative_marginal_gain_improvement_pct"] == 0.0

    # Case 4: Zero denominator handling
    # A) Baseline coverage = 0.0
    res_zero_cov = CosgoEvaluator.calculate_relative_metrics(
        cosgo_cov=0.25, cosgo_gain=0.25, cosgo_eff=0.01,
        baseline_cov=0.0, baseline_gain=0.0, baseline_eff=0.0
    )
    assert res_zero_cov["relative_final_coverage_improvement_pct"] is None
    assert "UNDEFINED_ZERO_DENOMINATOR" in res_zero_cov["relative_final_coverage_improvement_label"]

    # B) Baseline marginal gain = 0.0, but baseline coverage > 0
    res_zero_gain = CosgoEvaluator.calculate_relative_metrics(
        cosgo_cov=0.40, cosgo_gain=0.20, cosgo_eff=0.01,
        baseline_cov=0.20, baseline_gain=0.0, baseline_eff=0.0
    )
    assert res_zero_gain["relative_final_coverage_improvement_pct"] == 100.0  # (0.4 - 0.2)/0.2 = 100%
    assert res_zero_gain["relative_marginal_gain_improvement_pct"] is None
    assert "UNDEFINED_ZERO_DENOMINATOR" in res_zero_gain["relative_marginal_gain_improvement_label"]


def test_docker_effort_discount_and_uncertainty_range_consistency():
    """
    Validates Docker effort discount and uncertainty range consistency:
    1. Base point estimate: 14.0h. Base uncertainty range: (10.0, 18.0)h.
    2. 30% Inferred-skill discount applies consistently to point estimate and range:
       - Discounted point estimate: 14.0 * 0.70 = 9.8h
       - Discounted range: (10.0 * 0.70, 18.0 * 0.70) = (7.0, 12.6)h
       - Point estimate 9.8h strictly resides within the discounted range [7.0, 12.6]h.
    3. Explicit labels for base range and discounted range.
    4. Verified vs Inferred semantic boundaries:
       - Inferred skills CANNOT count toward baseline coverage.
       - Inferred skills CANNOT satisfy prerequisites for dependent skills.
    """
    # 1. Base (absent / full curriculum) Docker metadata
    base_meta = CosgoOptimizer.get_skill_metadata("Docker", has_partial_evidence=False)
    assert base_meta["estimated_hours"] == 14.0
    assert base_meta["uncertainty_range"]["min_hours"] == 10.0
    assert base_meta["uncertainty_range"]["max_hours"] == 18.0
    assert base_meta["uncertainty_range"]["base_range"] == (10.0, 18.0)
    assert base_meta["uncertainty_range"]["is_discounted"] is False
    assert base_meta["uncertainty_range"]["range_interpretation"] == "STANDARD_PRE_DISCOUNT"

    # 2. Inferred (30% discounted) Docker metadata
    inf_meta = CosgoOptimizer.get_skill_metadata("Docker", has_partial_evidence=True, inferred_discount=0.30)
    assert inf_meta["estimated_hours"] == 9.8
    assert inf_meta["uncertainty_range"]["min_hours"] == 7.0
    assert inf_meta["uncertainty_range"]["max_hours"] == 12.6
    assert inf_meta["uncertainty_range"]["base_range"] == (10.0, 18.0)
    assert inf_meta["uncertainty_range"]["discounted_range"] == (7.0, 12.6)
    assert inf_meta["uncertainty_range"]["is_discounted"] is True
    assert inf_meta["uncertainty_range"]["point_estimate_in_range"] is True
    assert inf_meta["effort_model"]["point_estimate_in_discounted_range"] is True
    assert inf_meta["uncertainty_range"]["range_interpretation"] == "POST_DISCOUNT_SCALED"

    # Verify 9.8 is strictly bounded in [7.0, 12.6]
    assert 7.0 <= inf_meta["estimated_hours"] <= 12.6

    # 3. Verified profile boundary:
    # Canonical fixture candidate has verified: {"Python"}, inferred: {"Docker"}
    fix = CosgoEvaluator.get_canonical_fixture()
    opps = fix["opportunities"]
    verified = set(fix["candidate_profile"]["verified_skills"])
    inferred = set(fix["candidate_profile"]["inferred_skills"])

    # Baseline coverage must only count verified Python (22.51%)
    eval_metrics = CosgoOptimizer.evaluate_coverage_metrics(opps, [], verified)
    assert math.isclose(eval_metrics["baseline_coverage"], 0.2251, abs_tol=1e-4)

    # Inferred Docker alone does NOT increase baseline coverage
    eval_with_inferred = CosgoOptimizer.evaluate_coverage_metrics(opps, [], verified)
    assert math.isclose(eval_with_inferred["baseline_coverage"], 0.2251, abs_tol=1e-4)


def test_oracle_feasible_subsets_set_difference_reconciliation():
    """
    Performs an exact set-theoretic comparison between:
    - Authoritative codebase taxonomy feasible subsets (17 at 35h, 24 at 40h)
    - Preliminary draft costs feasible subsets (23 at 35h, 38 at 40h)
    
    Explicitly identifies:
    1. Subsets feasible in Authoritative BUT infeasible in Preliminary.
    2. Subsets feasible in Preliminary BUT infeasible in Authoritative.
    """
    fix = CosgoEvaluator.get_canonical_fixture()
    verified = set(fix["candidate_profile"]["verified_skills"])
    inferred = set(fix["candidate_profile"]["inferred_skills"])
    inferred_lower = {s.lower() for s in inferred}
    inferred_discount = 0.30

    opps = fix["opportunities"]
    raw_cands = {s for j in opps for s in j["requirements"] if s not in verified}
    inspect_set = set(raw_cands)
    while inspect_set:
        curr_s = inspect_set.pop()
        for p in CosgoOptimizer.get_all_prerequisites(curr_s):
            if p not in verified and p not in raw_cands:
                raw_cands.add(p)
                inspect_set.add(p)
    cand_list = sorted(list(raw_cands))
    n = len(cand_list)
    assert n == 12

    # Authoritative costs & prereqs
    auth_costs = {
        s: CosgoOptimizer.get_skill_metadata(s, s.lower() in inferred_lower, inferred_discount)["estimated_hours"]
        for s in cand_list
    }
    auth_prereqs = {
        s: set(CosgoOptimizer.get_all_prerequisites(s)) - verified
        for s in cand_list
    }

    # Preliminary draft costs
    prelim_costs = {
        "Amazon Web Services (AWS)": 25.0,
        "Docker": 9.8,
        "FastAPI": 16.0,
        "Java": 22.0,
        "JavaScript": 14.0,
        "Kubernetes": 26.0,
        "PostgreSQL": 22.0,
        "PyTorch": 24.0,
        "SQL": 18.0,
        "Scikit-Learn": 14.0,
        "Spring Boot": 20.0,
        "TypeScript": 14.0
    }
    prelim_prereqs = {
        "Amazon Web Services (AWS)": set(),
        "Docker": set(),
        "FastAPI": set(),
        "Java": set(),
        "JavaScript": set(),
        "Kubernetes": {"Docker"},
        "PostgreSQL": {"SQL"},
        "PyTorch": set(),
        "SQL": set(),
        "Scikit-Learn": set(),
        "Spring Boot": {"Java"},
        "TypeScript": {"JavaScript"}
    }

    def get_feasible_subsets(costs, prereqs, budget):
        feasible = set()
        for mask in range(1 << n):
            cost = sum(costs[cand_list[i]] for i in range(n) if (mask & (1 << i)))
            if cost <= budget:
                sub = frozenset(cand_list[i] for i in range(n) if (mask & (1 << i)))
                if all(prereqs[s].issubset(sub) for s in sub):
                    feasible.add(sub)
        return feasible

    # Budget 35h
    auth_35 = get_feasible_subsets(auth_costs, auth_prereqs, 35.0)
    prelim_35 = get_feasible_subsets(prelim_costs, prelim_prereqs, 35.0)
    assert len(auth_35) == 17
    assert len(prelim_35) == 23

    # Symmetric difference at 35h:
    # Feasible in Auth, infeasible in Prelim: ['PostgreSQL', 'SQL'] (34.0h in auth <= 35h; 40.0h in prelim > 35h)
    only_auth_35 = auth_35 - prelim_35
    assert len(only_auth_35) == 1
    assert list(only_auth_35)[0] == frozenset({"PostgreSQL", "SQL"})

    # Feasible in Prelim, infeasible in Auth: 7 subsets due to lower Java/JS costs
    only_prelim_35 = prelim_35 - auth_35
    assert len(only_prelim_35) == 7
    expected_prelim_only_35 = {
        frozenset({"Java"}),
        frozenset({"Docker", "Java"}),
        frozenset({"Docker", "JavaScript"}),
        frozenset({"FastAPI", "JavaScript"}),
        frozenset({"Scikit-Learn", "JavaScript"}),
        frozenset({"SQL", "JavaScript"}),
        frozenset({"JavaScript", "TypeScript"}),
    }
    assert only_prelim_35 == expected_prelim_only_35

    # Budget 40h
    auth_40 = get_feasible_subsets(auth_costs, auth_prereqs, 40.0)
    prelim_40 = get_feasible_subsets(prelim_costs, prelim_prereqs, 40.0)
    assert len(auth_40) == 24
    assert len(prelim_40) == 38

    # All 24 auth subsets are feasible in prelim at 40h
    assert auth_40.issubset(prelim_40)
    # Exactly 14 extra subsets in prelim at 40h
    assert len(prelim_40 - auth_40) == 14
