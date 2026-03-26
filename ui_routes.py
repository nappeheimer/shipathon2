# ui_routes.py
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route

import audit_store

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Onboarding Agent</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:          #080b10;
    --surface:     #0e1117;
    --surface2:    #151a24;
    --border:      #1e2736;
    --border2:     #2a3548;
    --text:        #e2e8f4;
    --muted:       #5a6a84;
    --accent:      #00e5a0;
    --accent-dim:  #003d2b;
    --accent-glow: rgba(0,229,160,0.15);
    --warn:        #f59e0b;
    --warn-dim:    #3d2800;
    --err:         #f43f5e;
    --err-dim:     #3d0a15;
    --info:        #38bdf8;
    --info-dim:    #0a2a3d;
    --purple:      #a78bfa;
    --purple-dim:  #1e1540;
    --radius:      12px;
    --radius-sm:   8px;
    --mono: 'JetBrains Mono', monospace;
    --sans: 'Syne', sans-serif;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    font-size: 14px;
    line-height: 1.6;
    min-height: 100vh;
  }

  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(var(--border) 1px, transparent 1px),
      linear-gradient(90deg, var(--border) 1px, transparent 1px);
    background-size: 40px 40px;
    opacity: 0.25;
    pointer-events: none;
    z-index: 0;
  }

  .topbar {
    position: sticky; top: 0; z-index: 100;
    background: rgba(8,11,16,0.85);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border);
    padding: 0 32px; height: 60px;
    display: flex; align-items: center; justify-content: space-between;
  }
  .topbar-left { display: flex; align-items: center; gap: 14px; }
  .logo-dot {
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 12px var(--accent);
    animation: pulse 2.5s ease-in-out infinite;
  }
  @keyframes pulse {
    0%,100% { opacity:1; box-shadow: 0 0 10px var(--accent); }
    50%      { opacity:0.5; box-shadow: 0 0 4px var(--accent); }
  }
  .topbar h1 { font-size: 15px; font-weight: 700; letter-spacing: -0.02em; }
  .topbar-badge {
    font-family: var(--mono); font-size: 10px; font-weight: 600;
    background: var(--accent-dim); color: var(--accent);
    border: 1px solid rgba(0,229,160,0.25); border-radius: 4px;
    padding: 2px 8px; letter-spacing: 0.05em;
  }
  .refresh-btn {
    font-family: var(--sans); font-size: 12px; font-weight: 600;
    background: transparent; color: var(--muted);
    border: 1px solid var(--border2); border-radius: var(--radius-sm);
    padding: 6px 14px; cursor: pointer; transition: all .2s;
  }
  .refresh-btn:hover { color: var(--text); background: var(--surface); }

  .input-section {
    position: relative; z-index: 1;
    padding: 20px 32px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  .input-label {
    font-family: var(--mono); font-size: 10px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.12em;
    color: var(--muted); margin-bottom: 10px;
  }
  .input-row { display: flex; gap: 10px; }
  .input-row input {
    flex: 1;
    background: var(--bg); border: 1px solid var(--border2);
    border-radius: var(--radius); padding: 11px 18px;
    font-size: 14px; font-family: var(--sans); color: var(--text); outline: none;
    transition: border-color .2s, box-shadow .2s;
  }
  .input-row input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }
  .input-row input::placeholder { color: var(--muted); }
  .run-btn {
    font-family: var(--sans); font-weight: 700; font-size: 13px;
    background: var(--accent); color: #000;
    border: none; border-radius: var(--radius);
    padding: 11px 24px; cursor: pointer; white-space: nowrap;
    transition: all .2s; display: flex; align-items: center; gap: 8px;
  }
  .run-btn:hover { background: #00ffb0; transform: translateY(-1px); box-shadow: 0 4px 20px rgba(0,229,160,0.3); }
  .run-btn:active { transform: translateY(0); }
  .run-btn:disabled { background: var(--surface2); color: var(--muted); cursor: not-allowed; transform: none; box-shadow: none; }

  .status-bar {
    position: relative; z-index: 1;
    padding: 10px 32px; font-size: 13px; font-weight: 600;
    font-family: var(--mono); display: none;
    align-items: center; gap: 10px;
  }
  .status-bar.running { display: flex; background: var(--info-dim); color: var(--info); border-bottom: 1px solid rgba(56,189,248,0.2); }
  .status-bar.done    { display: flex; background: var(--accent-dim); color: var(--accent); border-bottom: 1px solid rgba(0,229,160,0.2); }
  .status-bar.err     { display: flex; background: var(--err-dim); color: var(--err); border-bottom: 1px solid rgba(244,63,94,0.2); }

  .spinner {
    width: 14px; height: 14px;
    border: 2px solid rgba(56,189,248,0.3); border-top-color: var(--info);
    border-radius: 50%; animation: spin .7s linear infinite; flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .history-bar {
    position: relative; z-index: 1;
    padding: 10px 32px; background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: none; align-items: center; gap: 8px; overflow-x: auto;
  }
  .history-bar::-webkit-scrollbar { display: none; }
  .history-bar.visible { display: flex; }
  .history-label {
    font-family: var(--mono); font-size: 10px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--muted); white-space: nowrap; margin-right: 4px;
  }
  .history-chip {
    font-family: var(--sans); font-size: 12px; font-weight: 600;
    background: var(--surface2); border: 1px solid var(--border2);
    border-radius: 20px; padding: 4px 14px; cursor: pointer;
    white-space: nowrap; color: var(--muted); transition: all .15s;
  }
  .history-chip:hover { color: var(--text); }
  .history-chip.active { background: var(--accent-dim); border-color: rgba(0,229,160,0.4); color: var(--accent); }

  .main {
    position: relative; z-index: 1;
    max-width: 960px; margin: 0 auto; padding: 32px 24px 80px;
  }
  .empty { text-align: center; color: var(--muted); padding: 100px 0; }
  .empty .icon { font-size: 48px; margin-bottom: 16px; }
  .empty .title { font-size: 16px; font-weight: 700; color: var(--text); margin-bottom: 8px; }
  .empty .sub { font-size: 13px; }

  .meta-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 24px; margin-bottom: 20px;
    animation: fadeUp .3s ease both;
  }
  @keyframes fadeUp {
    from { opacity:0; transform:translateY(10px); }
    to   { opacity:1; transform:translateY(0); }
  }
  .meta-top {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 16px; gap: 12px; flex-wrap: wrap;
  }
  .meta-top h2 {
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: var(--muted);
  }
  .meta-grid {
    display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr));
    gap: 16px; margin-bottom: 16px;
  }
  .meta-item label {
    display: block; font-family: var(--mono); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--muted); margin-bottom: 4px;
  }
  .meta-item .val {
    font-family: var(--mono); font-size: 13px; font-weight: 600;
    color: var(--text); word-break: break-all;
  }
  .instruction-box {
    background: var(--bg); border: 1px solid var(--border);
    border-left: 3px solid var(--accent); border-radius: var(--radius-sm);
    padding: 12px 16px; font-size: 13px; color: var(--text);
  }
  .instruction-box strong {
    color: var(--muted); font-weight: 600; margin-right: 8px;
    font-family: var(--mono); font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em;
  }

  .badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: 6px;
    font-size: 11px; font-weight: 700; font-family: var(--mono);
    letter-spacing: 0.04em; text-transform: uppercase;
  }
  .badge::before { content:''; width:6px; height:6px; border-radius:50%; flex-shrink:0; }
  .badge-success { background:var(--accent-dim); color:var(--accent); }
  .badge-success::before { background:var(--accent); box-shadow:0 0 6px var(--accent); }
  .badge-warn    { background:var(--warn-dim); color:var(--warn); }
  .badge-warn::before { background:var(--warn); }
  .badge-err     { background:var(--err-dim); color:var(--err); }
  .badge-err::before { background:var(--err); }
  .badge-info    { background:var(--info-dim); color:var(--info); }
  .badge-info::before { background:var(--info); }
  .badge-purple  { background:var(--purple-dim); color:var(--purple); }
  .badge-purple::before { background:var(--purple); }

  .stats {
    display: grid; grid-template-columns: repeat(4,1fr);
    gap: 12px; margin-bottom: 24px;
    animation: fadeUp .3s ease .05s both;
  }
  @media(max-width:600px){ .stats { grid-template-columns: repeat(2,1fr); } }
  .stat-box {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 18px 20px; transition: border-color .2s;
  }
  .stat-box:hover { border-color: var(--border2); }
  .stat-box .num { font-size: 32px; font-weight: 800; line-height: 1; margin-bottom: 6px; }
  .stat-box .lbl { font-family: var(--mono); font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; }

  .section-title {
    font-family: var(--mono); font-size: 10px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted);
    margin: 28px 0 12px; display: flex; align-items: center; gap: 10px;
  }
  .section-title::after { content:''; flex:1; height:1px; background:var(--border); }

  .plan-list { display: flex; flex-direction: column; gap: 6px; animation: fadeUp .3s ease .1s both; }
  .plan-item {
    display: flex; align-items: center; gap: 14px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 12px 16px; transition: border-color .2s;
  }
  .plan-item:hover { border-color: var(--border2); }
  .plan-num {
    width: 24px; height: 24px; background: var(--purple-dim); color: var(--purple);
    border-radius: 6px; display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; font-family: var(--mono); flex-shrink: 0;
  }
  .plan-tool { font-family: var(--mono); font-weight: 600; font-size: 13px; color: var(--text); min-width: 200px; }
  .plan-params { font-family: var(--mono); font-size: 11px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .trace-list { display: flex; flex-direction: column; gap: 8px; animation: fadeUp .3s ease .15s both; }
  .trace-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); overflow: hidden; transition: border-color .2s;
  }
  .trace-card:hover { border-color: var(--border2); }
  .trace-card.success   { border-left: 3px solid var(--accent); }
  .trace-card.failed    { border-left: 3px solid var(--err); }
  .trace-card.escalated { border-left: 3px solid var(--warn); }

  .trace-head {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 18px; cursor: pointer; user-select: none; transition: background .15s;
  }
  .trace-head:hover { background: var(--surface2); }
  .trace-step-num { font-family: var(--mono); font-size: 11px; font-weight: 700; color: var(--muted); min-width: 28px; }
  .trace-tool { font-family: var(--mono); font-weight: 600; font-size: 13px; color: var(--text); flex: 1; }
  .trace-meta { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
  .timing-label { font-family: var(--mono); font-size: 11px; color: var(--muted); }
  .chevron { font-size: 10px; color: var(--muted); transition: transform .2s; }
  .chevron.open { transform: rotate(90deg); }

  .trace-body { border-top: 1px solid var(--border); padding: 16px 18px; display: none; background: var(--bg); }
  .trace-body.open { display: block; }

  .detail-block { margin-bottom: 14px; }
  .detail-block:last-child { margin-bottom: 0; }
  .detail-label {
    font-family: var(--mono); font-size: 10px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 8px;
  }
  pre {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 12px 14px;
    font-size: 12px; font-family: var(--mono); overflow-x: auto;
    white-space: pre-wrap; word-break: break-all; line-height: 1.6; color: var(--text);
  }
  pre.result-text { background: var(--accent-dim); border-color: rgba(0,229,160,0.2); color: var(--accent); }

  .retry-item {
    background: var(--warn-dim); border: 1px solid rgba(245,158,11,0.2);
    border-radius: var(--radius-sm); padding: 10px 14px; margin-bottom: 8px;
    font-size: 12px; font-family: var(--mono);
  }
  .retry-item:last-child { margin-bottom: 0; }
  .retry-num { font-weight: 700; color: var(--warn); margin-bottom: 4px; }
  .retry-err { color: rgba(245,158,11,0.8); margin: 4px 0; }

  .escalation-box {
    background: var(--err-dim); border: 1px solid rgba(244,63,94,0.2);
    border-radius: var(--radius-sm); padding: 14px 16px;
  }
  .escalation-box .esc-title {
    font-family: var(--mono); font-weight: 700; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--err); margin-bottom: 10px;
  }
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-left">
    <div class="logo-dot"></div>
    <h1>Onboarding Agent</h1>
    <span class="topbar-badge">A2A · v1.0</span>
  </div>
  <button class="refresh-btn" onclick="load()">↻ Refresh</button>
</div>

<div class="input-section">
  <div class="input-label">New onboarding request</div>
  <div class="input-row">
    <input id="prompt" type="text"
      placeholder='e.g. "Onboard Sarah Connor to the Cybersecurity team starting next Monday"'
      onkeydown="if(event.key==='Enter')runWorkflow()" />
    <button class="run-btn" id="run-btn" onclick="runWorkflow()">
      <span>▶</span> Run
    </button>
  </div>
</div>

<div id="status-bar" class="status-bar"></div>
<div id="history-bar" class="history-bar"></div>

<div class="main" id="root">
  <div class="empty">
    <div class="icon">⚡</div>
    <div class="title">Ready to onboard</div>
    <div class="sub">Type a request above and hit Run to start a workflow</div>
  </div>
</div>

<script>
let allLogs = [];
let activeIndex = 0;

function statusBadge(s) {
  if (!s) return '';
  const map = { complete:'badge-success', success:'badge-success', escalated:'badge-warn', error:'badge-err', failed:'badge-err' };
  return `<span class="badge ${map[s]||'badge-info'}">${s}</span>`;
}

function fmt(ts) {
  if (!ts) return '—';
  try { return new Date(ts).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'}); } catch { return ts; }
}

function dur(a, b) {
  if (!a || !b) return '';
  const ms = new Date(b) - new Date(a);
  return ms < 1000 ? `${ms}ms` : `${(ms/1000).toFixed(1)}s`;
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function toggle(el) {
  el.nextElementSibling.classList.toggle('open');
  el.querySelector('.chevron').classList.toggle('open');
}

function renderMeta(log) {
  const m = log.workflow_metadata || {};
  return `<div class="meta-card">
    <div class="meta-top"><h2>Workflow run</h2>${statusBadge(m.final_status)}</div>
    <div class="meta-grid">
      <div class="meta-item"><label>Workflow ID</label><div class="val">${esc(m.workflow_id||'—')}</div></div>
      <div class="meta-item"><label>Started</label><div class="val">${fmt(m.timestamp_start)}</div></div>
      <div class="meta-item"><label>Duration</label><div class="val">${dur(m.timestamp_start,m.timestamp_end)||'—'}</div></div>
      <div class="meta-item"><label>Session</label><div class="val">${esc((m.session_id||'—').substring(0,8)+'…')}</div></div>
    </div>
    <div class="instruction-box"><strong>Instruction</strong>${esc(m.original_instruction||'—')}</div>
  </div>`;
}

function renderStats(log) {
  const m = log.workflow_metadata || {};
  return `<div class="stats">
    <div class="stat-box"><div class="num" style="color:var(--purple)">${m.total_steps_planned||0}</div><div class="lbl">Planned</div></div>
    <div class="stat-box"><div class="num" style="color:var(--accent)">${m.total_steps_succeeded||0}</div><div class="lbl">Succeeded</div></div>
    <div class="stat-box"><div class="num" style="color:${m.total_retries>0?'var(--warn)':'var(--muted)'}">${m.total_retries||0}</div><div class="lbl">Retries</div></div>
    <div class="stat-box"><div class="num" style="color:${m.escalations>0?'var(--err)':'var(--muted)'}">${m.escalations||0}</div><div class="lbl">Escalations</div></div>
  </div>`;
}

function renderPlan(log) {
  const steps = log.planned_steps || [];
  if (!steps.length) return '';
  const items = steps.map(s => {
    const params = Object.entries(s.parameters||{}).map(([k,v])=>`${k}: ${JSON.stringify(v)}`).join('  ·  ');
    return `<div class="plan-item">
      <div class="plan-num">${s.step_id}</div>
      <div class="plan-tool">${esc(s.tool_name)}</div>
      <div class="plan-params">${esc(params)}</div>
    </div>`;
  }).join('');
  return `<div class="section-title">Planned steps</div><div class="plan-list">${items}</div>`;
}

function renderTrace(log) {
  const trace = log.execution_trace || [];
  if (!trace.length) return '';
  const cards = trace.map(t => {
    const status = t.status || 'unknown';
    const cardCls = {success:'success',failed:'failed',escalated:'escalated'}[status]||'';
    const attempts = t.attempt_count || 1;
    const retries = (t.recovery||{}).attempts || [];
    const escalation = (t.recovery||{}).escalation_payload;
    const params = t.action?.parameters_used || {};
    const timing = t.timestamp_start && t.timestamp_end ? `<span class="timing-label">${dur(t.timestamp_start,t.timestamp_end)}</span>` : '';

    let resultHtml = t.outcome?.result ? `<div class="detail-block"><div class="detail-label">Result</div><pre class="result-text">${esc(t.outcome.result)}</pre></div>` : '';
    let errorHtml = '';
    if (t.outcome?.error_details) {
      const errs = Array.isArray(t.outcome.error_details) ? t.outcome.error_details.join('\\n') : String(t.outcome.error_details);
      errorHtml = `<div class="detail-block"><div class="detail-label">Errors</div><pre style="color:var(--err);background:var(--err-dim);border-color:rgba(244,63,94,0.2)">${esc(errs)}</pre></div>`;
    }
    let retryHtml = '';
    if (retries.length) {
      retryHtml = `<div class="detail-block"><div class="detail-label">Retry attempts</div>${
        retries.map(r=>`<div class="retry-item">
          <div class="retry-num">Attempt ${r.attempt} — ${r.error_type||'error'}${r.strategy?` [${r.strategy}]`:''}</div>
          <div class="retry-err">${esc(r.error||'')}</div>
          ${r.corrected_params?`<div style="color:var(--muted);margin-top:6px;font-size:11px">Corrected → <code style="color:var(--warn)">${esc(JSON.stringify(r.corrected_params))}</code></div>`:''}
        </div>`).join('')
      }</div>`;
    }
    let escHtml = escalation ? `<div class="detail-block"><div class="escalation-box"><div class="esc-title">⚠ Escalation triggered</div><pre style="background:transparent;border:none;padding:0;color:var(--err)">${esc(JSON.stringify(escalation,null,2))}</pre></div></div>` : '';

    return `<div class="trace-card ${cardCls}">
      <div class="trace-head" onclick="toggle(this)">
        <div class="trace-step-num">#${t.step_id}</div>
        <div class="trace-tool">${esc(t.tool_name)}</div>
        <div class="trace-meta">
          ${timing}
          ${attempts>1?`<span class="badge badge-warn">${attempts} attempts</span>`:''}
          ${statusBadge(status)}
          <span class="chevron">▶</span>
        </div>
      </div>
      <div class="trace-body">
        <div class="detail-block"><div class="detail-label">Parameters</div><pre>${esc(JSON.stringify(params,null,2))}</pre></div>
        ${resultHtml}${errorHtml}${retryHtml}${escHtml}
      </div>
    </div>`;
  }).join('');
  return `<div class="section-title">Execution trace</div><div class="trace-list">${cards}</div>`;
}

function renderHistory() {
  const bar = document.getElementById('history-bar');
  if (!allLogs.length) { bar.classList.remove('visible'); return; }
  bar.classList.add('visible');
  bar.innerHTML = `<span class="history-label">History</span>` + allLogs.map((log,i) => {
    const m = log.workflow_metadata || {};
    const instr = m.original_instruction || 'Run';
    const name = instr.length > 42 ? instr.substring(0,42)+'…' : instr;
    const dot = m.final_status==='complete'?'✓':m.final_status==='escalated'?'⚠':'✗';
    return `<div class="history-chip${i===activeIndex?' active':''}" onclick="showLog(${i})">${dot} ${esc(name)}</div>`;
  }).join('');
}

function showLog(index) {
  activeIndex = index;
  const log = allLogs[index];
  document.getElementById('root').innerHTML = renderMeta(log)+renderStats(log)+renderPlan(log)+renderTrace(log);
  renderHistory();
}

async function load() {
  try {
    const res = await fetch('/audit-log-all');
    if (!res.ok) throw new Error('none');
    const logs = await res.json();
    if (!logs || !logs.length) throw new Error('none');
    allLogs = logs;
    showLog(activeIndex < logs.length ? activeIndex : 0);
  } catch {
    document.getElementById('root').innerHTML = `<div class="empty"><div class="icon">⚡</div><div class="title">Ready to onboard</div><div class="sub">Type a request above and hit Run to start a workflow</div></div>`;
    document.getElementById('history-bar').classList.remove('visible');
  }
}

async function runWorkflow() {
  const input = document.getElementById('prompt');
  const btn = document.getElementById('run-btn');
  const statusBar = document.getElementById('status-bar');
  const text = input.value.trim();
  if (!text) return;

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Running…';
  statusBar.className = 'status-bar running';
  statusBar.innerHTML = '<div class="spinner"></div> Agent is planning and executing the workflow…';

  try {
    const res = await fetch('/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'message/send',
        id: Date.now().toString(),
        params: {
          message: {
            role: 'user',
            parts: [{ text }],
            messageId: 'msg-' + Date.now()
          }
        }
      })
    });
    if (!res.ok) throw new Error('Request failed');
    statusBar.className = 'status-bar done';
    statusBar.innerHTML = '✓ Workflow complete — loading results…';
    input.value = '';
    activeIndex = 0;
    setTimeout(() => { statusBar.className = 'status-bar'; load(); }, 1000);
  } catch(e) {
    statusBar.className = 'status-bar err';
    statusBar.innerHTML = '✗ Error: ' + e.message;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>▶</span> Run';
  }
}

load();
setInterval(load, 8000);
</script>
</body>
</html>
"""


async def audit_log_endpoint(request: Request):
    log = audit_store.get_latest()
    if log is None:
        return JSONResponse({"error": "No runs yet"}, status_code=404)
    return JSONResponse(log)


async def audit_log_all_endpoint(request: Request):
    logs = audit_store.get_all()
    if not logs:
        return JSONResponse([], status_code=404)
    return JSONResponse(logs)


async def ui_endpoint(request: Request):
    return HTMLResponse(DASHBOARD_HTML)


def get_ui_routes():
    return [
        Route("/audit-log", audit_log_endpoint, methods=["GET"]),
        Route("/audit-log-all", audit_log_all_endpoint, methods=["GET"]),
        Route("/ui", ui_endpoint, methods=["GET"]),
    ]