# GPU Optimize Capacity Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make GPU Optimize capacity recommendations safe and traceable by isolating model/region scopes, enforcing pool-level sharing authorization, and calculating cost from adjusted pools.

**Architecture:** Keep the existing four-page Streamlit flow. Replace the global capacity total with immutable pool and requirement records, solve each `(gpu_model, region)` scope independently, and emit resource-pool adjustments that drive scenario cost, recommendation evidence, approval state, and exports.

**Tech Stack:** Python 3, pandas, SciPy `optimize.milp`, Streamlit, unittest

**Spec:** `docs/superpowers/specs/2026-09-09-gpu-optimize-capacity-correctness-design.md`

## Global Constraints

- GPU models and regions never substitute for each other.
- Missing sharing authorization defaults to `none`.
- Demand and spare capacity are confirmed per team, model, and region.
- Costs use the adjusted pool's effective hourly rate; no average-rate fallback.
- Infeasibility never relaxes SLA or compatibility constraints.
- Recommendation state is workflow metadata and never changes solver output.
- No cloud, Kubernetes, procurement, MIG, or time-slicing execution is added.

---

### Task 1: Scoped capacity input model

**Files:**
- Modify: `src/capacity.py`
- Modify: `tests/test_capacity.py`

**Interfaces:**
- Produces: `ResourcePool`, scoped `TeamRequirement`, `CapacityInput`, `build_capacity_input(tables, confirmed_demands, sharing_scopes)`.
- `confirmed_demands` keys are `(team_id, gpu_model, region)` tuples.
- `sharing_scopes` maps `resource_pool_id` to `none`, `team`, or `cross_team`.

- [ ] **Step 1: Add failing tests for scope isolation and safe defaults**

```python
def test_builds_separate_model_and_region_requirements(self):
    tables = scoped_tables()
    problem = build_capacity_input(
        tables,
        {("search", "H100", "us-east"): 8, ("search", "A100", "us-east"): 4},
        {"h100-pool": "cross_team", "a100-pool": "team"},
    )
    self.assertEqual({r.scope for r in problem.requirements}, {("H100", "us-east"), ("A100", "us-east")})
    self.assertEqual(problem.pools[0].sharing_scope, "cross_team")

def test_missing_sharing_scope_defaults_to_none(self):
    problem = build_capacity_input(scoped_tables(), {("search", "H100", "us-east"): 8}, {})
    self.assertEqual(problem.pools[0].sharing_scope, "none")
```

- [ ] **Step 2: Run `python -m unittest tests.test_capacity -v`**

Expected: FAIL because current input is team-only and has no pool authorization.

- [ ] **Step 3: Replace the global dataclasses with scoped records**

```python
@dataclass(frozen=True)
class ResourcePool:
    resource_pool_id: str
    team_id: str
    gpu_model: str
    region: str
    gpu_count: int
    hourly_rate_usd: float
    sharing_scope: str

@dataclass(frozen=True)
class TeamRequirement:
    team_id: str
    gpu_model: str
    region: str
    confirmed_demand: int
    spare_capacity_pct: float
    minimum_gpu_count: int

    @property
    def scope(self):
        return self.gpu_model, self.region

@dataclass(frozen=True)
class CapacityInput:
    pools: tuple[ResourcePool, ...]
    requirements: tuple[TeamRequirement, ...]
```

Normalize only surrounding whitespace; preserve model and region labels for evidence. Reject duplicate pool IDs, unsupported sharing values, negative counts/rates, and requirements without matching model/region inventory.

- [ ] **Step 4: Run focused and full tests**

Run: `python -m unittest tests.test_capacity -v`

Run: `python -m unittest discover -s tests -v`

- [ ] **Step 5: Commit**

```powershell
git add src/capacity.py tests/test_capacity.py
git commit -m "refactor: scope gpu capacity inputs"
```

### Task 2: Authorization-aware scoped solver

**Files:**
- Modify: `src/capacity.py`
- Modify: `tests/test_capacity.py`

**Interfaces:**
- Produces: `PoolAdjustment` and `CapacitySolution(adjustments, shared_by_scope, conflicts)`.
- `solve_capacity(problem)` runs one model per `(gpu_model, region)` and aggregates results without cross-scope variables.

- [ ] **Step 1: Add failing authorization tests**

```python
def test_h100_cannot_cover_a100_shortfall(self):
    result = solve_capacity(problem_with_h100_surplus_and_a100_shortfall())
    self.assertIn("A100 / us-east 缺少 2 张 GPU", result.conflicts)

def test_team_scope_cannot_move_capacity_to_another_team(self):
    result = solve_capacity(problem_with_team_only_surplus())
    adjustment = next(a for a in result.adjustments if a.resource_pool_id == "search-h100")
    self.assertEqual(adjustment.cross_team_shared_gpu_count, 0)

def test_cross_team_scope_can_fill_compatible_shortfall(self):
    result = solve_capacity(problem_with_authorized_compatible_share())
    self.assertEqual(result.status, "optimal")
    self.assertEqual(result.shared_by_scope[("H100", "us-east")], 2)
```

- [ ] **Step 2: Run the focused tests**

Expected: FAIL because the current solver has no scoped adjustments.

- [ ] **Step 3: Implement explicit per-scope MILP variables**

For each scope create integer variables for retained quantity per pool and compatible cross-team transfer. Apply these bounds:

```text
none: retained == original count; cross-team transfer == 0
team: 0 <= retained <= original count; cross-team transfer == 0
cross_team: 0 <= retained + cross-team transfer <= original count
```

For every team in the scope, retained own capacity plus authorized incoming transfer must be at least `minimum_gpu_count`. Minimize, in order, uncovered demand, total retained capacity, then number of changed pools. Because SciPy accepts one objective, use coefficients separated by a proven upper bound: `uncovered * (inventory + 1)^2 + retained * (inventory + 1) + changed`. If uncovered is nonzero, return `infeasible` and the exact team/model/region shortfall instead of a candidate recommendation.

- [ ] **Step 4: Run focused and full tests**

Run: `python -m unittest tests.test_capacity -v`

Run: `python -m unittest discover -s tests -v`

- [ ] **Step 5: Commit**

```powershell
git add src/capacity.py tests/test_capacity.py
git commit -m "feat: enforce gpu sharing authorization"
```

### Task 3: Pool-rate scenario accounting

**Files:**
- Modify: `src/scenarios.py`
- Modify: `tests/test_scenarios.py`

**Interfaces:**
- Consumes: `CapacityInput`, `CapacitySolution`, and `period_hours`.
- Produces: scenario summaries plus `pool_adjustments`; no `hourly_rate` parameter remains.

- [ ] **Step 1: Add a failing mixed-rate test**

```python
def test_affected_cost_uses_each_adjusted_pool_rate(self):
    problem = problem_with_pool_rates({"cheap": 1.0, "expensive": 4.0})
    solution = solution_releasing({"cheap": 1, "expensive": 2})
    result = build_capacity_scenarios(problem, solution, period_hours=100)
    safe = next(row for row in result["scenarios"] if row["scenario"] == "安全调整")
    self.assertEqual(safe["affected_cost_usd"], 900.0)
    self.assertEqual(sum(row["affected_cost_usd"] for row in result["pool_adjustments"]), 900.0)
```

- [ ] **Step 2: Run `python -m unittest tests.test_scenarios -v`**

Expected: FAIL because current code accepts one average rate.

- [ ] **Step 3: Calculate resource-pool detail first, then aggregate**

Each detail row includes pool ID, team, model, region, current count, retained count, shared count, releasable count, hourly rate, affected cost, sharing scope, and solver status. Set theoretical savings to zero until procurement rules are implemented.

- [ ] **Step 4: Run focused and full tests**

Run: `python -m unittest tests.test_scenarios -v`

Run: `python -m unittest discover -s tests -v`

- [ ] **Step 5: Commit**

```powershell
git add src/scenarios.py tests/test_scenarios.py
git commit -m "fix: calculate capacity cost by resource pool"
```

### Task 4: Evidence-backed recommendations and approval states

**Files:**
- Create: `src/recommendations.py`
- Create: `tests/test_recommendations.py`
- Modify: `src/optimize_reporting.py`
- Modify: `tests/test_optimize_reporting.py`

**Interfaces:**
- Produces: `build_recommendations(problem, solution, scenario_result, observation_period)`.
- Recommendation fields: `recommendation_id`, `status`, `observation`, `affected_resources`, `period`, `current_configuration`, `proposed_configuration`, `constraints_met`, `affected_cost_usd`, `business_impact`, `sla_risk`, `limitation`, `owner_question`.
- Allowed states: `待确认`, `待审批`, `推迟`, `不适用`.

- [ ] **Step 1: Add failing evidence and status tests**

```python
def test_recommendation_contains_complete_decision_evidence(self):
    item = build_recommendations(problem, solution, scenarios, "2026-08")[0]
    required = {"affected_resources", "period", "current_configuration", "proposed_configuration", "constraints_met", "sla_risk", "limitation", "owner_question"}
    self.assertTrue(required.issubset(item))
    self.assertEqual(item["status"], "待审批")

def test_incomplete_boundary_is_waiting_for_confirmation(self):
    item = build_recommendations(unconfirmed_problem, solution, scenarios, "2026-08")[0]
    self.assertEqual(item["status"], "待确认")
```

- [ ] **Step 2: Run tests and confirm the missing module failure**

Run: `python -m unittest tests.test_recommendations -v`

- [ ] **Step 3: Implement deterministic recommendation records**

Generate one recommendation per compatible scope. Use pool IDs as evidence, never positional row numbers. `待审批` requires complete constraints and an optimal solution; otherwise use `待确认`. Add a pure `set_recommendation_status(items, recommendation_id, status)` function that validates the four allowed states and changes only copied workflow metadata.

- [ ] **Step 4: Extend Markdown and CSV exports**

Add constraint snapshot, recommendation evidence, pool adjustments, solver status, owner question, validation, and rollback sections. Export separate UTF-8-BOM CSV files for recommendations and pool adjustments.

- [ ] **Step 5: Run focused and full tests**

Run: `python -m unittest tests.test_recommendations tests.test_optimize_reporting -v`

Run: `python -m unittest discover -s tests -v`

- [ ] **Step 6: Commit**

```powershell
git add src/recommendations.py src/optimize_reporting.py tests/test_recommendations.py tests/test_optimize_reporting.py
git commit -m "feat: add evidence-backed capacity recommendations"
```

### Task 5: Correctness-first four-page UI

**Files:**
- Modify: `app.py`
- Modify: `src/workflow.py`
- Modify: `tests/test_app_contract.py`
- Modify: `tests/test_app_ui.py`

**Interfaces:**
- Keeps pages: `基线接入`, `目标与约束`, `容量优化`, `方案与审批`.
- Session state adds immutable `constraint_snapshot`, `capacity_solution`, `scenario_result`, and `recommendations`.

- [ ] **Step 1: Add failing UI contract tests**

```python
def test_ui_collects_scoped_demand_and_pool_sharing(self):
    source = Path("app.py").read_text(encoding="utf-8")
    self.assertIn("GPU 型号", source)
    self.assertIn("地域", source)
    self.assertIn("不可共享", source)
    self.assertIn("团队内共享", source)
    self.assertIn("跨团队共享", source)

def test_ui_exposes_evidence_and_approval_state(self):
    source = Path("app.py").read_text(encoding="utf-8")
    self.assertIn("受影响资源", source)
    self.assertIn("观察期间", source)
    self.assertIn("待审批", source)
```

- [ ] **Step 2: Run UI tests and confirm failures**

Run: `python -m unittest tests.test_app_contract tests.test_app_ui -v`

- [ ] **Step 3: Update constraints page**

Show peak observations grouped by team/model/region. Require demand confirmation for every observed scope and a sharing selection for every pool. Save the exact values used by the solver as a constraint snapshot.

- [ ] **Step 4: Update result and approval pages**

Show one section per model/region with solver status, recommendation card, and pool adjustment table. Keep infeasible scopes visible beside feasible scopes. Add approval-state selectors that change metadata only. Download the management report, recommendations CSV, pool adjustments CSV, and constraint snapshot CSV.

- [ ] **Step 5: Run all checks and local smoke test**

Run: `python -m unittest discover -s tests -v`

Run: `python -m compileall app.py src tests`

Run: `streamlit run app.py --server.headless true --server.port 8766`

Run separately: `curl.exe http://localhost:8766/_stcore/health`

Expected: tests pass, compilation exits 0, and health returns `ok`.

- [ ] **Step 6: Commit**

```powershell
git add app.py src/workflow.py tests/test_app_contract.py tests/test_app_ui.py
git commit -m "feat: show scoped gpu optimization evidence"
```

### Task 6: Product documentation and final verification

**Files:**
- Modify: `README.md`
- Modify: `docs/GPU-Optimize-容量试点.md`

**Interfaces:**
- Documents only the shipped scoped-capacity capability.

- [ ] **Step 1: Update product and pilot documentation**

Document model/region isolation, pool sharing scopes, actual pool-rate accounting, evidence fields, approval states, and the unchanged limitation that affected cost is not verified savings. Add pilot checks proving H100/A100 isolation, regional isolation, authorization enforcement, and detail-to-summary reconciliation.

- [ ] **Step 2: Run final verification**

Run: `python -m unittest discover -s tests -v`

Run: `python -m compileall app.py src tests`

Run: `git diff --check`

Expected: all tests pass, compilation exits 0, and diff check has no output.

- [ ] **Step 3: Commit**

```powershell
git add README.md docs/GPU-Optimize-容量试点.md
git commit -m "docs: validate scoped gpu capacity pilot"
```
