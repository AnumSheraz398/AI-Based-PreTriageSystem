import { useState } from "react";

const INITIAL = [
    {
        id: "P-1001",
        name: "Ali Khan",
        urgency: 3,
        status: "Pending Review",
        department: "Emergency OPD",
        redFlags: ["fever", "dehydration"],
        waitMins: 18,
    },
    {
        id: "P-1002",
        name: "Ayesha Noor",
        urgency: 2,
        status: "Alerted",
        department: "A&E",
        redFlags: ["chest pain"],
        waitMins: 4,
    },
    {
        id: "P-1003",
        name: "Hamza Ahmed",
        urgency: 5,
        status: "Routed",
        department: "General OPD",
        redFlags: [],
        waitMins: 29,
    },
];

const urgencyLabel = {
    1: "Resuscitation",
    2: "Emergent",
    3: "Urgent",
    4: "Less Urgent",
    5: "Non-Urgent",
};

export default function App() {
    const [rows, setRows] = useState(INITIAL);

    const overrideUrgency = (id, newLevel) => {
        setRows((prev) =>
            prev.map((r) =>
                r.id === id
                    ? { ...r, urgency: Number(newLevel), status: "Overridden by nurse" }
                    : r
            )
        );
    };

    const markSeen = (id) => {
        setRows((prev) => prev.map((r) => (r.id === id ? { ...r, status: "Seen" } : r)));
    };

    const sortedRows = [...rows].sort((a, b) => a.urgency - b.urgency || a.waitMins - b.waitMins);
    const emergencyCount = sortedRows.filter((r) => r.urgency <= 2).length;

    const urgencyBadgeClass = (urgency) => {
        if (urgency === 1) return "bg-red-700 text-white";
        if (urgency === 2) return "bg-red-500 text-white";
        if (urgency === 3) return "bg-amber-400 text-slate-900";
        if (urgency === 4) return "bg-lime-400 text-slate-900";
        return "bg-sky-300 text-slate-900";
    };

    return (
        <main className="dashboard-shell min-h-screen p-4 md:p-8">
            <section className="dashboard-panel mx-auto max-w-7xl rounded-3xl p-5 md:p-8">
                <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                    <div>
                        <p className="dashboard-chip inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em]">
                            Clinical Monitoring
                        </p>
                        <h1 className="mt-3 text-3xl font-bold text-slate-900 md:text-4xl">Pre-Triage Staff Dashboard</h1>
                        <p className="mt-1 text-sm text-slate-700">
                            Live queue sorted by urgency level with nurse override and emergency visual alerts.
                        </p>
                    </div>
                    <div className="flex items-center gap-2 rounded-2xl bg-cyan-950/95 px-4 py-3 text-white shadow-lg">
                        <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-red-400" />
                        <span className="text-sm font-semibold">Level 1-2 Alerts: {emergencyCount}</span>
                    </div>
                </header>

                <div className="mt-6 overflow-x-auto rounded-2xl border border-cyan-100 bg-white">
                    <table className="w-full border-collapse text-left text-sm">
                        <thead>
                            <tr className="border-b bg-cyan-50 text-slate-700">
                                <th className="p-3">Patient ID</th>
                                <th className="p-3">Name</th>
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
                                    className={`border-b ${r.urgency <= 2 ? "animate-[flash_1.6s_ease-in-out_infinite] bg-red-50/70" : ""}`}
                                >
                                    <td className="p-3 font-medium text-slate-900">{r.id}</td>
                                    <td className="p-3">{r.name}</td>
                                    <td className="p-3">
                                        <span className={`rounded-full px-2 py-1 text-xs font-bold shadow-sm ${urgencyBadgeClass(r.urgency)}`}>
                                            L{r.urgency} - {urgencyLabel[r.urgency]}
                                        </span>
                                    </td>
                                    <td className="p-3">{r.department}</td>
                                    <td className="p-3">
                                        {r.redFlags.length ? (
                                            <span className="rounded-full bg-rose-100 px-2 py-1 text-xs font-semibold text-rose-700">
                                                {r.redFlags.join(", ")}
                                            </span>
                                        ) : (
                                            <span className="rounded-full bg-cyan-100 px-2 py-1 text-xs font-semibold text-cyan-700">None</span>
                                        )}
                                    </td>
                                    <td className="p-3">{r.waitMins}</td>
                                    <td className="p-3">
                                        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">{r.status}</span>
                                    </td>
                                    <td className="p-3">
                                        <select
                                            className="rounded-lg border border-cyan-200 bg-white p-1 shadow-sm"
                                            value={r.urgency}
                                            onChange={(event) => overrideUrgency(r.id, event.target.value)}
                                        >
                                            {[1, 2, 3, 4, 5].map((lvl) => (
                                                <option key={lvl} value={lvl}>
                                                    {lvl}
                                                </option>
                                            ))}
                                        </select>
                                    </td>
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
                </div>

                <p className="mt-4 rounded-xl border border-cyan-100 bg-cyan-50 p-3 text-xs text-cyan-900">
                    Audit log, explanation text, and protocol chunk visibility can be connected from backend log endpoints in the next phase.
                </p>
            </section>
        </main>
    );
}
