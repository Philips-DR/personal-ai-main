"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api-client";
import type { AuditEntry, AuditPage, Metrics, ModuleMetric } from "../../lib/types";

const ALL_MODULES = [
  "orchestrator", "email", "meeting", "tasks", "morning_brief",
  "drive", "learning_coach", "github_docs", "general_chat",
];

function fmt(ms: number | null) {
  if (!ms) return "—";
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

function fmtTokens(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

function relTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return new Date(iso).toLocaleDateString();
}

function ModuleBadge({ module }: { module: string }) {
  const colors: Record<string, string> = {
    email: "#3b82f6",
    meeting: "#a855f7",
    tasks: "#f59e0b",
    morning_brief: "#14b8a6",
    drive: "#22c55e",
    learning_coach: "#ec4899",
    github_docs: "#6366f1",
    general_chat: "#64748b",
    orchestrator: "#94a3b8",
  };
  const color = colors[module] ?? "#64748b";
  return (
    <span
      className="inline-block px-2 py-0.5 rounded text-xs font-medium"
      style={{
        background: `${color}20`,
        color,
        border: `1px solid ${color}40`,
      }}
    >
      {module}
    </span>
  );
}

function MetricsPanel({ metrics }: { metrics: Metrics }) {
  const errorRate = metrics.total_calls
    ? ((metrics.total_errors / metrics.total_calls) * 100).toFixed(1)
    : "0";

  return (
    <div className="space-y-4 mb-6">
      {/* Top stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Total calls", value: metrics.total_calls.toLocaleString() },
          { label: "Avg latency", value: fmt(metrics.avg_duration_ms) },
          {
            label: "Input tokens",
            value: fmtTokens(metrics.total_input_tokens),
          },
          {
            label: "Error rate",
            value: `${errorRate}%`,
            highlight: parseFloat(errorRate) > 5,
          },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl p-4"
            style={{
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>
              {stat.label}
            </p>
            <p
              className="text-xl font-semibold"
              style={{
                color: stat.highlight ? "#f87171" : "var(--text-primary)",
              }}
            >
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      {/* Per-module table */}
      {metrics.by_module.length > 0 && (
        <div
          className="rounded-xl overflow-hidden"
          style={{
            border: "1px solid var(--border-subtle)",
            background: "var(--bg-elevated)",
          }}
        >
          <table className="w-full text-xs">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                {["Module", "Calls", "Errors", "Avg latency", "Tokens in", "Tokens out"].map(
                  (h) => (
                    <th
                      key={h}
                      className="px-4 py-2.5 text-left font-semibold uppercase tracking-wider"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {metrics.by_module.map((m: ModuleMetric) => (
                <tr
                  key={m.module}
                  style={{ borderBottom: "1px solid var(--border-subtle)" }}
                >
                  <td className="px-4 py-2.5">
                    <ModuleBadge module={m.module} />
                  </td>
                  <td className="px-4 py-2.5" style={{ color: "var(--text-primary)" }}>
                    {m.total_calls}
                  </td>
                  <td
                    className="px-4 py-2.5"
                    style={{ color: m.error_calls > 0 ? "#f87171" : "var(--text-muted)" }}
                  >
                    {m.error_calls}
                  </td>
                  <td className="px-4 py-2.5" style={{ color: "var(--text-secondary)" }}>
                    {fmt(m.avg_duration_ms)}
                  </td>
                  <td className="px-4 py-2.5" style={{ color: "var(--text-secondary)" }}>
                    {fmtTokens(m.total_input_tokens)}
                  </td>
                  <td className="px-4 py-2.5" style={{ color: "var(--text-secondary)" }}>
                    {fmtTokens(m.total_output_tokens)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  const [expanded, setExpanded] = useState(false);
  const tokens = (entry.metadata?.tokens as Record<string, number> | undefined);
  const totalTokens = tokens
    ? (tokens.input_tokens ?? 0) + (tokens.output_tokens ?? 0)
    : null;

  return (
    <>
      <tr
        onClick={() => setExpanded((v) => !v)}
        className="cursor-pointer transition-colors"
        style={{ borderBottom: "1px solid var(--border-subtle)" }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.02)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLElement).style.background = "transparent";
        }}
      >
        <td className="px-4 py-3">
          <span style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>
            {relTime(entry.created_at)}
          </span>
        </td>
        <td className="px-4 py-3">
          <ModuleBadge module={entry.module} />
        </td>
        <td className="px-4 py-3">
          {entry.intent ? (
            <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
              {entry.intent}
            </span>
          ) : (
            <span style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>—</span>
          )}
        </td>
        <td className="px-4 py-3">
          <span
            className="text-xs truncate max-w-xs block"
            style={{ color: "var(--text-secondary)" }}
          >
            {entry.input_summary ?? "—"}
          </span>
        </td>
        <td className="px-4 py-3 text-right">
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {fmt(entry.duration_ms)}
          </span>
        </td>
        <td className="px-4 py-3 text-right">
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {totalTokens ? fmtTokens(totalTokens) : "—"}
          </span>
        </td>
        <td className="px-4 py-3 text-center">
          {entry.error ? (
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ background: "#f87171" }}
              title={entry.error}
            />
          ) : (
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ background: "#4ade80" }}
            />
          )}
        </td>
      </tr>
      {expanded && (
        <tr style={{ background: "rgba(0,0,0,0.2)" }}>
          <td colSpan={7} className="px-6 py-4">
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <p className="font-semibold mb-1" style={{ color: "var(--text-muted)" }}>
                  Input
                </p>
                <p style={{ color: "var(--text-secondary)" }}>
                  {entry.input_summary ?? "—"}
                </p>
              </div>
              <div>
                <p className="font-semibold mb-1" style={{ color: "var(--text-muted)" }}>
                  Output
                </p>
                <p style={{ color: "var(--text-secondary)" }}>
                  {entry.output_summary ?? "—"}
                </p>
              </div>
              {entry.error && (
                <div className="col-span-2">
                  <p className="font-semibold mb-1" style={{ color: "#f87171" }}>
                    Error
                  </p>
                  <p className="font-mono text-xs" style={{ color: "#f87171" }}>
                    {entry.error}
                  </p>
                </div>
              )}
              {tokens && (
                <div>
                  <p className="font-semibold mb-1" style={{ color: "var(--text-muted)" }}>
                    Tokens
                  </p>
                  <p style={{ color: "var(--text-secondary)" }}>
                    {tokens.input_tokens} in / {tokens.output_tokens} out
                    ({tokens.calls} call{tokens.calls !== 1 ? "s" : ""})
                  </p>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function AuditPage() {
  const [page, setPage] = useState<AuditPage | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [filterModule, setFilterModule] = useState("");
  const [filterErrors, setFilterErrors] = useState(false);
  const limit = 50;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [auditData, metricsData] = await Promise.all([
        api.admin.audit({
          module: filterModule || undefined,
          has_error: filterErrors || undefined,
          limit,
          offset,
        }),
        offset === 0 ? api.admin.metrics() : Promise.resolve(metrics),
      ]);
      setPage(auditData);
      if (metricsData) setMetrics(metricsData);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [filterModule, filterErrors, offset]);

  useEffect(() => { load(); }, [load]);

  function applyFilter() {
    setOffset(0);
    load();
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-deep)" }}>
      {/* Header */}
      <header
        className="sticky top-0 z-10 px-6 py-4 flex items-center gap-4"
        style={{
          borderBottom: "1px solid var(--border-subtle)",
          background: "rgba(10, 10, 15, 0.85)",
          backdropFilter: "blur(16px)",
        }}
      >
        <a
          href="/"
          className="flex items-center gap-1.5 text-xs font-medium"
          style={{ color: "var(--text-muted)" }}
          onMouseEnter={(e) => { e.currentTarget.style.color = "var(--accent)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-muted)"; }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15,18 9,12 15,6" />
          </svg>
          Back
        </a>
        <span style={{ color: "var(--border-subtle)" }}>|</span>
        <h1 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
          Audit Log
        </h1>
        <div className="flex-1" />
        <button
          onClick={load}
          className="px-3 py-1.5 rounded-lg text-xs transition-colors"
          style={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-subtle)",
            color: "var(--text-muted)",
          }}
        >
          Refresh
        </button>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6">
        {error && (
          <div
            className="mb-4 px-4 py-3 rounded-xl text-sm"
            style={{
              background: "rgba(239,68,68,0.1)",
              color: "#f87171",
              border: "1px solid rgba(239,68,68,0.2)",
            }}
          >
            {error}
          </div>
        )}

        {/* Metrics panel */}
        {metrics && <MetricsPanel metrics={metrics} />}

        {/* Filters */}
        <div
          className="flex gap-3 items-center mb-4 flex-wrap"
          style={{ padding: "12px 16px", background: "var(--bg-elevated)", borderRadius: "12px", border: "1px solid var(--border-subtle)" }}
        >
          <select
            value={filterModule}
            onChange={(e) => setFilterModule(e.target.value)}
            className="rounded-lg px-3 py-1.5 text-sm outline-none"
            style={{
              background: "var(--bg-deep)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-primary)",
            }}
          >
            <option value="">All modules</option>
            {ALL_MODULES.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>

          <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "var(--text-secondary)" }}>
            <input
              type="checkbox"
              checked={filterErrors}
              onChange={(e) => setFilterErrors(e.target.checked)}
              className="accent-teal-400"
            />
            Errors only
          </label>

          <button
            onClick={applyFilter}
            className="px-3 py-1.5 rounded-lg text-sm font-medium"
            style={{
              background: "var(--accent-dim)",
              color: "var(--accent)",
              border: "1px solid rgba(20,184,166,0.2)",
            }}
          >
            Apply
          </button>

          {page && (
            <span className="ml-auto text-xs" style={{ color: "var(--text-muted)" }}>
              {page.total.toLocaleString()} entries
            </span>
          )}
        </div>

        {/* Table */}
        <div
          className="rounded-xl overflow-hidden"
          style={{ border: "1px solid var(--border-subtle)", background: "var(--bg-elevated)" }}
        >
          {loading ? (
            <div className="flex items-center justify-center py-16" style={{ color: "var(--text-muted)" }}>
              Loading…
            </div>
          ) : page && page.items.length > 0 ? (
            <>
              <table className="w-full text-xs">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    {["Time", "Module", "Intent", "Input", "Latency", "Tokens", "Status"].map((h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left font-semibold uppercase tracking-wider"
                        style={{ color: "var(--text-muted)" }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {page.items.map((entry) => (
                    <AuditRow key={entry.id} entry={entry} />
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              <div
                className="flex items-center justify-between px-4 py-3"
                style={{ borderTop: "1px solid var(--border-subtle)" }}
              >
                <button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="px-3 py-1.5 rounded-lg text-xs disabled:opacity-40"
                  style={{
                    background: "var(--bg-deep)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-secondary)",
                  }}
                >
                  ← Previous
                </button>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {offset + 1}–{Math.min(offset + limit, page.total)} of {page.total}
                </span>
                <button
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= page.total}
                  className="px-3 py-1.5 rounded-lg text-xs disabled:opacity-40"
                  style={{
                    background: "var(--bg-deep)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-secondary)",
                  }}
                >
                  Next →
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center py-16 flex-col gap-2">
              <p style={{ color: "var(--text-muted)" }}>No audit entries yet.</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                Entries appear here after the first chat request.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
