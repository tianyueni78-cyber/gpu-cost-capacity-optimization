"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const LABELS = {
  "gpu-data": ["GPU Data", "建立可信成本与资源基线"],
  "gpu-optimize": ["GPU Optimize", "生成可审批容量方案"],
  "gpu-improve": ["GPU Improve", "验证行动与实际收益"],
  "gpu-forecast": ["GPU Forecast", "预测容量缺口与采购时点"],
};

async function request(path, options = {}) {
  const response = await fetch(API + path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "请求失败");
  return data;
}

export default function Home() {
  const [email, setEmail] = useState("student@example.com");
  const [password, setPassword] = useState("");
  const [selectionToken, setSelectionToken] = useState("");
  const [tenants, setTenants] = useState([]);
  const [chosen, setChosen] = useState("");
  const [token, setToken] = useState("");
  const [products, setProducts] = useState([]);
  const [status, setStatus] = useState({});
  const [jobs, setJobs] = useState([]);
  const [error, setError] = useState("");

  async function login(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await request("/v1/dev/login", {
        method: "POST", body: JSON.stringify({ email, password }),
      });
      setSelectionToken(data.selection_token);
      setTenants(data.tenants);
      setChosen(`${data.tenants[0].organization_id}|${data.tenants[0].project_id}`);
    } catch (err) { setError(err.message); }
  }

  async function selectTenant() {
    const [organization_id, project_id] = chosen.split("|");
    try {
      const data = await request("/v1/dev/select", {
        method: "POST",
        headers: { Authorization: `Bearer ${selectionToken}` },
        body: JSON.stringify({ organization_id, project_id }),
      });
      setToken(data.access_token);
      localStorage.setItem("gpu_token", data.access_token);
    } catch (err) { setError(err.message); }
  }

  async function load(accessToken) {
    const headers = { Authorization: `Bearer ${accessToken}` };
    const [catalog, health, taskList] = await Promise.all([
      request("/v1/products", { headers }),
      request("/v1/system/status", { headers }),
      request("/v1/jobs", { headers }),
    ]);
    setProducts(catalog.products);
    setStatus(health);
    setJobs(taskList.jobs);
  }

  useEffect(() => {
    const saved = localStorage.getItem("gpu_token");
    if (saved) setToken(saved);
  }, []);
  useEffect(() => {
    if (token) load(token).catch(err => {
      localStorage.removeItem("gpu_token");
      setToken("");
      setError(err.message);
    });
  }, [token]);

  if (!selectionToken && !token) return (
    <main><section className="panel">
      <p className="eyebrow">LOCAL PRODUCTION-EQUIVALENT</p>
      <h1>GPU Cost & Capacity Copilot</h1>
      <p>登录本地环境，进入同一组织下的四个 GPU 产品。</p>
      <form onSubmit={login}>
        <label>邮箱<input value={email} onChange={e => setEmail(e.target.value)} /></label>
        <label>本地密码<input type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>
        <button>登录</button>
      </form>
      {error && <p className="error">{error}</p>}
    </section></main>
  );

  if (!token) return (
    <main><section className="panel">
      <h1>选择组织与项目</h1>
      <select value={chosen} onChange={e => setChosen(e.target.value)}>
        {tenants.map(t => <option key={t.project_id} value={`${t.organization_id}|${t.project_id}`}>{t.organization_name} / {t.project_name}</option>)}
      </select>
      <button onClick={selectTenant}>进入工作台</button>
      {error && <p className="error">{error}</p>}
    </section></main>
  );

  return (
    <main>
      <header><div><p className="eyebrow">GPU FINOPS WORKSPACE</p><h1>产品工作台</h1></div>
        <button className="secondary" onClick={() => {
          localStorage.removeItem("gpu_token");
          setToken("");
          setSelectionToken("");
        }}>退出</button>
      </header>
      <section className="status">
        {["api", "database", "redis", "worker"].map(key =>
          <span key={key} className={status[key]}>{key}：{status[key] || "检查中"}</span>)}
      </section>
      <section className="grid">
        {products.map(slug => <a className="card" key={slug} href={`/products/${slug}`}>
          <small>{slug}</small><h2>{LABELS[slug]?.[0] || slug}</h2>
          <p>{LABELS[slug]?.[1]}</p><b>进入产品 →</b>
        </a>)}
      </section>
      <section className="panel compact"><h2>后台任务</h2>
        {jobs.length
          ? jobs.map(job => <p key={job.job_id}>{job.product} · {job.operation} · {job.status} ({job.progress}%)</p>)
          : <p>暂无任务。</p>}
      </section>
    </main>
  );
}
