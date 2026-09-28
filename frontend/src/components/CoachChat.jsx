import { useEffect, useRef, useState } from "react";
import { getCoaches, sendChat } from "../api";

// The backend accepts at most 1000 characters per history turn and trims to the latest turns itself.
const MAX_TURN_CHARS = 1000;
const MAX_HISTORY = 10;

const SUGGESTIONS = [
  "How am I doing this month?",
  "Which category am I spending the most in?",
  "Show me my latest expenses.",
];

export default function CoachChat() {
  const [coaches, setCoaches] = useState([]);
  const [coachId, setCoachId] = useState("");
  const [coachesError, setCoachesError] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState(null);
  const listRef = useRef(null);

  useEffect(() => {
    getCoaches()
      .then((list) => {
        setCoaches(list);
        if (list.length) setCoachId(list[0].id);
      })
      .catch((e) => setCoachesError(e.message));
  }, []);

  // Count seconds while waiting, so a slow local model visibly looks "busy", not frozen.
  useEffect(() => {
    if (!sending) return undefined;
    setElapsed(0);
    const timer = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [sending]);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, sending]);

  const coach = coaches.find((c) => c.id === coachId);

  async function send(text) {
    const message = text.trim();
    if (!message || sending || !coach) return;

    // History = earlier successful turns only (server is stateless; it keeps no conversation).
    const history = messages
      .filter((m) => !m.failed)
      .slice(-MAX_HISTORY)
      .map((m) => ({ role: m.role, content: m.content.slice(0, MAX_TURN_CHARS) }));

    const userMessage = { role: "user", content: message };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setError(null);
    setSending(true);
    try {
      const response = await sendChat({ coachId: coach.id, message, history });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.reply, coachName: coach.display_name, toolsUsed: response.tools_used },
      ]);
    } catch (e) {
      // Mark the question as undelivered (excluded from future history) and give the text back.
      setMessages((prev) => prev.map((m) => (m === userMessage ? { ...m, failed: true } : m)));
      setInput(message);
      setError(e.message);
    } finally {
      setSending(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    send(input);
  }

  return (
    <section className="panel chat">
      <h2>AI Financial Coach</h2>
      <p className="muted small">
        Answers come from your real SpendSmart data. The coach only changes the style, never the numbers.
      </p>

      <label className="coach-select">
        Choose your coach
        <select value={coachId} onChange={(e) => setCoachId(e.target.value)} disabled={sending || coaches.length === 0}>
          {coaches.map((c) => (
            <option key={c.id} value={c.id}>
              {c.display_name}
            </option>
          ))}
        </select>
      </label>
      {coach && <p className="tagline">{coach.tagline}</p>}
      {coachesError && <p className="error" role="alert">Couldn't load coaches: {coachesError}</p>}

      <div className="messages" ref={listRef} aria-live="polite">
        {messages.length === 0 && !sending && (
          <div className="empty">
            <p>Ask your coach about your budget and spending.</p>
            <div className="chips">
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" className="chip" onClick={() => setInput(s)} disabled={!coach}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role} ${m.failed ? "failed" : ""}`}>
            {m.role === "assistant" && <span className="bubble-author">{m.coachName}</span>}
            <p>{m.content}</p>
            {m.failed && <span className="bubble-meta">Not delivered</span>}
            {m.toolsUsed?.length > 0 && (
              <span className="bubble-meta">Checked your data: {[...new Set(m.toolsUsed)].join(", ")}</span>
            )}
          </div>
        ))}
        {sending && (
          <div className="bubble assistant thinking" role="status">
            <span className="bubble-author">{coach?.display_name}</span>
            <p>
              Thinking<span className="dots" aria-hidden="true" /> {elapsed}s
            </p>
            <span className="bubble-meta">A local AI model can take a minute or two. Please keep this page open.</span>
          </div>
        )}
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      <form onSubmit={handleSubmit} className="chat-form">
        <input
          type="text"
          value={input}
          maxLength={1000}
          placeholder={coach ? `Ask ${coach.display_name}…` : "Coach unavailable"}
          onChange={(e) => setInput(e.target.value)}
          disabled={!coach}
          aria-label="Message to your coach"
        />
        <button type="submit" disabled={sending || !input.trim() || !coach}>
          {sending ? "Waiting…" : "Send"}
        </button>
      </form>
    </section>
  );
}
