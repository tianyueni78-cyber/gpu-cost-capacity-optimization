# GPU Optimize Capacity Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the first sellable GPU Optimize slice: convert an audited baseline and user-confirmed capacity constraints into feasible, explainable team allocation scenarios and an approval report.

**Architecture:** Keep intake and audit unchanged. Add a pure Python capacity-problem builder, a SciPy MILP solver, scenario comparison, reporting, and a four-page Streamlit flow that exposes only implemented capacity capability. Procurement and runtime configuration remain separate later plans because each needs different inputs and validation.

**Tech Stack:** Python 3, pandas, SciPy `optimize.milp`, Streamlit, unittest

**Spec:** `docs/superpowers/specs/2026-09-09-gpu-optimize-design.md`

## Global Constraints

- All hard constraints must be satisfied before cost is minimized.
- A low-utilization observation alone must never authorize resource release.
- Users must confirm demand, SLA spare capacity, sharing eligibility, and GPU compatibility.
- Infeasible problems return conflicts; they never silently relax constraints.
- Outputs are approval proposals and never production execution commands.
- Only the implemented capacity module is visible in this phase.

---

### Task 1: Capacity input contract and validation

**Files:**
- Modify: `requirements.txt`
- Create: `src/capacity.py`
- Create: `tests/test_capacity.py`

**Interfaces:**
- Consumes: audited `inventory`, `usage`, and `sla` pandas DataFrames.
- Produces: `CapacityInput`, `TeamRequirement`, `build_capacity_input(tables, confirmed_demands)` and `validate_capacity_input(problem)`.

- [ ] **Step 1: Write the failing contract tests**

```python
import unittest
import pandas as pd

from src.capacity import build_capacity_input, validate_capacity_input


class CapacityInputTest(unittest.TestCase):
    def test_builds_confirmed_team_requirements(self):
        tables = {
            "inventory": pd.DataFrame([
                {"resource_pool_id": "p1", "team_id": "search", "gpu_model": "H100", "gpu_count": 32, "region": "us", "effective_hourly_rate_usd": 3.0},
            ]),
            "usage": pd.DataFrame([
                {"team_id": "search", "resource_pool_id": "p1", "active_gpu_count": 18},
            ]),
            "sla": pd.DataFrame([
                {"team_id": "search", "region": "us", "min_spare_capacity_pct": 20},
            ]),
        }
        problem = build_capacity_input(tables, {"search": 18})
        self.assertEqual(problem.teams[0].minimum_gpu_count, 22)
        self.assertEqual(validate_capacity_input(problem), [])

    def test_rejects_unconfirmed_or_impossible_demand(self):
        problem = build_capacity_input({"inventory": pd.DataFrame(), "usage": pd.DataFrame(), "sla": pd.DataFrame()}, {})
        self.assertIn("至少确认一个团队需求", validate_capacity_input(problem))
```

- [ ] **Step 2: Run the tests and confirm the missing module failure**

Run: `python -m unittest tests.test_capacity -v`

Expected: `ModuleNotFoundError: No module named 'src.capacity'`.

- [ ] **Step 3: Implement the minimum immutable input model**

```python
from dataclasses import dataclass
from math import ceil

import pandas as pd


@dataclass(frozen=True)
class TeamRequirement:
    team_id: str
    confirmed_demand: int
    spare_capacity_pct: float
    minimum_gpu_count: int


@dataclass(frozen=True)
class CapacityInput:
    total_gpu_count: int
    teams: tuple[TeamRequirement, ...]


def build_capacity_input(tables: dict[str, pd.DataFrame], confirmed_demands: dict[str, int]) -> CapacityInput:
    inventory = tables.get("inventory", pd.DataFrame())
    sla = tables.get("sla", pd.DataFrame())
    spare_by_team = sla.groupby("team_id")["min_spare_capacity_pct"].max().to_dict() if not sla.empty else {}
    teams = tuple(
        TeamRequirement(team, int(demand), float(spare_by_team.get(team, 0)), ceil(demand * (1 + float(spare_by_team.get(team, 0)) / 100)))
        for team, demand in sorted(confirmed_demands.items())
    )
    total = int(pd.to_numeric(inventory.get("gpu_count", pd.Series(dtype=float)), errors="coerce").sum())
    return CapacityInput(total, teams)


def validate_capacity_input(problem: CapacityInput) -> list[str]:
    errors = []
    if not problem.teams:
        errors.append("至少确认一个团队需求")
    if any(team.confirmed_demand < 0 or not 0 <= team.spare_capacity_pct <= 100 for team in problem.teams):
        errors.append("需求必须非负，备用容量必须在 0% 到 100% 之间")
    return errors
```

- [ ] **Step 4: Declare the existing SciPy runtime dependency and run tests**

Add `scipy>=1.16,<2` to `requirements.txt`.

Run: `python -m unittest tests.test_capacity -v`

Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```powershell
git add requirements.txt src/capacity.py tests/test_capacity.py
git commit -m "feat: define gpu capacity constraints"
```

### Task 2: Exact feasible-capacity solver

**Files:**
- Modify: `src/capacity.py`
- Modify: `tests/test_capacity.py`

**Interfaces:**
- Consumes: `CapacityInput`.
- Produces: `CapacitySolution`, `solve_capacity(problem)`; infeasible cases use `status="infeasible"` and list concrete conflicts.

- [ ] **Step 1: Add failing feasible and infeasible tests**

```python
from src.capacity import CapacityInput, TeamRequirement, solve_capacity

def test_solver_keeps_required_capacity_and_releases_surplus(self):
    problem = CapacityInput(32, (TeamRequirement("search", 18, 20, 22),))
    result = solve_capacity(problem)
    self.assertEqual(result.status, "optimal")
    self.assertEqual(result.team_allocations, {"search": 22})
    self.assertEqual(result.shared_gpu_count, 10)

def test_solver_explains_capacity_shortfall(self):
    problem = CapacityInput(20, (TeamRequirement("search", 18, 20, 22),))
    result = solve_capacity(problem)
    self.assertEqual(result.status, "infeasible")
    self.assertIn("缺少 2 张 GPU", result.conflicts)
```

- [ ] **Step 2: Run tests and confirm `solve_capacity` is missing**

Run: `python -m unittest tests.test_capacity -v`

Expected: import failure for `solve_capacity`.

- [ ] **Step 3: Implement the minimal integer model**

Use one integer decision variable per team plus one shared-pool variable. Team allocations have lower bounds equal to confirmed demand plus spare capacity; the equality constraint allocates the available inventory. Use `scipy.optimize.milp` with zero cost on team allocations and `-1` on the shared-pool variable so surplus is maximized only after hard requirements are met. Return an explicit shortfall before calling the solver when total minimum demand exceeds inventory.

```python
@dataclass(frozen=True)
class CapacitySolution:
    status: str
    team_allocations: dict[str, int]
    shared_gpu_count: int
    conflicts: tuple[str, ...]


def solve_capacity(problem: CapacityInput) -> CapacitySolution:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp

    required = sum(team.minimum_gpu_count for team in problem.teams)
    if required > problem.total_gpu_count:
        return CapacitySolution("infeasible", {}, 0, (f"缺少 {required - problem.total_gpu_count} 张 GPU",))
    lower = np.array([team.minimum_gpu_count for team in problem.teams] + [0.0])
    upper = np.full(len(lower), problem.total_gpu_count, dtype=float)
    objective = np.array([0.0] * len(problem.teams) + [-1.0])
    total = LinearConstraint(np.ones((1, len(lower))), problem.total_gpu_count, problem.total_gpu_count)
    result = milp(objective, integrality=np.ones(len(lower)), bounds=Bounds(lower, upper), constraints=total)
    values = np.rint(result.x).astype(int)
    allocations = {team.team_id: int(values[index]) for index, team in enumerate(problem.teams)}
    return CapacitySolution("optimal", allocations, int(values[-1]), ())
```

Keep this first MILP formulation explicit; do not add a solver wrapper hierarchy.

- [ ] **Step 4: Run tests**

Run: `python -m unittest tests.test_capacity -v`

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/capacity.py tests/test_capacity.py
git commit -m "feat: solve minimum safe gpu allocation"
```

### Task 3: Scenario comparison

**Files:**
- Modify: `src/capacity.py`
- Create: `src/scenarios.py`
- Create: `tests/test_scenarios.py`

**Interfaces:**
- Consumes: capacity requirements plus user-confirmed `share_allowed` flags and hourly rates.
- Produces: `build_capacity_scenarios(problem, current_allocations, hourly_rate)` with current, lowest-cost, and low-change rows.

- [ ] **Step 1: Write failing scenario tests**

```python
import unittest
from src.capacity import CapacityInput, TeamRequirement
from src.scenarios import build_capacity_scenarios


class ScenarioTest(unittest.TestCase):
    def test_compares_same_cost_basis(self):
        problem = CapacityInput(32, (TeamRequirement("search", 18, 20, 22),))
        rows = build_capacity_scenarios(problem, {"search": 32}, hourly_rate=3.0, hours=720)
        lowest = next(row for row in rows if row["scenario"] == "安全释放")
        self.assertEqual(lowest["reallocatable_gpu_count"], 10)
        self.assertEqual(lowest["affected_cost_usd"], 21600.0)
        self.assertEqual(lowest["theoretical_savings_usd"], 0.0)
        self.assertEqual(lowest["sla_shortfall_gpu_count"], 0)
```

- [ ] **Step 2: Run test and confirm missing module failure**

Run: `python -m unittest tests.test_scenarios -v`

Expected: `ModuleNotFoundError: No module named 'src.scenarios'`.

- [ ] **Step 3: Implement same-basis comparison**

Build plain dictionaries for `当前方案`, `安全释放`, and `低变更`. Calculate affected cost with the same `hourly_rate * hours` basis, but keep theoretical savings at zero until the procurement module verifies contract and rate effects. The low-change scenario may release at most half of safe surplus; it must never reduce a team below `minimum_gpu_count`.

- [ ] **Step 4: Run focused and full tests**

Run: `python -m unittest tests.test_scenarios -v`

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/capacity.py src/scenarios.py tests/test_scenarios.py
git commit -m "feat: compare gpu capacity scenarios"
```

### Task 4: Infeasibility and approval report

**Files:**
- Create: `src/optimize_reporting.py`
- Create: `tests/test_optimize_reporting.py`

**Interfaces:**
- Consumes: validated inputs and scenario rows.
- Produces: `build_approval_report(problem, scenarios, constraints)` and UTF-8-BOM CSV bytes.

- [ ] **Step 1: Write failing report tests**

```python
import unittest
from src.optimize_reporting import build_approval_report, scenarios_csv


class ReportingTest(unittest.TestCase):
    def test_report_marks_cost_scope_and_customer_decision(self):
        report = build_approval_report({"period": "2026-08"}, [{"scenario": "安全释放", "affected_cost_usd": 21600, "theoretical_savings_usd": 0}], ["20% 备用容量"])
        self.assertIn("受影响成本", report)
        self.assertIn("不是已验证节省", report)
        self.assertIn("客户负责人审批", report)
        self.assertNotIn("自动执行", report)

    def test_csv_is_excel_compatible(self):
        self.assertTrue(scenarios_csv([{"scenario": "当前方案"}]).startswith(b"\xef\xbb\xbf"))
```

- [ ] **Step 2: Run and confirm missing module failure**

Run: `python -m unittest tests.test_optimize_reporting -v`

- [ ] **Step 3: Implement deterministic Markdown and CSV exports**

The Markdown sections must be: decision scope, confirmed constraints, scenario comparison, adjustment detail, risks and assumptions, validation and rollback, and customer approval. Use `pandas.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")` for CSV.

- [ ] **Step 4: Run focused and full tests**

Run: `python -m unittest tests.test_optimize_reporting -v`

Run: `python -m unittest discover -s tests -v`

- [ ] **Step 5: Commit**

```powershell
git add src/optimize_reporting.py tests/test_optimize_reporting.py
git commit -m "feat: export gpu capacity approval package"
```

### Task 5: Four-page capacity-only Streamlit workflow

**Files:**
- Modify: `app.py`
- Modify: `src/workflow.py`
- Modify: `tests/test_app_contract.py`
- Create: `tests/test_app_ui.py`

**Interfaces:**
- Consumes: existing mapped and audited tables, confirmed constraints, scenarios, and report builders.
- Produces: pages `基线接入`, `目标与约束`, `容量优化`, `方案与审批`.

- [ ] **Step 1: Add failing workflow and UI contract tests**

```python
def test_optimization_requires_clean_audit_and_confirmed_constraints(self):
    self.assertFalse(ready_for_optimization(None, False))
    clean = pd.DataFrame([{"status": "通过", "severity": "阻断"}])
    self.assertTrue(ready_for_optimization(clean, True))

def test_only_completed_capacity_pages_are_exposed(self):
    source = Path("app.py").read_text(encoding="utf-8")
    for page in ("基线接入", "目标与约束", "容量优化", "方案与审批"):
        self.assertIn(page, source)
    self.assertNotIn('"运行配置优化"', source)
```

- [ ] **Step 2: Run tests and confirm failures**

Run: `python -m unittest tests.test_app_contract tests.test_app_ui -v`

- [ ] **Step 3: Implement the four-page flow**

Reuse the existing intake and audit UI for `基线接入`. Store mapped tables and audit results in `st.session_state`. The constraints page requires explicit confirmation before solving. The capacity page shows current, lowest-cost, and low-change scenarios with assumptions. The approval page exports Markdown and CSV. Display one persistent notice: “方案仅供审批，不会修改生产资源”.

- [ ] **Step 4: Run all automated checks**

Run: `python -m unittest discover -s tests -v`

Run: `python -m compileall app.py src tests`

Expected: all tests pass and compilation exits 0.

- [ ] **Step 5: Run the local smoke test**

Run: `streamlit run app.py --server.headless true --server.port 8766`

In another terminal run: `curl.exe http://localhost:8766/_stcore/health`

Expected: `ok`.

- [ ] **Step 6: Commit**

```powershell
git add app.py src/workflow.py tests/test_app_contract.py tests/test_app_ui.py
git commit -m "feat: deliver gpu capacity optimization workflow"
```

### Task 6: Pilot documentation and release verification

**Files:**
- Modify: `README.md`
- Create: `docs/GPU-Optimize-容量试点.md`

**Interfaces:**
- Consumes: completed capacity workflow.
- Produces: honest customer-facing scope, 30-minute pilot script, and release checklist.

- [ ] **Step 1: Document only shipped capability**

README must say that capacity allocation is available, while procurement and runtime configuration are planned but not available. The pilot must verify input reconciliation, constraint confirmation, feasible/infeasible behavior, same-basis costs, and customer understanding that approval and execution remain their responsibility.

- [ ] **Step 2: Run release checks**

Run: `python -m unittest discover -s tests -v`

Run: `python -m compileall app.py src tests`

Run: `git diff --check`

Expected: all tests pass, compilation exits 0, and diff check has no output.

- [ ] **Step 3: Commit**

```powershell
git add README.md docs/GPU-Optimize-容量试点.md
git commit -m "docs: prepare gpu optimize capacity pilot"
```

## Later plans

After this capacity phase passes a real-data pilot, create separate plans in this order:

1. Runtime configuration: GPU compatibility matrix, MIG and time-slicing safety rules, validation and rollback.
2. Procurement optimization: recompute stable demand after capacity/runtime changes, simulate actual rates and commitments, and prevent double-counted savings.
3. Joint comparison: combine validated module outputs into the six-page workflow from the product spec.

Do not expose placeholders for these phases in the capacity release.
