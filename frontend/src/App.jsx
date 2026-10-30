import React, { useState, useEffect } from 'react';

export default function App() {
  const [incidents, setIncidents] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [report, setReport] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchIncidents = async () => {
    try {
      const res = await fetch('/api/v1/incidents');
      const data = await res.json();
      setIncidents(data);
      if (data.length > 0 && !selectedId) {
        setSelectedId(data[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchDetail = async (id) => {
    if (!id) return;
    try {
      const [incRes, repRes, timeRes, apprRes] = await Promise.all([
        fetch(`/api/v1/incidents/${id}`),
        fetch(`/api/v1/incidents/${id}/investigation`),
        fetch(`/api/v1/incidents/${id}/timeline`),
        fetch(`/api/v1/approvals?incident_id=${id}`)
      ]);
      setDetail(await incRes.json());
      setReport(repRes.ok ? await repRes.json() : null);
      setTimeline(await timeRes.json());
      setApprovals(await apprRes.json());
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedId) {
      fetchDetail(selectedId);
    }
  }, [selectedId]);

  const handleSimulate = async (scenario) => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/simulator/trigger-scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario, auto_investigate: true })
      });
      const data = await res.json();
      await fetchIncidents();
      if (data.incident_id) setSelectedId(data.incident_id);
    } catch (e) {
      alert(e);
    } finally {
      setLoading(false);
    }
  };

  const handleApproval = async (approvalId, decision) => {
    try {
      await fetch(`/api/v1/approvals/${approvalId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, actor: 'sre_lead' })
      });
      await fetchIncidents();
      await fetchDetail(selectedId);
    } catch (e) {
      alert(e);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      {/* Top Header */}
      <header className="bg-slate-900 border-b border-slate-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold">
            AI
          </div>
          <span className="font-bold text-base">Production Incident & Root-Cause Assistant</span>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => handleSimulate('payment-db-pool-exhaustion')}
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold px-3.5 py-1.5 rounded-lg transition-all"
          >
            {loading ? 'Simulating...' : 'Simulate Outage: DB Pool (98%)'}
          </button>
        </div>
      </header>

      {/* Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-80 border-r border-slate-800 bg-slate-900/50 p-4 overflow-y-auto space-y-2">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            Incidents ({incidents.length})
          </h2>
          {incidents.map((inc) => (
            <div
              key={inc.id}
              onClick={() => setSelectedId(inc.id)}
              className={`p-3 rounded-xl border cursor-pointer transition-all ${
                selectedId === inc.id
                  ? 'bg-slate-800 border-indigo-500'
                  : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex justify-between items-center text-xs mb-1">
                <span className="font-mono text-indigo-400">{inc.id}</span>
                <span className="text-[10px] uppercase font-bold text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded">
                  {inc.severity}
                </span>
              </div>
              <p className="text-xs font-semibold text-slate-200 line-clamp-1">{inc.title}</p>
              <p className="text-[10px] text-slate-500 font-mono mt-1">{inc.service} • {inc.status}</p>
            </div>
          ))}
        </aside>

        {/* Content */}
        <main className="flex-1 p-6 overflow-y-auto space-y-6">
          {detail ? (
            <>
              {/* Incident Header */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-xs font-mono text-indigo-400">{detail.id} • {detail.service}</span>
                    <h2 className="text-xl font-bold mt-1 text-white">{detail.title}</h2>
                    <p className="text-xs text-slate-400 mt-1">{detail.description}</p>
                  </div>
                  <span className="px-2.5 py-1 text-xs rounded-full bg-indigo-500/10 text-indigo-400 font-semibold border border-indigo-500/20">
                    {detail.status.toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Approvals */}
              {approvals.length > 0 && (
                <div className="bg-amber-950/20 border border-amber-600/40 rounded-xl p-4 space-y-3">
                  <h3 className="text-xs font-bold text-amber-400 uppercase tracking-wide">
                    Human Approval Required (Remediation)
                  </h3>
                  {approvals.map((appr) => (
                    <div key={appr.id} className="bg-slate-900 border border-slate-800 p-3 rounded-lg flex justify-between items-center">
                      <div>
                        <span className="text-xs font-mono font-bold uppercase text-indigo-400">{appr.action_type}</span>
                        <p className="text-xs text-slate-300 mt-0.5">{appr.description}</p>
                      </div>
                      {appr.status === 'pending' ? (
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handleApproval(appr.id, 'approve')}
                            className="bg-emerald-600 hover:bg-emerald-500 text-xs px-3 py-1 rounded-md font-semibold"
                          >
                            Approve
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-emerald-400 font-mono font-bold uppercase">{appr.status}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* AI Report */}
              {report && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                    <h3 className="text-sm font-bold text-white">AI Root-Cause Investigation Report</h3>
                    <span className="text-xs font-mono text-indigo-400 font-bold">
                      Confidence: {Math.round(report.confidence_score * 100)}%
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-lg">{report.summary}</p>
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-slate-400 uppercase">Hypotheses</h4>
                    {report.hypotheses.map((h, i) => (
                      <div key={i} className="bg-slate-950/80 border border-slate-800 p-3 rounded-lg">
                        <div className="flex justify-between text-xs font-bold text-white mb-1">
                          <span>{h.title}</span>
                          <span className="text-rose-400">{h.likelihood} Likelihood</span>
                        </div>
                        <p className="text-xs text-slate-400">{h.rationale}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-20 text-slate-500 text-xs">Select an incident to view details</div>
          )}
        </main>
      </div>
    </div>
  );
}

