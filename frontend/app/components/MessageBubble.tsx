"use client";

import ReactMarkdown from "react-markdown";
import type { Message } from "../lib/types";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-fade-in-up`}>
      {/* Assistant avatar */}
      {!isUser && (
        <div className="flex-shrink-0 mr-3 mt-1">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold"
            style={{
              background: "linear-gradient(135deg, var(--accent), #0d9488)",
              color: "#fff",
              boxShadow: "0 0 12px var(--accent-glow)",
            }}
          >
            AI
          </div>
        </div>
      )}

      <div
        className={`max-w-[78%] rounded-2xl text-sm leading-relaxed ${
          isUser
            ? "px-4 py-3 rounded-br-md"
            : "px-4 py-3 rounded-bl-md"
        }`}
        style={
          isUser
            ? {
                background: "var(--user-bubble)",
                border: "1px solid var(--user-bubble-border)",
                color: "#d4e4f7",
              }
            : {
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-subtle)",
              }
        }
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose-assistant">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
