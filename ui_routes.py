# ui_routes.py
# Adds two routes to the Starlette app:
#   GET /audit-log  → returns latest audit log as JSON
#   GET /ui         → serves the visual dashboard (json-render style)

import json
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route

import audit_store

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Onboarding Agent — Audit Dashboard</title>
<style>
  :root {
    --bg: #f5f5f0;
    --card: #ffffff;
    --border: #e2e0d8;
    --text: #1a1a18;
    --muted: #6b6b65;
    --success-bg: #eaf3de;
    --success-txt: #27500a;
    --success-bdr: #97c459;
    --warn-bg: #faeeda;
    --warn-txt: #633806;
    --warn-bdr: #ef9f27;
    --err-bg: #fcebeb;
    --err-txt: #501313;
    --err-bdr: #e24b4a;
    --info-bg: #e6f1fb;
    --info-txt: #042c53;
    --info-bdr: #85b7eb;
    --purple-bg: #eeedfe;
    --purple-txt: #26215c;
    --purple-bdr: #afa9ec;
    --radius: 10px;
    --mono: 'Menlo','Consolas','Monaco',monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #1a1a18;
      --card: #242422;
      --border: #3a3a36;
      --text: #e8e6dc;
      --muted: #9c9a90;
      --success-bg: #173404;
      --success-txt: #c0dd97;
      --success-bdr: #3b6d11;
      --warn-bg: #412402;
      --warn-txt: #fac775;
      --warn-bdr: #854f0b;
      --err-bg: #501313;
      --err-txt: #f7c1c1;
      --err-bdr: #a32d2d;
      --info-bg: #042c53;
      --info-txt: #b5d4f4;
      --info-bdr: #185fa5;
      --purple-bg: #26215c;
      --purple-txt: #cecbf6;
      --purple-bdr: #534ab7;
    }
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; font-size: 14px; line-height: 1.6; }
  .topbar { background: var(--card); border-bottom: 1px solid var(--border); padding: 14px 28px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 10; }
  .topbar h1 { font-size: 16px; font-weight: 600; letter-spacing: -0.01em; }
  .topbar .sub { color: var(--muted); font-size: 12px; margin-top: 2px; }
  .refresh-btn { background: var(--info-bg); color: var(--info-txt); border: 1px solid var(--info-bdr); border-radius: 6px; padding: 6px 14px; cursor: pointer; font-size: 13px; font-weight: 500; transition: opacity .15s; }
  .refresh-btn:hover { opacity: .8; }
  .main { max-width: 900px; margin: 0 auto; padding: 28px 20px 60px; }
  .empty { text-align: center; color: var(--muted); padding: 80px 0; font-size: 15px; }
  .empty .icon { font-size: 40px; margin-bottom: 12px; }

  /* Meta card */
  .meta-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px 24px; margin-bottom: 24px; }
  .meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-top: 12px; }
  .meta-item label { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin-bottom: 4px; }
  .meta-item .val { font-size: 14px; font-weight: 500; font-family: var(--mono); word-break: break-all; }
  .meta-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .meta-top h2 { font-size: 15px; font-weight: 600; }

  /* Badges */
  .badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; border: 1px solid; }
  .badge-success { background: var(--success-bg); color: var(--success-txt); border-color: var(--success-bdr); }
  .badge-warn    { background: var(--warn-bg);    color: var(--warn-txt);    border-color: var(--warn-bdr);    }
  .badge-err     { background: var(--err-bg);     color: var(--err-txt);     border-color: var(--err-bdr);     }
  .badge-info    { background: var(--info-bg);    color: var(--info-txt);    border-color: var(--info-bdr);    }
  .badge-purple  { background: var(--purple-bg);  color: var(--purple-txt);  border-color: var(--purple-bdr);  }

  /* Stats row */
  .stats { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }
  .stat-box { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 18px; flex: 1; min-width: 110px; }
  .stat-box .num { font-size: 26px; font-weight: 700; line-height: 1; }
  .stat-box .lbl { font-size: 11px; color: var(--muted); margin-top: 4px; text-transform: uppercase; letter-spacing: .05em; }

  /* Section */
  .section-title { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); margin: 28px 0 12px; }

  /* Planned steps pills */
  .plan-list { display: flex; flex-direction: column; gap: 6px; }
  .plan-item { display: flex; align-items: center; gap: 10px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; }
  .plan-num { background: var(--purple-bg); color: var(--purple-txt); border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0; }
  .plan-tool { font-weight: 600; font-size: 13px; font-family: var(--mono); }
  .plan-params { color: var(--muted); font-size: 12px; font-family: var(--mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  /* Execution trace cards */
  .trace-list { display: flex; flex-direction: column; gap: 12px; }
  .trace-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
  .trace-card.success { border-left: 4px solid var(--success-bdr); }
  .trace-card.failed  { border-left: 4px solid var(--err-bdr); }
  .trace-card.escalated { border-left: 4px solid var(--warn-bdr); }
  .trace-head { display: flex; align-items: center; gap: 10px; padding: 14px 18px; cursor: pointer; user-select: none; }
  .trace-head:hover { background: var(--bg); }
  .trace-step-num { font-size: 12px; font-weight: 700; color: var(--muted); min-width: 24px; }
  .trace-tool { font-family: var(--mono); font-weight: 600; font-size: 14px; flex: 1; }
  .trace-meta { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
  .attempts-label { font-size: 12px; color: var(--muted); }
  .chevron { font-size: 11px; color: var(--muted); transition: transform .2s; }
  .chevron.open { transform: rotate(90deg); }
  .trace-body { border-top: 1px solid var(--border); padding: 14px 18px; display: none; }
  .trace-body.open { display: block; }
  .detail-block { margin-bottom: 12px; }
  .detail-block:last-child { margin-bottom: 0; }
  .detail-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin-bottom: 6px; }
  pre { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 10px 14px; font-size: 12px; font-family: var(--mono); overflow-x: auto; white-space: pre-wrap; word-break: break-all; line-height: 1.5; }
  .result-text { color: var(--success-txt); background: var(--success-bg); border-color: var(--success-bdr); }
  .retry-item { background: var(--warn-bg); border: 1px solid var(--warn-bdr); border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; font-size: 12px; }
  .retry-item:last-child { margin-bottom: 0; }
  .retry-num { font-weight: 700; color: var(--warn-txt); margin-bottom: 4px; }
  .escalation-box { background: var(--err-bg); border: 1px solid var(--err-bdr); border-radius: 6px; padding: 14px 16px; }
  .escalation-box .esc-title { font-weight: 700; color: var(--err-txt); margin-bottom: 8px; }
</style>
</head>
<body>
<div class="topbar">
  <div>
    <h1>Onboarding Agent — Audit Dashboard</h1>
    <div class="sub">Live view of the last workflow run</div>
  </div>
  <button class="refresh-btn" onclick="load()">Refresh</button>
</div>

<div class="main" id="root">
  <div class="empty"><div class="icon">⏳</div>Loading...</div>
</div>

<script>
function statusBadge(s) {
  if (!s) return '';
  const map = {
    complete: 'badge-success', success: 'badge-success',
    escalated: 'badge-warn',
    error: 'badge-err', failed: 'badge-err'
  };
  const cls = map[s] || 'badge-info';
  return `<span class="badge ${cls}">${s}</span>`;
}

function fmt(ts) {
  if (!ts) return '—';
  try { return new Date(ts).toLocaleTimeString(); } catch { return ts; }
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
  const body = el.nextElementSibling;
  const chev = el.querySelector('.chevron');
  body.classList.toggle('open');
  chev.classList.toggle('open');
}

function renderMeta(log) {
  const m = log.workflow_metadata || {};
  const statusCls = {complete:'success',escalated:'warn',error:'err',failed:'err'}[m.final_status] || 'info';
  return `
    <div class="meta-card">
      <div class="meta-top">
        <h2>Workflow run</h2>
        ${statusBadge(m.final_status)}
      </div>
      <div class="meta-grid">
        <div class="meta-item"><label>Workflow ID</label><div class="val">${esc(m.workflow_id||'—')}</div></div>
        <div class="meta-item"><label>Started</label><div class="val">${fmt(m.timestamp_start)}</div></div>
        <div class="meta-item"><label>Duration</label><div class="val">${dur(m.timestamp_start, m.timestamp_end)}</div></div>
        <div class="meta-item"><label>Session ID</label><div class="val">${esc(m.session_id||'—')}</div></div>
      </div>
      <div style="margin-top:14px;padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:8px;font-size:13px;color:var(--muted);">
        <strong style="color:var(--text)">Instruction:</strong> ${esc(m.original_instruction||'—')}
      </div>
    </div>`;
}

function renderStats(log) {
  const m = log.workflow_metadata || {};
  return `
    <div class="stats">
      <div class="stat-box"><div class="num">${m.total_steps_planned||0}</div><div class="lbl">Steps planned</div></div>
      <div class="stat-box"><div class="num" style="color:var(--success-txt)">${m.total_steps_succeeded||0}</div><div class="lbl">Succeeded</div></div>
      <div class="stat-box"><div class="num" style="color:var(--warn-txt)">${m.total_retries||0}</div><div class="lbl">Retries</div></div>
      <div class="stat-box"><div class="num" style="color:var(--err-txt)">${m.escalations||0}</div><div class="lbl">Escalations</div></div>
    </div>`;
}

function renderPlan(log) {
  const steps = log.planned_steps || [];
  if (!steps.length) return '';
  const items = steps.map(s => {
    const params = Object.entries(s.parameters||{}).map(([k,v]) => `${k}: ${JSON.stringify(v)}`).join(', ');
    return `<div class="plan-item">
      <div class="plan-num">${s.step_id}</div>
      <div style="flex:1;overflow:hidden">
        <div class="plan-tool">${esc(s.tool_name)}</div>
        <div class="plan-params">${esc(params)}</div>
      </div>
    </div>`;
  }).join('');
  return `<div class="section-title">Planned steps</div><div class="plan-list">${items}</div>`;
}

function renderTrace(log) {
  const trace = log.execution_trace || [];
  if (!trace.length) return '';
  const cards = trace.map((t, i) => {
    const status = t.status || 'unknown';
    const cardCls = {success:'success',failed:'failed',escalated:'escalated'}[status] || '';
    const attempts = t.attempt_count || 1;
    const recovery = t.recovery || {};
    const retries = recovery.attempts || [];
    const escalation = recovery.escalation_payload;

    // Result block
    let resultHtml = '';
    if (t.outcome?.result) {
      resultHtml = `<div class="detail-block">
        <div class="detail-label">Result</div>
        <pre class="result-text">${esc(t.outcome.result)}</pre>
      </div>`;
    }

    // Error block
    let errorHtml = '';
    if (t.outcome?.error_details) {
      const errs = Array.isArray(t.outcome.error_details)
        ? t.outcome.error_details.join('\\n') : String(t.outcome.error_details);
      errorHtml = `<div class="detail-block">
        <div class="detail-label">Errors</div>
        <pre>${esc(errs)}</pre>
      </div>`;
    }

    // Params block
    const params = t.action?.parameters_used || {};
    const paramsHtml = `<div class="detail-block">
      <div class="detail-label">Parameters used</div>
      <pre>${esc(JSON.stringify(params, null, 2))}</pre>
    </div>`;

    // Retry blocks
    let retryHtml = '';
    if (retries.length) {
      const items = retries.map(r => `<div class="retry-item">
        <div class="retry-num">Attempt ${r.attempt} — ${r.error_type||'error'} ${r.strategy ? `[${r.strategy}]` : ''}</div>
        <div style="color:var(--warn-txt);margin:4px 0">${esc(r.error||'')}</div>
        ${r.corrected_params ? `<div style="color:var(--muted);margin-top:4px">Corrected params: <code>${esc(JSON.stringify(r.corrected_params))}</code></div>` : ''}
      </div>`).join('');
      retryHtml = `<div class="detail-block">
        <div class="detail-label">Retry attempts</div>
        ${items}
      </div>`;
    }

    // Escalation block
    let escHtml = '';
    if (escalation) {
      escHtml = `<div class="detail-block">
        <div class="escalation-box">
          <div class="esc-title">Escalation triggered</div>
          <pre>${esc(JSON.stringify(escalation, null, 2))}</pre>
        </div>
      </div>`;
    }

    const timing = t.timestamp_start && t.timestamp_end
      ? `<span class="attempts-label">${dur(t.timestamp_start, t.timestamp_end)}</span>` : '';

    return `<div class="trace-card ${cardCls}">
      <div class="trace-head" onclick="toggle(this)">
        <div class="trace-step-num">#${t.step_id}</div>
        <div class="trace-tool">${esc(t.tool_name)}</div>
        <div class="trace-meta">
          ${timing}
          ${attempts > 1 ? `<span class="badge badge-warn">${attempts} attempts</span>` : ''}
          ${statusBadge(status)}
          <span class="chevron">▶</span>
        </div>
      </div>
      <div class="trace-body">
        ${paramsHtml}
        ${resultHtml}
        ${errorHtml}
        ${retryHtml}
        ${escHtml}
      </div>
    </div>`;
  }).join('');

  return `<div class="section-title">Execution trace</div><div class="trace-list">${cards}</div>`;
}

async function load() {
  const root = document.getElementById('root');
  try {
    const res = await fetch('/audit-log');
    if (!res.ok) throw new Error('No logs yet');
    const log = await res.json();
    if (!log) throw new Error('No logs yet');
    root.innerHTML = renderMeta(log) + renderStats(log) + renderPlan(log) + renderTrace(log);
  } catch(e) {
    root.innerHTML = `<div class="empty"><div class="icon">🤖</div><div>No workflow runs yet.</div><div style="margin-top:8px;font-size:13px">Send an onboarding request to the agent, then refresh.</div></div>`;
  }
}

load();
setInterval(load, 8000);
</script>
</body>
</html>
"""


async def audit_log_endpoint(request: Request):
    """GET /audit-log — returns the latest audit log as JSON."""
    log = audit_store.get_latest()
    if log is None:
        return JSONResponse({"error": "No runs yet"}, status_code=404)
    return JSONResponse(log)


async def ui_endpoint(request: Request):
    """GET /ui — serves the visual audit dashboard."""
    return HTMLResponse(DASHBOARD_HTML)


def get_ui_routes():
    return [
        Route("/audit-log", audit_log_endpoint, methods=["GET"]),
        Route("/ui", ui_endpoint, methods=["GET"]),
    ]