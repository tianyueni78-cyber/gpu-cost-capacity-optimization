"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ProductClient({ slug }) {
  const [result, setResult] = useState("");

  async function createJob() {
    const token = localStorage.getItem("gpu_token");
    if (!token) {
      location.href = "/";
      return;
    }
    const response = await fetch(API + "/v1/jobs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        product: slug,
        operation: "LOCAL_PRODUCT_RUN",
        idempotency_key: crypto.randomUUID(),
      }),
    });
    const data = await response.json();
    setResult(response.ok ? `任务已创建：${data.job_id}` : (data.detail || "任务创建失败"));
  }

  return <div className="product-action">
    <button onClick={createJob}>创建本地运行任务</button>
    {result && <p>{result}</p>}
  </div>;
}
