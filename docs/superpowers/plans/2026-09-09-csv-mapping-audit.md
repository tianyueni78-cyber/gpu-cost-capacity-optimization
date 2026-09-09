# CSV Intake, Guided Mapping, and Data Audit Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a local Streamlit MVP where a customer uploads four GPU business CSV files, confirms guided field mappings, and receives an automatic, explainable data-audit report without changing or persisting the source files.

**Architecture:** Keep Streamlit as a thin UI. Put CSV decoding and mapping in `src/intake.py`, canonical field definitions in `src/schema.py`, and pure audit rules in `src/audit.py`. Each uploaded file is assigned to a known business role, mapped into canonical names, then audited independently and across tables. The UI stores data only in the current Streamlit session and offers the audit result as a CSV download.

**Tech Stack:** Python 3.11+, pandas, Streamlit, unittest.

---

### Task 1: Project runtime and canonical schemas

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `src/__init__.py`
- Test: `tests/test_schema.py`
- Create: `src/schema.py`

**Steps:**
1. Write tests asserting the four supported table roles exist and that every role defines required fields, a unique-key field, and Chinese labels.
2. Run `python -m unittest tests.test_schema -v`; verify failure because `src.schema` does not exist.
3. Implement immutable table specifications for inventory, usage, billing, and SLA. Include only fields needed by the first product workflow; optional fields remain selectable but do not block mapping.
4. Run the test again; verify it passes.

### Task 2: CSV reading and guided field mapping

**Files:**
- Test: `tests/test_intake.py`
- Create: `src/intake.py`

**Steps:**
1. Write tests for UTF-8/GB18030 CSV reading, exact-name and common-alias suggestions, missing required mappings, duplicate source-column mappings, and non-mutating column renaming.
2. Run `python -m unittest tests.test_intake -v`; verify failure because the intake API is absent.
3. Implement:
   - `read_csv_bytes(content: bytes) -> pd.DataFrame`
   - `suggest_mapping(columns, spec) -> dict[str, str | None]`
   - `validate_mapping(mapping, spec) -> list[str]`
   - `apply_mapping(frame, mapping) -> pd.DataFrame`
4. Keep aliases explicit and narrow. Do not guess by fuzzy matching.
5. Run the tests; verify they pass.

### Task 3: Explainable automatic audit engine

**Files:**
- Test: `tests/test_audit.py`
- Create: `src/audit.py`

**Steps:**
1. Write tests proving the engine detects: empty tables, duplicate keys, required-value gaps, invalid numeric ranges, invalid procurement values, billing formula mismatches, date parse failures, and unmatched resource-pool IDs.
2. Add tests proving valid data passes and missing optional telemetry becomes a warning rather than an invented zero.
3. Run `python -m unittest tests.test_audit -v`; verify failure because the audit API is absent.
4. Implement `audit_tables(tables: dict[str, pd.DataFrame]) -> pd.DataFrame` returning these stable columns:
   `check_id`, `table_name`, `category`, `severity`, `status`, `affected_rows`, `total_rows`, `message`, `action`.
5. Implement only transparent deterministic rules. Never clean or overwrite uploaded data.
6. Run the tests; verify they pass.

### Task 4: Three-step Streamlit workflow

**Files:**
- Create: `app.py`
- Test: `tests/test_app_contract.py`

**Steps:**
1. Write a contract test that imports the app-facing helper and verifies all four upload roles must be mapped before audit can run.
2. Run the test; verify failure for the missing helper.
3. Implement the UI:
   - Step 1: four labelled CSV uploaders with row/column preview.
   - Step 2: pre-filled select boxes for every canonical required/optional field; show mapping errors inline.
   - Step 3: run audit, show pass/warning/block counts, detailed findings, and a CSV download button.
4. Add a clear notice: uploaded data is held only in the current local session; no production changes are executed.
5. Run all tests.

### Task 5: Product handoff and verification

**Files:**
- Modify: `README.md`

**Steps:**
1. Add product purpose, current capability, supported inputs, local start commands, audit interpretation, privacy boundary, and next product milestone.
2. Run `python -m unittest discover -s tests -v`.
3. Run `python -m compileall app.py src tests`.
4. Run a Streamlit headless startup smoke test and confirm the server reaches a healthy state.
5. Run `git diff --check` and inspect `git status --short`.
6. Commit the verified feature branch, merge it into `main`, push `main`, and verify the remote commit.

## Self-review

- The feature stops at audit; it does not silently clean customer data or generate production actions.
- File upload roles are explicit, so table classification cannot silently choose the wrong business table.
- Mapping suggestions are assistive and always user-confirmed.
- Core logic is independent of Streamlit and therefore testable and reusable for a future API.
- No database, authentication service, GPU server, paid cloud component, or new architecture layer is added.
