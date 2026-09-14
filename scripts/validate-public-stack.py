"""Verify the public GPU Data -> GPU Optimize flow against the running stack."""

import argparse
import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


def request(base_url, path, *, token=None, payload=None, method=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read()
            if not body:
                return response.status, None
            try:
                return response.status, json.loads(body)
            except json.JSONDecodeError:
                return response.status, body.decode()
    except urllib.error.HTTPError as error:
        body = error.read().decode()
        return error.code, json.loads(body) if body else None


def credentials(env_path):
    values = {}
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        if line and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values["LOCAL_DEV_EMAIL"], values["LOCAL_DEV_PASSWORD"]


def login(base_url, env_path):
    email, password = credentials(env_path)
    status, data = request(base_url, "/v1/dev/login", payload={"email": email, "password": password}, method="POST")
    assert status == 200, data
    tenant = data["tenants"][0]
    status, selected = request(
        base_url,
        "/v1/dev/select",
        token=data["selection_token"],
        payload={"organization_id": tenant["organization_id"], "project_id": tenant["project_id"]},
        method="POST",
    )
    assert status == 200, selected
    return selected["access_token"]


def wait_for_result(base_url, token, dataset_id):
    for _ in range(60):
        status, result = request(base_url, f"/v1/gpu-data/datasets/{dataset_id}/result", token=token)
        if status == 200:
            return result
        time.sleep(0.5)
    raise TimeoutError(f"analysis did not finish: {dataset_id}")


def upload_case(base_url, token, folder):
    files = {}
    for role in ("inventory", "usage", "billing", "sla"):
        path = folder / f"{role}.csv"
        files[role] = {"file_name": path.name, "content_base64": base64.b64encode(path.read_bytes()).decode()}
    status, dataset = request(base_url, "/v1/gpu-data/datasets", token=token, payload={"files": files}, method="POST")
    assert status == 201, dataset
    return dataset


def analyze(base_url, token, dataset):
    dataset_id = dataset["dataset_id"]
    status, job = request(
        base_url,
        f"/v1/gpu-data/datasets/{dataset_id}/analyze",
        token=token,
        payload={"idempotency_key": f"public-validation-{dataset_id}"},
        method="POST",
    )
    assert status == 202, job
    assert job["organization_id"] and job["project_id"] and job["idempotency_key"]
    return wait_for_result(base_url, token, dataset_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--prepared-root", type=Path, default=Path(r"E:\DockerData\gpu-saas\validation\prepared\alibaba-pai-t4-azure-eastus"))
    parser.add_argument("--existing-dataset")
    args = parser.parse_args()
    token = login(args.base_url, args.env)

    if args.existing_dataset:
        status, result = request(args.base_url, f"/v1/gpu-data/datasets/{args.existing_dataset}/result", token=token)
        assert status == 200 and result["status"] == "SUCCEEDED", result
        status, optimized = request(args.base_url, f"/v1/gpu-optimize/datasets/{args.existing_dataset}/recommendations", token=token)
        assert status == 200 and optimized["recommendations"], optimized
        print(json.dumps({"persisted_dataset_id": args.existing_dataset, "result_id": result["result_id"], "recommendation_count": len(optimized["recommendations"])}, indent=2))
        return

    status, normal = request(args.base_url, "/v1/gpu-data/datasets/public-case", token=token, payload={}, method="POST")
    assert status == 201 and normal["source_type"] == "PUBLIC", normal
    normal_result = analyze(args.base_url, token, normal)
    summary = normal_result["summary"]
    assert normal_result["status"] == "SUCCEEDED"
    assert abs(summary["total_cost_usd"] - 1362.3535883333334) < 1e-6
    assert summary["gpu_count"] == 20
    assert summary["gpu_telemetry_coverage_pct"] == 100
    assert abs(summary["median_gpu_utilization_pct"] - 2.6458597815259455) < 1e-6
    assert abs(summary["p95_gpu_utilization_pct"] - 84.97296515627833) < 1e-6

    path = f"/v1/gpu-optimize/datasets/{normal['dataset_id']}/recommendations"
    status, optimized = request(args.base_url, path, token=token, payload={}, method="POST")
    assert status == 201 and optimized["recommendations"], optimized
    assert all(item["theoretical_savings_usd"] == 0 for item in optimized["recommendations"])
    first_ids = [item["recommendation_id"] for item in optimized["recommendations"]]
    status, repeated = request(args.base_url, path, token=token, payload={}, method="POST")
    assert status == 201
    assert first_ids == [item["recommendation_id"] for item in repeated["recommendations"]]
    status, report = request(args.base_url, f"/v1/gpu-optimize/datasets/{normal['dataset_id']}/report", token=token)
    assert status == 200 and "GPU Optimize" in report

    fault_results = {}
    for case in ("blocked", "missing-telemetry"):
        dataset = upload_case(args.base_url, token, args.prepared_root / case)
        result = analyze(args.base_url, token, dataset)
        assert result["status"] == "BLOCKED" and "total_cost_usd" not in result["summary"]
        status, detail = request(
            args.base_url,
            f"/v1/gpu-optimize/datasets/{dataset['dataset_id']}/recommendations",
            token=token,
            payload={},
            method="POST",
        )
        assert status == 409, detail
        fault_results[case] = {"dataset_id": dataset["dataset_id"], "blocking_count": result["summary"]["blocking_count"]}

    print(json.dumps({
        "normal_dataset_id": normal["dataset_id"],
        "result_id": normal_result.get("result_id"),
        "total_cost_usd": summary["total_cost_usd"],
        "gpu_count": summary["gpu_count"],
        "telemetry_coverage_pct": summary["gpu_telemetry_coverage_pct"],
        "median_utilization_pct": summary["median_gpu_utilization_pct"],
        "p95_utilization_pct": summary["p95_gpu_utilization_pct"],
        "recommendation_count": len(optimized["recommendations"]),
        "fault_cases": fault_results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
