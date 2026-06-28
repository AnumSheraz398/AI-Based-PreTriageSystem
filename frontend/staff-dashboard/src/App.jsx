import { useState, useEffect, useRef, useCallback } from "react";
import DisclaimerBanner from "./components/DisclaimerBanner";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const WS_BASE  = API_BASE.replace("http://", "ws://").replace("https://", "wss://");

const urgencyLabel = {
    1: "Resuscitation",
    2: "Emergent",
    3: "Urgent",
    4: "Less Urgent",
    5: "Non-Urgent",
};

const urgencyBadgeClass = (urgency) => {
    if (urgency === 1) return "bg-red-700 text-white";
    if (urgency === 2) return "bg-red-500 text-white";
    if (urgency === 3) return "bg-amber-400 text-slate-900";
    if (urgency === 4) return "bg-lime-400 text-slate-900";
    return "bg-sky-300 text-slate-900";
};

// ── Map backend patient shape → dashboard row shape ───────────────────────────
function mapPatient(p) {
    return {
        id:         p.id,
        token:      p.token_number    || p.id,
        complaint:  p.chief_complaint || "—",
        urgency:    p.triage_level    || 3,
        status:     mapStatus(p.status),
        department: p.department_name || p.department_code || "—",
        redFlags:   Array.isArray(p.red_flag_symptoms) ? p.red_flag_symptoms : [],
        waitMins:   p.waiting_since_mins ?? p.wait_mins ?? 0,
        confidence: p.confidence,
        requiresReview: p.requires_review,
        escalateNow:    p.escalate_now,
        safetyRule:     p.safety_rule_name,
    };
}

function mapStatus(backendStatus) {
    const map = {
        pending:    "Pending Review",
        confirmed:  "Confirmed",
        overridden: "Overridden",
        seen:       "Seen",
        escalated:  "Escalated",
    };
    return map[backendStatus] || backendStatus || "Pending Review";
}

export default function App() {
    const [rows, setRows]           = useState([]);
    const [loading, setLoading]     = useState(true);
    const [error, setError]         = useState("");
    const [wsStatus, setWsStatus]   = useState("connecting");  // connecting | live | reconnecting
    const [lastUpdate, setLastUpdate] = useState(null);
    const [overrideReasons, setOverrideReasons] = useState({});  // session_id -> reason text
    const wsRef = useRef(null);
    const reconnectTimer = useRef(null);

    // ── Fetch full queue from backend ─────────────────────────────────────────
    const fetchQueue = useCallback(async () => {
        try {
            const res  = await fetch(`${API_BASE}/dashboard/queue`);
            const data = await res.json();
            if (!res.ok) throw new Error(data?.detail || "Failed to fetch queue");
            setRows((data.patients || []).map(mapPatient));
            setLastUpdate(new Date());
            setError("");
        } catch (err) {
            setError(err.message || "Cannot reach backend");
        } finally {
            setLoading(false);
        }
    }, []);

    // ── WebSocket connection ──────────────────────────────────────────────────
    const connectWebSocket = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const ws = new WebSocket(`${WS_BASE}/dashboard/ws`);
        wsRef.current = ws;

        ws.onopen = () => {
            setWsStatus("live");
            setError("");
            // Ping every 25 seconds to keep connection alive
            const ping = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: "ping" }));
                } else {
                    clearInterval(ping);
                }
            }, 25000);
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                setLastUpdate(new Date());

                if (msg.type === "queue_refresh") {
                    // Full queue refresh — replace all rows
                    setRows((msg.data || []).map(mapPatient));

                } else if (msg.type === "new_patient") {
                    // Add new patient to queue
                    const newRow = mapPatient(msg.data);
                    setRows((prev) => {
                        const exists = prev.find((r) => r.id === newRow.id);
                        if (exists) return prev;
                        return [...prev, newRow];
                    });

                } else if (msg.type === "patient_update") {
                    // Update existing patient (override, seen, etc.)
                    const updated = mapPatient(msg.data);
                    setRows((prev) =>
                        updated.status === "Seen"
                            ? prev.filter((r) => r.id !== updated.id)   // remove seen patients
                            : prev.map((r) => r.id === updated.id ? updated : r)
                    );

                } else if (msg.type === "level1_alert") {
                    // Level 1 emergency — play alert sound
                    playAlertSound();
                }
            } catch (e) {
                console.error("WebSocket message parse error:", e);
            }
        };

        ws.onclose = () => {
            setWsStatus("reconnecting");
            // Reconnect after 3 seconds
            reconnectTimer.current = setTimeout(() => {
                connectWebSocket();
            }, 3000);
        };

        ws.onerror = () => {
            setWsStatus("reconnecting");
            ws.close();
        };
    }, []);

    // ── Alert sound for Level 1 ───────────────────────────────────────────────
    const playAlertSound = () => {
        try {
            const ctx  = new (window.AudioContext || window.webkitAudioContext)();
            const osc  = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.setValueAtTime(880, ctx.currentTime);
            osc.frequency.setValueAtTime(440, ctx.currentTime + 0.3);
            osc.frequency.setValueAtTime(880, ctx.currentTime + 0.6);
            gain.gain.setValueAtTime(0.4, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.2);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 1.2);
        } catch (e) { /* silent fail */ }
    };

    // ── On mount: fetch queue + connect WebSocket ─────────────────────────────
    useEffect(() => {
        fetchQueue();
        connectWebSocket();
        return () => {
            wsRef.current?.close();
            clearTimeout(reconnectTimer.current);
        };
    }, [fetchQueue, connectWebSocket]);

    // ── Fallback polling every 15s if WebSocket is down ──────────────────────
    useEffect(() => {
        if (wsStatus !== "live") {
            const poll = setInterval(fetchQueue, 15000);
            return () => clearInterval(poll);
        }
    }, [wsStatus, fetchQueue]);

    // ── Override urgency (calls backend) ─────────────────────────────────────
    const overrideUrgency = async (id, newLevel) => {
        const reason = overrideReasons[id] || "Nurse assessment";
        try {
            const res = await fetch(`${API_BASE}/dashboard/override`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: id,
                    new_level:  Number(newLevel),
                    reason,
                    nurse_id:   "nurse",
                }),
            });
            if (!res.ok) throw new Error("Override failed");

            // Optimistic UI update (WebSocket will also broadcast this)
            setRows((prev) =>
                prev.map((r) =>
                    r.id === id
                        ? { ...r, urgency: Number(newLevel), status: "Overridden" }
                        : r
                )
            );
        } catch (err) {
            alert(`Override failed: ${err.message}`);
        }
    };

    // ── Mark seen (calls backend) ─────────────────────────────────────────────
    const markSeen = async (id) => {
        try {
            const res = await fetch(
                `${API_BASE}/dashboard/seen/${id}?nurse_id=nurse`,
                { method: "POST" }
            );
            if (!res.ok) throw new Error("Mark seen failed");

            // Optimistic: remove from queue (WebSocket will confirm)
            setRows((prev) => prev.filter((r) => r.id !== id));
        } catch (err) {
            alert(`Mark seen failed: ${err.message}`);
        }
    };

    // ── Sort by urgency then wait time ────────────────────────────────────────
    const sortedRows = [...rows].sort(
        (a, b) => a.urgency - b.urgency || b.waitMins - a.waitMins
    );
    const emergencyCount = sortedRows.filter((r) => r.urgency <= 2).length;

    // ── Render ─────────────────────────────────────────────────────────────────
    return (
         <>
    <DisclaimerBanner language="en" />
        <main className="dashboard-shell min-h-screen p-4 md:p-8">
            <section className="dashboard-panel mx-auto max-w-7xl rounded-3xl p-5 md:p-8">

                {/* Header */}
                <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                    <div>
                        <p className="dashboard-chip inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em]">
                            Clinical Monitoring
                        </p>
                        <h1 className="mt-3 text-3xl font-bold text-slate-900 md:text-4xl">
                            Pre-Triage Staff Dashboard
                        </h1>
                        <p className="mt-1 text-sm text-slate-700">
                            Live queue sorted by urgency level with nurse override and emergency visual alerts.
                        </p>
                    </div>

                    <div className="flex flex-col items-end gap-2">
                        {/* Level 1-2 alert counter */}
                        <div className="flex items-center gap-2 rounded-2xl bg-cyan-950/95 px-4 py-3 text-white shadow-lg">
                            <span className={`inline-block h-3 w-3 rounded-full ${emergencyCount > 0 ? "animate-pulse bg-red-400" : "bg-green-400"}`} />
                            <span className="text-sm font-semibold">Level 1-2 Alerts: {emergencyCount}</span>
                        </div>

                        {/* WebSocket status */}
                        <div className="flex items-center gap-1.5 text-xs text-slate-500">
                            <span className={`inline-block h-2 w-2 rounded-full ${
                                wsStatus === "live"         ? "bg-green-500" :
                                wsStatus === "reconnecting" ? "bg-amber-400 animate-pulse" :
                                                             "bg-slate-400 animate-pulse"
                            }`} />
                            {wsStatus === "live"         ? "Live" :
                             wsStatus === "reconnecting" ? "Reconnecting..." :
                                                          "Connecting..."}
                            {lastUpdate && (
                                <span className="ml-1">
                                    · Updated {lastUpdate.toLocaleTimeString()}
                                </span>
                            )}
                        </div>
                    </div>
                </header>

                {/* Error banner */}
                {error && (
                    <div className="mt-4 flex items-center justify-between rounded-xl bg-red-50 border border-red-200 px-4 py-3">
                        <span className="text-sm text-red-700">⚠ {error}</span>
                        <button
                            onClick={fetchQueue}
                            className="ml-4 rounded-lg bg-red-100 px-3 py-1 text-xs font-semibold text-red-800 hover:bg-red-200"
                        >
                            Retry
                        </button>
                    </div>
                )}

                {/* Queue table */}
                <div className="mt-6 overflow-x-auto rounded-2xl border border-cyan-100 bg-white">
                    {loading ? (
                        <div className="flex items-center justify-center py-16 text-slate-500">
                            <svg className="mr-2 h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                            </svg>
                            Loading patient queue...
                        </div>
                    ) : sortedRows.length === 0 ? (
                        <div className="py-16 text-center text-slate-400">
                            <p className="text-lg">No patients in queue</p>
                            <p className="mt-1 text-sm">New patients will appear here automatically</p>
                        </div>
                    ) : (
                        <table className="w-full border-collapse text-left text-sm">
                            <thead>
                                <tr className="border-b bg-cyan-50 text-slate-700">
                                    <th className="p-3">Token</th>
                                    <th className="p-3">Complaint</th>
                                    <th className="p-3">Urgency</th>
                                    <th className="p-3">Department</th>
                                    <th className="p-3">Red Flags</th>
                                    <th className="p-3">Wait (mins)</th>
                                    <th className="p-3">Status</th>
                                    <th className="p-3">Override</th>
                                    <th className="p-3">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {sortedRows.map((r) => (
                                    <tr
                                        key={r.id}
                                        className={`border-b transition-colors ${
                                            r.urgency === 1
                                                ? "bg-red-50 animate-pulse"
                                                : r.urgency === 2
                                                ? "bg-red-50/50"
                                                : ""
                                        }`}
                                    >
                                        {/* Token */}
                                        <td className="p-3 font-mono font-semibold text-slate-900">
                                            {r.token}
                                            {r.requiresReview && (
                                                <span className="ml-1 text-amber-500" title="Low confidence — review needed">⚠</span>
                                            )}
                                        </td>

                                        {/* Complaint */}
                                        <td className="p-3 max-w-[200px]">
                                            <span className="block truncate text-slate-700" title={r.complaint}>
                                                {r.complaint}
                                            </span>
                                            {r.safetyRule && (
                                                <span className="mt-0.5 block text-xs text-red-600">
                                                    Rule: {r.safetyRule}
                                                </span>
                                            )}
                                        </td>

                                        {/* Urgency badge */}
                                        <td className="p-3">
                                            <span className={`rounded-full px-2 py-1 text-xs font-bold shadow-sm ${urgencyBadgeClass(r.urgency)}`}>
                                                L{r.urgency} — {urgencyLabel[r.urgency]}
                                            </span>
                                            {r.confidence !== undefined && (
                                                <span className="mt-1 block text-xs text-slate-400">
                                                    {r.confidence}% confidence
                                                </span>
                                            )}
                                        </td>

                                        {/* Department */}
                                        <td className="p-3 text-slate-700">{r.department}</td>

                                        {/* Red flags */}
                                        <td className="p-3">
                                            {r.redFlags.length ? (
                                                <span className="rounded-full bg-rose-100 px-2 py-1 text-xs font-semibold text-rose-700">
                                                    {r.redFlags.join(", ")}
                                                </span>
                                            ) : (
                                                <span className="rounded-full bg-cyan-100 px-2 py-1 text-xs font-semibold text-cyan-700">
                                                    None
                                                </span>
                                            )}
                                        </td>

                                        {/* Wait time */}
                                        <td className="p-3 text-slate-700">{r.waitMins}</td>

                                        {/* Status */}
                                        <td className="p-3">
                                            <span className={`rounded-full px-2 py-1 text-xs font-semibold ${
                                                r.status === "Overridden"
                                                    ? "bg-purple-100 text-purple-700"
                                                    : r.status === "Confirmed"
                                                    ? "bg-green-100 text-green-700"
                                                    : "bg-slate-100 text-slate-700"
                                            }`}>
                                                {r.status}
                                            </span>
                                        </td>

                                        {/* Override */}
                                        <td className="p-3">
                                            <div className="flex flex-col gap-1">
                                                <select
                                                    className="rounded-lg border border-cyan-200 bg-white p-1 text-xs shadow-sm"
                                                    value={r.urgency}
                                                    onChange={(e) => overrideUrgency(r.id, e.target.value)}
                                                >
                                                    {[1, 2, 3, 4, 5].map((lvl) => (
                                                        <option key={lvl} value={lvl}>{lvl}</option>
                                                    ))}
                                                </select>
                                                <input
                                                    type="text"
                                                    placeholder="Reason..."
                                                    className="rounded-lg border border-cyan-200 px-1.5 py-0.5 text-xs w-full"
                                                    value={overrideReasons[r.id] || ""}
                                                    onChange={(e) =>
                                                        setOverrideReasons((prev) => ({
                                                            ...prev,
                                                            [r.id]: e.target.value,
                                                        }))
                                                    }
                                                />
                                            </div>
                                        </td>

                                        {/* Actions */}
                                        <td className="p-3">
                                            <button
                                                type="button"
                                                onClick={() => markSeen(r.id)}
                                                className="rounded-lg bg-gradient-to-r from-cyan-700 to-teal-700 px-2 py-1 text-xs font-semibold text-white shadow-sm hover:from-cyan-800 hover:to-teal-800"
                                            >
                                                Mark Seen
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Footer */}
                <div className="mt-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <p className="rounded-xl border border-cyan-100 bg-cyan-50 p-3 text-xs text-cyan-900">
                        {sortedRows.length} patient{sortedRows.length !== 1 ? "s" : ""} in queue.
                        Override changes are saved to audit log automatically.
                    </p>
                    <a
                        href={`${API_BASE}/dashboard/audit/export`}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-xl border border-cyan-200 bg-white px-4 py-2 text-xs font-semibold text-cyan-800 hover:bg-cyan-50 text-center"
                    >
                        ↓ Export Audit Log CSV
                    </a>
                </div>
            </section>
        </main>
         </>
    );
}