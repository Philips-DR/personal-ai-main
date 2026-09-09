"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api-client";
import type { UserPreferences } from "../lib/types";

const TIMEZONES = [
  "Africa/Lagos", "UTC", "America/New_York", "America/Chicago",
  "America/Denver", "America/Los_Angeles", "Europe/London",
  "Europe/Paris", "Asia/Dubai", "Asia/Kolkata", "Asia/Singapore",
  "Australia/Sydney",
];

const TONES = [
  { value: "warm", label: "Warm & friendly" },
  { value: "professional", label: "Professional" },
  { value: "concise", label: "Short & punchy" },
];

const TRANSCRIPTION_PROVIDERS = [
  { value: "assemblyai", label: "AssemblyAI (cloud)" },
  { value: "whisper", label: "Whisper (local, Phase 3)" },
];

function TagInput({
  label, values, onChange,
}: { label: string; values: string[]; onChange: (v: string[]) => void }) {
  const [draft, setDraft] = useState("");
  return (
    <div>
      <label className="block text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>
        {label}
      </label>
      <div className="flex flex-wrap gap-2 mb-2">
        {values.map((tag) => (
          <span
            key={tag}
            className="flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs"
            style={{
              background: "var(--accent-dim)",
              color: "var(--accent)",
              border: "1px solid rgba(20, 184, 166, 0.2)",
            }}
          >
            {tag}
            <button
              onClick={() => onChange(values.filter((v) => v !== tag))}
              className="ml-1 opacity-60 hover:opacity-100"
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <input
        type="text"
        value={draft}
        placeholder="Add topic and press Enter"
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && draft.trim()) {
            onChange([...values, draft.trim()]);
            setDraft("");
          }
        }}
        className="w-full rounded-lg px-3 py-2 text-sm outline-none"
        style={{
          background: "var(--bg-deep)",
          border: "1px solid var(--border-subtle)",
          color: "var(--text-primary)",
        }}
      />
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className="relative inline-flex h-5 w-9 flex-shrink-0 rounded-full transition-colors duration-200"
      style={{
        background: checked ? "var(--accent)" : "var(--bg-deep)",
        border: "1px solid",
        borderColor: checked ? "var(--accent)" : "var(--border-subtle)",
      }}
    >
      <span
        className="inline-block h-3.5 w-3.5 rounded-full transition-transform duration-200"
        style={{
          background: "#fff",
          transform: checked ? "translateX(18px)" : "translateX(2px)",
          marginTop: "2px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
        }}
      />
    </button>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      className="rounded-2xl p-6 mb-4"
      style={{
        background: "var(--bg-elevated)",
        border: "1px solid var(--border-subtle)",
      }}
    >
      <h2
        className="text-sm font-semibold uppercase tracking-widest mb-5"
        style={{ color: "var(--text-muted)", letterSpacing: "0.1em" }}
      >
        {title}
      </h2>
      <div className="space-y-5">{children}</div>
    </div>
  );
}

function Field({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-6">
      <div className="flex-1">
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{label}</p>
        {description && (
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{description}</p>
        )}
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.preferences.get()
      .then(setPrefs)
      .catch((e) => setError(String(e)));
  }, []);

  async function save() {
    if (!prefs) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.preferences.update(prefs);
      setPrefs(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  function update<K extends keyof UserPreferences>(key: K, value: UserPreferences[K]) {
    setPrefs((p) => p ? { ...p, [key]: value } : p);
  }

  if (!prefs && !error) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: "var(--bg-deep)", color: "var(--text-muted)" }}
      >
        Loading preferences…
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-deep)" }}>
      {/* Header */}
      <header
        className="sticky top-0 z-10 px-6 py-4 flex items-center justify-between"
        style={{
          borderBottom: "1px solid var(--border-subtle)",
          background: "rgba(10, 10, 15, 0.85)",
          backdropFilter: "blur(16px)",
        }}
      >
        <div className="flex items-center gap-3">
          <a
            href="/"
            className="flex items-center gap-1.5 text-xs font-medium transition-colors"
            style={{ color: "var(--text-muted)" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "var(--accent)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-muted)"; }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15,18 9,12 15,6" />
            </svg>
            Back to chat
          </a>
          <span style={{ color: "var(--border-subtle)" }}>|</span>
          <h1 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
            Settings
          </h1>
        </div>
        <button
          onClick={save}
          disabled={saving || !prefs}
          className="px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200"
          style={
            saving
              ? { background: "var(--bg-elevated)", color: "var(--text-muted)", border: "1px solid var(--border-subtle)" }
              : saved
              ? { background: "rgba(34,197,94,0.15)", color: "#4ade80", border: "1px solid rgba(34,197,94,0.3)" }
              : {
                  background: "linear-gradient(135deg, var(--accent), #0d9488)",
                  color: "#fff",
                  border: "none",
                  boxShadow: "0 0 16px var(--accent-glow)",
                }
          }
        >
          {saving ? "Saving…" : saved ? "Saved!" : "Save changes"}
        </button>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-8">
        {error && (
          <div
            className="mb-4 px-4 py-3 rounded-xl text-sm"
            style={{ background: "rgba(239,68,68,0.1)", color: "#f87171", border: "1px solid rgba(239,68,68,0.2)" }}
          >
            {error}
          </div>
        )}

        {prefs && (
          <>
            {/* Morning Brief */}
            <Section title="Morning Brief">
              <div>
                <label className="block text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>
                  Cron schedule
                </label>
                <input
                  type="text"
                  value={prefs.brief_cron}
                  onChange={(e) => update("brief_cron", e.target.value)}
                  placeholder="0 7 * * *"
                  className="w-full rounded-lg px-3 py-2 text-sm font-mono outline-none"
                  style={{
                    background: "var(--bg-deep)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-primary)",
                  }}
                />
                <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                  Standard 5-field cron. Default: 7:00 AM daily.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>
                  Timezone
                </label>
                <select
                  value={prefs.brief_timezone}
                  onChange={(e) => update("brief_timezone", e.target.value)}
                  className="w-full rounded-lg px-3 py-2 text-sm outline-none"
                  style={{
                    background: "var(--bg-deep)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-primary)",
                  }}
                >
                  {TIMEZONES.map((tz) => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>
                  Tone
                </label>
                <div className="flex gap-2">
                  {TONES.map((t) => (
                    <button
                      key={t.value}
                      onClick={() => update("brief_tone", t.value)}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150"
                      style={{
                        background: prefs.brief_tone === t.value ? "var(--accent-dim)" : "var(--bg-deep)",
                        color: prefs.brief_tone === t.value ? "var(--accent)" : "var(--text-muted)",
                        border: "1px solid",
                        borderColor: prefs.brief_tone === t.value ? "rgba(20,184,166,0.3)" : "var(--border-subtle)",
                      }}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              <Field label="Learning nudge" description="Include a study suggestion based on your roadmaps">
                <Toggle
                  checked={prefs.brief_include_learning}
                  onChange={(v) => update("brief_include_learning", v)}
                />
              </Field>

              <Field label="Life nudge" description="Include a personal wellbeing or life suggestion">
                <Toggle
                  checked={prefs.brief_include_life}
                  onChange={(v) => update("brief_include_life", v)}
                />
              </Field>
            </Section>

            {/* Learning */}
            <Section title="Learning & Growth">
              <TagInput
                label="Focus areas"
                values={prefs.learning_focus_areas}
                onChange={(v) => update("learning_focus_areas", v)}
              />
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                e.g. Rust, MLOps, Distributed Systems — used to personalise coaching suggestions.
              </p>
            </Section>

            {/* Life */}
            <Section title="Life Outside Work">
              <TagInput
                label="Interests & goals"
                values={prefs.life_focus_areas}
                onChange={(v) => update("life_focus_areas", v)}
              />
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                e.g. Running, reading sci-fi, cooking — informs life nudges in the brief.
              </p>
            </Section>

            {/* Integrations */}
            <Section title="Integrations">
              <Field label="Google Drive" description="Enable Drive, Docs & Sheets read/write">
                <Toggle
                  checked={prefs.drive_enabled}
                  onChange={(v) => update("drive_enabled", v)}
                />
              </Field>

              <div>
                <label className="block text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>
                  Transcription provider
                </label>
                <div className="flex gap-2">
                  {TRANSCRIPTION_PROVIDERS.map((p) => (
                    <button
                      key={p.value}
                      onClick={() => update("transcription_provider", p.value)}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150"
                      style={{
                        background: prefs.transcription_provider === p.value ? "var(--accent-dim)" : "var(--bg-deep)",
                        color: prefs.transcription_provider === p.value ? "var(--accent)" : "var(--text-muted)",
                        border: "1px solid",
                        borderColor: prefs.transcription_provider === p.value
                          ? "rgba(20,184,166,0.3)"
                          : "var(--border-subtle)",
                      }}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>
            </Section>
          </>
        )}
      </main>
    </div>
  );
}
