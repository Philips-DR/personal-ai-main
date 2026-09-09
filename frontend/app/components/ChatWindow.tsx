"use client";

import { useState, useRef, useEffect } from "react";
import { api } from "../lib/api-client";
import type { ChatResponse, Message, PendingAction } from "../lib/types";
import MessageBubble from "./MessageBubble";

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage() {
    if (!input.trim() || loading) return;

    const userMsg: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history = messages.slice(-6); // Last 3 exchanges
      const res: ChatResponse = await api.chat({
        message: userMsg.content,
        conversation_history: history,
      });

      const assistantMsg: Message = { role: "assistant", content: res.content };
      setMessages((prev) => [...prev, assistantMsg]);

      if (res.pending_actions?.length) {
        setPendingAction(res.pending_actions[0]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err instanceof Error ? err.message : "Unknown error"}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleActionApproval(approved: boolean) {
    if (!pendingAction) return;
    const action = pendingAction;
    setPendingAction(null);

    try {
      const result = approved
        ? await api.actions.execute(action)
        : await api.actions.reject(action);
      setMessages((prev) => [...prev, { role: "assistant", content: result.message }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Action failed: ${err instanceof Error ? err.message : "Unknown error"}` },
      ]);
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      {/* Header */}
      <header
        className="px-6 py-4 flex items-center justify-between flex-shrink-0"
        style={{
          borderBottom: "1px solid var(--border-subtle)",
          background: "rgba(10, 10, 15, 0.8)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold"
            style={{
              background: "linear-gradient(135deg, var(--accent), #0d9488)",
              color: "#fff",
              boxShadow: "0 0 16px var(--accent-glow)",
            }}
          >
            A
          </div>
          <div>
            <h1
              className="text-base font-semibold tracking-tight"
              style={{ color: "var(--text-primary)" }}
            >
              Personal AI Assistant
            </h1>
            <p className="text-[0.7rem] tracking-wide uppercase" style={{ color: "var(--text-muted)" }}>
              AyaData AI Solutions
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <a
            href="/admin/audit"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
            style={{
              background: "var(--bg-elevated)",
              color: "var(--text-secondary)",
              border: "1px solid var(--border-subtle)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "rgba(20, 184, 166, 0.3)";
              e.currentTarget.style.color = "var(--accent)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border-subtle)";
              e.currentTarget.style.color = "var(--text-secondary)";
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            Audit
          </a>
          <a
            href="/settings"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
            style={{
              background: "var(--bg-elevated)",
              color: "var(--text-secondary)",
              border: "1px solid var(--border-subtle)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "rgba(20, 184, 166, 0.3)";
              e.currentTarget.style.color = "var(--accent)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border-subtle)";
              e.currentTarget.style.color = "var(--text-secondary)";
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            Settings
          </a>
          <div
            className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs"
            style={{
              background: "var(--accent-dim)",
              color: "var(--accent)",
              border: "1px solid rgba(20, 184, 166, 0.15)",
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: "var(--accent)", boxShadow: "0 0 6px var(--accent)" }}
            />
            Online
          </div>
        </div>
      </header>

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto px-6 py-6 space-y-5"
        style={{ background: "var(--bg-deep)" }}
      >
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center mt-24 animate-fade-in-up">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-bold mb-6"
              style={{
                background: "linear-gradient(135deg, var(--accent), #0d9488)",
                color: "#fff",
                boxShadow: "0 0 40px var(--accent-glow), 0 0 80px rgba(20, 184, 166, 0.1)",
              }}
            >
              A
            </div>
            <p
              className="text-lg font-medium"
              style={{ color: "var(--text-primary)" }}
            >
              How can I help you today?
            </p>
            <p className="text-sm mt-2 text-center max-w-xs" style={{ color: "var(--text-muted)" }}>
              Try &ldquo;remind me to send the report to Elton by Friday&rdquo;
            </p>
            <div
              className="flex gap-2 mt-8 flex-wrap justify-center"
            >
              {["Show my tasks", "Summarize recent emails", "Generate morning brief"].map((hint) => (
                <button
                  key={hint}
                  onClick={() => { setInput(hint); }}
                  className="px-3.5 py-2 rounded-xl text-xs font-medium transition-all duration-200"
                  style={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-secondary)",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = "rgba(20, 184, 166, 0.3)";
                    e.currentTarget.style.color = "var(--accent)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = "var(--border-subtle)";
                    e.currentTarget.style.color = "var(--text-secondary)";
                  }}
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {loading && (
          <div className="flex items-center gap-3 animate-fade-in-up">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0"
              style={{
                background: "linear-gradient(135deg, var(--accent), #0d9488)",
                color: "#fff",
                boxShadow: "0 0 12px var(--accent-glow)",
              }}
            >
              AI
            </div>
            <div
              className="px-4 py-3 rounded-2xl rounded-bl-md"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div className="thinking-dots">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Pending Action Review Gate */}
      {pendingAction && (
        <div
          className="mx-6 mb-3 p-4 rounded-xl animate-fade-in-up"
          style={{
            background: "rgba(245, 158, 11, 0.08)",
            border: "1px solid rgba(245, 158, 11, 0.25)",
          }}
        >
          <div className="flex items-start gap-3">
            <div className="text-amber-400 mt-0.5">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-amber-300 text-sm font-semibold mb-1">
                Action requires your approval
              </p>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                {pendingAction.description}
              </p>
              <div className="flex gap-2.5 mt-3">
                <button
                  onClick={() => handleActionApproval(true)}
                  className="px-4 py-1.5 text-sm font-medium rounded-lg transition-all duration-200"
                  style={{
                    background: "rgba(34, 197, 94, 0.15)",
                    color: "#4ade80",
                    border: "1px solid rgba(34, 197, 94, 0.3)",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "rgba(34, 197, 94, 0.25)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "rgba(34, 197, 94, 0.15)";
                  }}
                >
                  Approve
                </button>
                <button
                  onClick={() => handleActionApproval(false)}
                  className="px-4 py-1.5 text-sm font-medium rounded-lg transition-all duration-200"
                  style={{
                    background: "rgba(239, 68, 68, 0.12)",
                    color: "#f87171",
                    border: "1px solid rgba(239, 68, 68, 0.25)",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "rgba(239, 68, 68, 0.22)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "rgba(239, 68, 68, 0.12)";
                  }}
                >
                  Reject
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Input */}
      <div
        className="px-6 py-4 flex-shrink-0"
        style={{
          borderTop: "1px solid var(--border-subtle)",
          background: "rgba(10, 10, 15, 0.6)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
        }}
      >
        <form
          onSubmit={(e) => { e.preventDefault(); sendMessage(); }}
          className="flex gap-3 items-end"
        >
          <div className="flex-1 relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me anything..."
              className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-all duration-200"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
              }}
              disabled={loading}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = "rgba(20, 184, 166, 0.4)";
                e.currentTarget.style.boxShadow = "0 0 0 3px var(--accent-dim)";
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = "var(--border-subtle)";
                e.currentTarget.style.boxShadow = "none";
              }}
            />
          </div>
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-5 py-3 text-sm font-semibold rounded-xl transition-all duration-200 flex-shrink-0"
            style={
              loading || !input.trim()
                ? {
                    background: "var(--bg-elevated)",
                    color: "var(--text-muted)",
                    border: "1px solid var(--border-subtle)",
                    cursor: "not-allowed",
                  }
                : {
                    background: "linear-gradient(135deg, var(--accent), #0d9488)",
                    color: "#fff",
                    border: "none",
                    boxShadow: "0 0 20px var(--accent-glow)",
                  }
            }
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
