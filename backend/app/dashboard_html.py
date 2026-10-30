DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Production AI Incident & Root-Cause Assistant</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: { 50: '#eef2ff', 500: '#6366f1', 600: '#4f46e5', 700: '#4338ca' },
            darkbg: '#0f172a',
            darkcard: '#1e293b',
            darkborder: '#334155'
          }
        }
      }
    }
  </script>
  <style>
    body { background-color: #0b0f19; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0b0f19; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #475569; }
  </style>
</head>
<body class="text-slate-100 min-h-screen flex flex-col">

  <!-- TOP HEADER -->
  <header class="bg-[#111827] border-b border-slate-800 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50">
    <div class="flex items-center space-x-3">
      <div class="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/30">
        <i class="fa-solid fa-shield-halved text-lg"></i>
      </div>
      <div>
        <h1 class="text-lg font-bold tracking-tight text-white flex items-center gap-2">
          Production AI Incident Assistant
          <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">LIVE</span>
        </h1>
        <p class="text-xs text-slate-400">Autonomous Telemetry Correlation & Evidence-Grounded Root-Cause Analysis</p>
      </div>
    </div>

    <!-- SIMULATOR CONTROL -->
    <div class="flex items-center gap-3 bg-slate-900/80 p-1.5 rounded-xl border border-slate-800">
      <span class="text-xs text-slate-400 font-medium pl-2 hidden sm:inline"><i class="fa-solid fa-bolt text-amber-400 mr-1.5"></i>Simulate Outage:</span>
      <select id="scenario-select" class="bg-slate-800 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 border border-slate-700 focus:outline-none focus:border-indigo-500">
        <option value="payment-db-pool-exhaustion">Payment: DB Pool Saturation (98%)</option>
        <option value="order-memory-leak">Order: Memory Leak & OOMKilled</option>
        <option value="checkout-gateway-timeout">Checkout: Downstream Gateway 504</option>
      </select>
      <button onclick="triggerSimulation()" id="simulate-btn" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-3.5 py-1.5 rounded-lg transition-all flex items-center gap-1.5 shadow-md shadow-indigo-600/30">
        <i class="fa-solid fa-play text-[10px]"></i> Trigger Outage
      </button>
    </div>

    <!-- SYSTEM STATUS -->
    <div class="flex items-center gap-3 text-xs">
      <a href="/docs" target="_blank" class="text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-1">
        <i class="fa-solid fa-book-open"></i> API Docs
      </a>
      <span class="h-4 w-px bg-slate-800"></span>
      <div class="flex items-center gap-1.5 text-emerald-400 bg-emerald-950/40 px-2.5 py-1 rounded-md border border-emerald-800/40">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span id="health-label">Engine Ready</span>
      </div>
    </div>
  </header>

  <!-- MAIN WORKSPACE -->
  <div class="flex-1 flex overflow-hidden">
    
    <!-- LEFT SIDEBAR: INCIDENT LIST -->
    <aside class="w-80 md:w-96 border-r border-slate-800 bg-[#0f172a] flex flex-col shrink-0">
      <div class="p-4 border-b border-slate-800 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <i class="fa-solid fa-fire text-rose-500"></i> Active Incidents
          <span id="incident-count-badge" class="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full font-mono">0</span>
        </h2>
        <button onclick="loadIncidents()" class="text-xs text-slate-400 hover:text-slate-200 transition-colors" title="Refresh">
          <i class="fa-solid fa-arrows-rotate"></i>
        </button>
      </div>

      <!-- FILTER TABS -->
      <div class="px-4 py-2 bg-slate-900/60 border-b border-slate-800 flex gap-2 overflow-x-auto text-xs">
        <button onclick="filterStatus('all')" class="status-filter active px-2.5 py-1 rounded-md bg-indigo-600/20 text-indigo-400 font-medium">All</button>
        <button onclick="filterStatus('triggered')" class="status-filter px-2.5 py-1 rounded-md text-slate-400 hover:bg-slate-800">Triggered</button>
        <button onclick="filterStatus('investigating')" class="status-filter px-2.5 py-1 rounded-md text-slate-400 hover:bg-slate-800">Investigating</button>
        <button onclick="filterStatus('identified')" class="status-filter px-2.5 py-1 rounded-md text-slate-400 hover:bg-slate-800">Identified</button>
        <button onclick="filterStatus('resolved')" class="status-filter px-2.5 py-1 rounded-md text-slate-400 hover:bg-slate-800">Resolved</button>
      </div>

      <!-- INCIDENTS SCROLL AREA -->
      <div id="incidents-list" class="flex-1 overflow-y-auto p-3 space-y-2.5">
        <div class="text-center py-12 text-slate-500 text-xs">Loading active incidents...</div>
      </div>
    </aside>

    <!-- RIGHT CONTENT: INCIDENT DETAILS & WORKSPACE -->
    <main class="flex-1 overflow-y-auto bg-[#0b0f19] p-6" id="incident-detail-container">
      <div class="h-full flex flex-col items-center justify-center text-center text-slate-500 py-20">
        <div class="w-16 h-16 rounded-2xl bg-slate-900 flex items-center justify-center text-slate-600 mb-4 border border-slate-800">
          <i class="fa-solid fa-magnifying-glass-chart text-2xl"></i>
        </div>
        <h3 class="text-base font-semibold text-slate-300">No Incident Selected</h3>
        <p class="text-xs text-slate-500 max-w-sm mt-1">Select an incident from the left sidebar or trigger a simulation above to begin AI root-cause analysis.</p>
      </div>
    </main>

  </div>

  <script>
    let currentIncidentId = null;
    let allIncidents = [];
    let activeFilter = 'all';

    async function checkHealth() {
      try {
        const res = await fetch('/api/v1/health');
        const data = await res.json();
        document.getElementById('health-label').innerText = data.database === 'healthy' ? 'Engine Ready' : 'Degraded';
      } catch (e) {
        document.getElementById('health-label').innerText = 'Offline';
      }
    }

    async function loadIncidents() {
      try {
        const res = await fetch('/api/v1/incidents?limit=50');
        allIncidents = await res.json();
        renderIncidentsList();
        if (allIncidents.length > 0 && !currentIncidentId) {
          selectIncident(allIncidents[0].id);
        } else if (currentIncidentId) {
          loadIncidentDetails(currentIncidentId);
        }
      } catch (err) {
        console.error("Failed to load incidents:", err);
      }
    }

    function filterStatus(status) {
      activeFilter = status;
      document.querySelectorAll('.status-filter').forEach(btn => {
        btn.classList.remove('bg-indigo-600/20', 'text-indigo-400');
        btn.classList.add('text-slate-400');
        if (btn.innerText.toLowerCase() === status) {
          btn.classList.add('bg-indigo-600/20', 'text-indigo-400');
          btn.classList.remove('text-slate-400');
        }
      });
      renderIncidentsList();
    }

    function renderIncidentsList() {
      const container = document.getElementById('incidents-list');
      const filtered = activeFilter === 'all' 
        ? allIncidents 
        : allIncidents.filter(i => i.status.toLowerCase() === activeFilter);

      document.getElementById('incident-count-badge').innerText = filtered.length;

      if (filtered.length === 0) {
        container.innerHTML = `
          <div class="text-center py-12 text-slate-500 text-xs">
            No incidents match "${activeFilter}".<br/>
            Click "Trigger Outage" above to create one.
          </div>
        `;
        return;
      }

      container.innerHTML = filtered.map(inc => {
        const isSelected = inc.id === currentIncidentId;
        const sevColor = inc.severity === 'critical' ? 'text-rose-400 bg-rose-500/10 border-rose-500/20' : 
                         inc.severity === 'high' ? 'text-amber-400 bg-amber-500/10 border-amber-500/20' : 
                         'text-blue-400 bg-blue-500/10 border-blue-500/20';
        
        const statusColor = inc.status === 'resolved' ? 'text-emerald-400 bg-emerald-500/10' :
                            inc.status === 'identified' ? 'text-cyan-400 bg-cyan-500/10' :
                            inc.status === 'investigating' ? 'text-indigo-400 bg-indigo-500/10' :
                            'text-amber-400 bg-amber-500/10';

        const timeStr = inc.created_at ? new Date(inc.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';

        return `
          <div onclick="selectIncident('${inc.id}')" class="p-3.5 rounded-xl border transition-all cursor-pointer ${isSelected ? 'bg-slate-800/90 border-indigo-500 shadow-md shadow-indigo-500/10' : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/50 hover:border-slate-700'}">
            <div class="flex items-center justify-between gap-2 mb-1.5">
              <span class="text-[11px] font-mono font-semibold px-2 py-0.5 rounded border ${sevColor}">
                ${inc.severity.toUpperCase()}
              </span>
              <span class="text-[11px] font-medium px-2 py-0.5 rounded ${statusColor}">
                ${inc.status.toUpperCase()}
              </span>
            </div>
            <h4 class="text-xs font-semibold text-slate-200 line-clamp-1 mb-1">${inc.title}</h4>
            <div class="flex items-center justify-between text-[11px] text-slate-500">
              <span class="font-mono bg-slate-800/80 px-1.5 py-0.5 rounded text-slate-400">${inc.service}</span>
              <span>${timeStr}</span>
            </div>
          </div>
        `;
      }).join('');
    }

    function selectIncident(id) {
      currentIncidentId = id;
      renderIncidentsList();
      loadIncidentDetails(id);
    }

    async function loadIncidentDetails(id) {
      const container = document.getElementById('incident-detail-container');
      try {
        const [incRes, reportRes, timelineRes, approvalsRes, eventsRes] = await Promise.all([
          fetch(`/api/v1/incidents/${id}`),
          fetch(`/api/v1/incidents/${id}/investigation`),
          fetch(`/api/v1/incidents/${id}/timeline`),
          fetch(`/api/v1/approvals?incident_id=${id}`),
          fetch(`/api/v1/incidents/${id}/events`)
        ]);

        const inc = await incRes.json();
        const report = reportRes.ok ? await reportRes.json() : null;
        const timeline = await timelineRes.json();
        const approvals = await approvalsRes.json();
        const events = await eventsRes.json();

        renderIncidentView(inc, report, timeline, approvals, events);
      } catch (err) {
        console.error("Failed to load incident detail:", err);
      }
    }

    function renderIncidentView(inc, report, timeline, approvals, events) {
      const container = document.getElementById('incident-detail-container');

      const sevBadge = inc.severity === 'critical' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 
                       inc.severity === 'high' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 
                       'bg-blue-500/10 text-blue-400 border-blue-500/20';

      const statusBadge = inc.status === 'resolved' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                          inc.status === 'identified' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' :
                          inc.status === 'investigating' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' :
                          'bg-amber-500/10 text-amber-400 border-amber-500/20';

      container.innerHTML = `
        <div class="max-w-6xl mx-auto space-y-6">

          <!-- HEADER CARD -->
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div class="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div class="flex items-center gap-2 mb-2 font-mono text-xs">
                  <span class="text-indigo-400 font-semibold">${inc.id}</span>
                  <span class="text-slate-600">•</span>
                  <span class="bg-slate-800 text-slate-300 px-2 py-0.5 rounded">${inc.service}</span>
                  <span class="text-slate-600">•</span>
                  <span class="px-2 py-0.5 rounded border ${sevBadge} font-semibold">${inc.severity.toUpperCase()}</span>
                  <span class="px-2 py-0.5 rounded border ${statusBadge} font-semibold">${inc.status.toUpperCase()}</span>
                </div>
                <h2 class="text-xl font-bold text-white">${inc.title}</h2>
                <p class="text-xs text-slate-400 mt-1.5 max-w-2xl">${inc.description}</p>
              </div>

              <!-- ACTION BUTTONS -->
              <div class="flex items-center gap-2">
                ${inc.status !== 'resolved' ? `
                  <button onclick="triggerInvestigation('${inc.id}')" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all shadow-lg shadow-indigo-600/30 flex items-center gap-2">
                    <i class="fa-solid fa-microchip"></i> Run AI Investigation
                  </button>
                  <button onclick="resolveIncident('${inc.id}')" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-3.5 py-2 rounded-xl transition-all shadow-md shadow-emerald-600/20 flex items-center gap-1.5">
                    <i class="fa-solid fa-check"></i> Mark Resolved
                  </button>
                ` : `
                  <div class="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-3 py-1.5 rounded-xl font-medium">
                    <i class="fa-solid fa-circle-check"></i> Incident Resolved
                  </div>
                `}
              </div>
            </div>
          </div>

          <!-- HUMAN APPROVALS BANNER (IF ANY PENDING) -->
          ${approvals && approvals.length > 0 ? `
            <div class="bg-gradient-to-r from-amber-950/40 via-slate-900 to-slate-900 border border-amber-600/40 rounded-2xl p-5 shadow-lg">
              <div class="flex items-center justify-between mb-3">
                <h3 class="text-sm font-bold text-amber-400 flex items-center gap-2">
                  <i class="fa-solid fa-user-shield"></i> Human Approval Gate (Production Remediation)
                </h3>
                <span class="text-xs bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full font-mono font-medium">
                  ${approvals.filter(a => a.status === 'pending').length} Actions Pending Sign-off
                </span>
              </div>
              <div class="space-y-3">
                ${approvals.map(appr => `
                  <div class="bg-slate-950/80 border border-slate-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div class="flex items-center gap-2 font-mono text-xs mb-1">
                        <span class="text-indigo-400 font-bold uppercase">${appr.action_type}</span>
                        <span class="text-slate-600">•</span>
                        <span class="text-[10px] uppercase font-semibold px-2 py-0.5 rounded ${appr.risk_level === 'high' ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/20 text-amber-400'}">Risk: ${appr.risk_level}</span>
                        <span class="text-slate-600">•</span>
                        <span class="text-[10px] px-2 py-0.5 rounded ${appr.status === 'executed' ? 'bg-emerald-500/20 text-emerald-400' : appr.status === 'rejected' ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/20 text-amber-400'} font-semibold uppercase">
                          ${appr.status}
                        </span>
                      </div>
                      <p class="text-xs text-slate-300 font-medium">${appr.description}</p>
                      ${appr.execution_result ? `
                        <div class="mt-2 text-[11px] font-mono text-emerald-400 bg-emerald-950/30 p-2 rounded border border-emerald-900/40">
                          <i class="fa-solid fa-terminal mr-1"></i> Result: ${appr.execution_result.message || JSON.stringify(appr.execution_result)}
                        </div>
                      ` : ''}
                    </div>
                    ${appr.status === 'pending' ? `
                      <div class="flex items-center gap-2">
                        <button onclick="handleApproval('${appr.id}', 'approve')" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-3.5 py-1.5 rounded-lg transition-all shadow-md shadow-emerald-600/30 flex items-center gap-1.5">
                          <i class="fa-solid fa-check"></i> Approve & Execute
                        </button>
                        <button onclick="handleApproval('${appr.id}', 'reject')" class="bg-rose-600/80 hover:bg-rose-600 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1">
                          <i class="fa-solid fa-xmark"></i> Reject
                        </button>
                      </div>
                    ` : ''}
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}

          <!-- AI INVESTIGATION REPORT CARD -->
          ${report ? `
            <div class="bg-slate-900/90 border border-indigo-900/50 rounded-2xl p-6 shadow-xl space-y-6">
              <div class="flex items-center justify-between border-b border-slate-800 pb-4">
                <div class="flex items-center gap-2.5">
                  <div class="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/40 text-indigo-400 flex items-center justify-center">
                    <i class="fa-solid fa-brain"></i>
                  </div>
                  <div>
                    <h3 class="text-sm font-bold text-white">AI Root-Cause Investigation Report</h3>
                    <p class="text-[11px] text-slate-400">Generated with tool-grounded multi-source reasoning</p>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-xs text-slate-400">Confidence:</span>
                  <div class="w-24 bg-slate-800 h-2.5 rounded-full overflow-hidden border border-slate-700">
                    <div class="bg-indigo-500 h-full rounded-full" style="width: ${Math.round(report.confidence_score * 100)}%"></div>
                  </div>
                  <span class="text-xs font-mono font-bold text-indigo-400">${Math.round(report.confidence_score * 100)}%</span>
                </div>
              </div>

              <!-- SUMMARY -->
              <div class="bg-slate-950/60 border border-slate-800 p-4 rounded-xl">
                <h4 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Executive Summary</h4>
                <p class="text-xs text-slate-200 leading-relaxed">${report.summary}</p>
              </div>

              <!-- ROOT CAUSE HYPOTHESES -->
              <div>
                <h4 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Evaluated Root-Cause Hypotheses</h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  ${report.hypotheses.map((hyp, i) => `
                    <div class="bg-slate-950/80 border ${i === 0 ? 'border-indigo-500/60 shadow-md shadow-indigo-500/5' : 'border-slate-800'} p-4 rounded-xl flex flex-col justify-between">
                      <div>
                        <div class="flex items-center justify-between gap-2 mb-2">
                          <span class="text-xs font-bold text-white flex items-center gap-1.5">
                            ${i === 0 ? '<i class="fa-solid fa-circle-check text-indigo-400"></i>' : ''}
                            ${hyp.title}
                          </span>
                          <span class="text-[10px] font-mono px-2 py-0.5 rounded font-bold ${hyp.likelihood === 'High' ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/20 text-amber-400'}">
                            ${hyp.likelihood.toUpperCase()} LIKELIHOOD
                          </span>
                        </div>
                        <p class="text-xs text-slate-400 mb-3">${hyp.rationale}</p>
                      </div>
                      <div>
                        <div class="flex items-center justify-between text-[11px] text-slate-500 font-mono pt-2 border-t border-slate-900">
                          <span>Confidence: ${(hyp.confidence_score * 100).toFixed(0)}%</span>
                          <span>Evidence: ${hyp.supporting_evidence_ids.length} linked sources</span>
                        </div>
                      </div>
                    </div>
                  `).join('')}
                </div>
              </div>

              <!-- SUPPORTING EVIDENCE PILLS -->
              <div>
                <h4 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Supporting Telemetry Evidence</h4>
                <div class="space-y-2">
                  ${report.supporting_evidence.map(ev => `
                    <div class="bg-slate-950/60 border border-slate-800/80 px-3.5 py-2.5 rounded-lg flex items-center justify-between gap-4 text-xs">
                      <div class="flex items-center gap-2.5 truncate">
                        <span class="font-mono text-[10px] px-1.5 py-0.5 rounded uppercase font-semibold ${ev.type === 'error' ? 'bg-rose-500/20 text-rose-400' : ev.type === 'deployment' ? 'bg-indigo-500/20 text-indigo-400' : 'bg-cyan-500/20 text-cyan-400'}">
                          ${ev.type}
                        </span>
                        <span class="text-slate-300 truncate">${ev.summary}</span>
                      </div>
                      <span class="font-mono text-[11px] text-slate-500 shrink-0">${ev.source}</span>
                    </div>
                  `).join('')}
                </div>
              </div>

              <!-- UNCERTAINTY FACTORS -->
              ${report.uncertainty_factors && report.uncertainty_factors.length > 0 ? `
                <div class="bg-amber-950/20 border border-amber-900/30 p-3.5 rounded-xl text-xs">
                  <h5 class="text-amber-400 font-semibold mb-1 flex items-center gap-1.5">
                    <i class="fa-solid fa-triangle-exclamation"></i> Uncertainty & Telemetry Gaps
                  </h5>
                  <ul class="list-disc list-inside text-slate-400 space-y-0.5 text-[11px]">
                    ${report.uncertainty_factors.map(u => `<li>${u}</li>`).join('')}
                  </ul>
                </div>
              ` : ''}

            </div>
          ` : `
            <div class="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center">
              <div class="w-12 h-12 rounded-xl bg-indigo-600/10 text-indigo-400 flex items-center justify-center mx-auto mb-3">
                <i class="fa-solid fa-wand-magic-sparkles text-lg"></i>
              </div>
              <h4 class="text-sm font-semibold text-slate-200">AI Investigation Not Yet Executed</h4>
              <p class="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">Click below to trigger the AI investigation agent, retrieve RAG runbooks, correlate telemetry, and generate evidence-grounded hypotheses.</p>
              <button onclick="triggerInvestigation('${inc.id}')" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all shadow-md shadow-indigo-600/30 inline-flex items-center gap-2">
                <i class="fa-solid fa-play text-[10px]"></i> Run Investigation Now
              </button>
            </div>
          `}

          <!-- TIMELINE -->
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h3 class="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <i class="fa-solid fa-timeline text-indigo-400"></i> Chronological Incident Timeline
            </h3>
            <div class="relative border-l-2 border-slate-800 ml-4 space-y-4 py-2">
              ${timeline.map(t => {
                const timeStr = t.timestamp ? new Date(t.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'}) : '';
                const nodeColor = t.event_type.includes('remediation') || t.event_type.includes('resolved') ? 'bg-emerald-500 text-white' :
                                  t.event_type.includes('approval') ? 'bg-amber-500 text-white' :
                                  t.event_type.includes('deployment') ? 'bg-indigo-500 text-white' :
                                  'bg-rose-500 text-white';

                return `
                  <div class="relative pl-6">
                    <div class="absolute -left-2.5 top-1 w-5 h-5 rounded-full ${nodeColor} flex items-center justify-center text-[9px] shadow-md">
                      <i class="fa-solid fa-circle"></i>
                    </div>
                    <div class="bg-slate-950/70 border border-slate-800/80 p-3 rounded-xl">
                      <div class="flex items-center justify-between text-xs mb-1">
                        <span class="font-semibold text-slate-200">${t.title}</span>
                        <span class="text-[11px] font-mono text-slate-500">${timeStr}</span>
                      </div>
                      <p class="text-xs text-slate-400">${t.description}</p>
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>

          <!-- RAW TELEMETRY EVENTS -->
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-sm font-bold text-white flex items-center gap-2">
                <i class="fa-solid fa-database text-cyan-400"></i> Correlated Telemetry & Errors (${events.length})
              </h3>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs">
                <thead>
                  <tr class="border-b border-slate-800 text-slate-400 font-mono text-[11px]">
                    <th class="py-2.5 px-3">Type</th>
                    <th class="py-2.5 px-3">Severity</th>
                    <th class="py-2.5 px-3">Message</th>
                    <th class="py-2.5 px-3">Anomaly</th>
                    <th class="py-2.5 px-3 text-right">Time</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-800/60 font-mono">
                  ${events.map(e => `
                    <tr class="hover:bg-slate-800/40 transition-colors">
                      <td class="py-2.5 px-3 uppercase text-indigo-400 font-semibold">${e.event_type}</td>
                      <td class="py-2.5 px-3 uppercase ${e.severity === 'critical' ? 'text-rose-400' : e.severity === 'high' ? 'text-amber-400' : 'text-slate-400'}">${e.severity}</td>
                      <td class="py-2.5 px-3 font-sans text-slate-200">${e.message}</td>
                      <td class="py-2.5 px-3">${e.is_anomaly ? '<span class="bg-rose-500/20 text-rose-400 px-1.5 py-0.5 rounded text-[10px]">ANOMALY</span>' : '<span class="text-slate-600">-</span>'}</td>
                      <td class="py-2.5 px-3 text-right text-slate-500 text-[11px]">${e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : ''}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      `;
    }

    async function triggerInvestigation(id) {
      try {
        const btn = event.currentTarget;
        const origText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Investigating...';
        btn.disabled = true;

        const res = await fetch(`/api/v1/incidents/${id}/investigate`, { method: 'POST' });
        await res.json();
        await loadIncidents();
        await loadIncidentDetails(id);
      } catch (err) {
        alert("Investigation error: " + err);
      }
    }

    async function handleApproval(approvalId, decision) {
      try {
        const res = await fetch(`/api/v1/approvals/${approvalId}/action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision, actor: 'on_call_engineer' })
        });
        await res.json();
        await loadIncidents();
        await loadIncidentDetails(currentIncidentId);
      } catch (err) {
        alert("Action error: " + err);
      }
    }

    async function resolveIncident(id) {
      try {
        await fetch(`/api/v1/incidents/${id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'resolved', resolution_notes: 'Resolved manually by engineer.' })
        });
        await loadIncidents();
        await loadIncidentDetails(id);
      } catch (err) {
        alert("Resolve error: " + err);
      }
    }

    async function triggerSimulation() {
      const select = document.getElementById('scenario-select');
      const btn = document.getElementById('simulate-btn');
      const scenario = select.value;

      try {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Simulating...';
        btn.disabled = true;

        const res = await fetch('/api/v1/simulator/trigger-scenario', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario, auto_investigate: true })
        });

        const data = await res.json();
        await loadIncidents();
        if (data.incident_id) {
          selectIncident(data.incident_id);
        }
      } catch (err) {
        alert("Simulation error: " + err);
      } finally {
        btn.innerHTML = '<i class="fa-solid fa-play text-[10px]"></i> Trigger Outage';
        btn.disabled = false;
      }
    }

    // Startup
    checkHealth();
    loadIncidents();
    setInterval(loadIncidents, 10000);
  </script>
</body>
</html>
"""

