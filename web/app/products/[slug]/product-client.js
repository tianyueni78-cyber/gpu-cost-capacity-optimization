"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ROLES = [["inventory", "GPU 资源清单"], ["usage", "GPU 使用记录"], ["billing", "GPU 云账单"], ["sla", "团队 SLA"]];

async function api(path, token, options = {}) {
  const response = await fetch(API + path, { ...options, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(options.headers || {}) } });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "请求失败");
  return data;
}

function fileBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function Metric({ label, value, suffix = "" }) {
  const present = value !== null && value !== undefined;
  return <div className="metric"><small>{label}</small><strong>{present ? value : "数据不足"}{present ? suffix : ""}</strong></div>;
}

export default function ProductClient({ slug }) {
  const [files, setFiles] = useState({});
  const [dataset, setDataset] = useState(null);
  const [result, setResult] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  function token() { const value = localStorage.getItem("gpu_token"); if (!value) location.href = "/"; return value; }

  useEffect(() => {
    if (slug !== "gpu-data") return;
    const datasetId = localStorage.getItem("gpu_data_dataset_id");
    if (!datasetId) return;
    api(`/v1/gpu-data/datasets/${datasetId}`, token()).then(setDataset).then(() =>
      api(`/v1/gpu-data/datasets/${datasetId}/result`, token()).then(setResult).catch(() => {}),
    ).catch(() => localStorage.removeItem("gpu_data_dataset_id"));
  }, [slug]);

  async function useSample() {
    setBusy(true); setMessage(""); setResult(null);
    try { const created = await api("/v1/gpu-data/datasets/sample", token(), { method: "POST" }); setDataset(created); localStorage.setItem("gpu_data_dataset_id", created.dataset_id); }
    catch (error) { setMessage(error.message); } finally { setBusy(false); }
  }

  async function upload() {
    if (ROLES.some(([role]) => !files[role])) { setMessage("请为四张表分别选择一个 CSV 文件。"); return; }
    setBusy(true); setMessage(""); setResult(null);
    try {
      const payload = { files: {} };
      for (const [role] of ROLES) payload.files[role] = { file_name: files[role].name, content_base64: await fileBase64(files[role]) };
      const created = await api("/v1/gpu-data/datasets", token(), { method: "POST", body: JSON.stringify(payload) }); setDataset(created); localStorage.setItem("gpu_data_dataset_id", created.dataset_id);
    } catch (error) { setMessage(error.message); } finally { setBusy(false); }
  }

  async function analyze() {
    setBusy(true); setMessage("真实分析正在后台运行…"); setResult(null);
    try {
      await api(`/v1/gpu-data/datasets/${dataset.dataset_id}/analyze`, token(), { method: "POST", body: JSON.stringify({ idempotency_key: `gpu-data-${dataset.dataset_id}` }) });
      for (let attempt = 0; attempt < 90; attempt += 1) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        try { const completed = await api(`/v1/gpu-data/datasets/${dataset.dataset_id}/result`, token()); setResult(completed); setMessage(""); return; }
        catch (error) { if (error.message !== "分析结果尚未生成") throw error; }
      }
      throw new Error("分析仍在运行，请稍后刷新重试。");
    } catch (error) { setMessage(error.message); } finally { setBusy(false); }
  }

  async function download(artifact) {
    const response = await fetch(`${API}/v1/gpu-data/artifacts/${artifact.artifact_id}`, { headers: { Authorization: `Bearer ${token()}` } });
    if (!response.ok) { setMessage("报告下载失败"); return; }
    const link = document.createElement("a"); link.href = URL.createObjectURL(await response.blob()); link.download = artifact.file_name; link.click(); URL.revokeObjectURL(link.href);
  }

  if (slug !== "gpu-data") return <p className="muted">该产品将在 GPU Data 真实闭环验证后接入。</p>;
  const summary = result?.summary || {};
  return <div className="gpu-flow">
    <section><h2>1. 准备数据</h2><p>先用确定性样例体验，或上传四张 CSV。缺失遥测保留为空，不会填零。</p>
      <button onClick={useSample} disabled={busy}>使用样例数据</button>
      <div className="file-grid">{ROLES.map(([role, label]) => <label key={role}>{label}<input type="file" accept=".csv,text/csv" onChange={event => setFiles(current => ({ ...current, [role]: event.target.files[0] }))} /></label>)}</div>
      <button className="secondary" onClick={upload} disabled={busy}>上传四张 CSV</button>
    </section>
    {dataset && <section><h2>2. 数据集已保存</h2><div className="file-list">{dataset.files?.map(file => <span key={file.role}>{file.role}：{file.file_name}（{file.row_count} 行）</span>)}</div><button onClick={analyze} disabled={busy}>开始真实分析</button></section>}
    {message && <p className="notice">{message}</p>}
    {result && <section><h2>3. 分析结果：{result.status === "SUCCEEDED" ? "已完成" : "数据被阻断"}</h2>
      <div className="metrics"><Metric label="总成本" value={summary.total_cost_usd} suffix=" USD" /><Metric label="已归因成本" value={summary.attributed_cost_usd} suffix=" USD" /><Metric label="未归因成本" value={summary.unattributed_cost_usd} suffix=" USD" /><Metric label="成本归因覆盖率" value={summary.cost_attribution_coverage_pct} suffix="%" /><Metric label="GPU 数量" value={summary.gpu_count} /><Metric label="GPU 遥测覆盖率" value={summary.gpu_telemetry_coverage_pct} suffix="%" /><Metric label="GPU 利用率中位数" value={summary.median_gpu_utilization_pct} suffix="%" /><Metric label="GPU 利用率 P95" value={summary.p95_gpu_utilization_pct} suffix="%" /><Metric label="闲置候选" value={summary.idle_candidate_count} /><Metric label="闲置候选相关成本" value={summary.idle_affected_cost_usd} suffix=" USD" /></div>
      <p>期间：{summary.analysis_period || "因质量问题未生成"}　币种：{summary.currency || "未生成"}　来源：{summary.source || "未生成"}</p>
      {summary.inventory_by_model && <p>按型号：{Object.entries(summary.inventory_by_model).map(([name, count]) => `${name} ${count} 张`).join("；")}</p>}
      {summary.inventory_by_team && <p>按团队：{Object.entries(summary.inventory_by_team).map(([name, count]) => `${name} ${count} 张`).join("；")}</p>}
      <h3>数据质量</h3><p>阻断 {summary.blocking_count} 项，警告 {summary.warning_count} 项。</p>
      {result.audit?.filter(item => item.status === "异常").map(item => <p key={item.check_id} className={item.severity === "阻断" ? "error" : "notice"}>{item.severity}｜{item.message}</p>)}
      <h3>调查线索</h3>{result.signals?.length ? result.signals.map(item => <article key={item.signal_id} className="signal"><b>{item.scope}｜{item.observation}</b><p>{item.evidence}</p><small>相关成本 ${item.affected_cost_usd}，不等于可节省金额。{item.limitation}</small></article>) : <p>没有发布调查线索。</p>}
      <h3>下载交付物</h3><div className="downloads">{result.artifacts?.map(item => <button className="secondary" key={item.artifact_id} onClick={() => download(item)}>{item.file_name}</button>)}</div>
    </section>}
  </div>;
}
