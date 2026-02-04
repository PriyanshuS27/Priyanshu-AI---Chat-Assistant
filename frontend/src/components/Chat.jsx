import { useState } from "react";
import "./Chat.css";

export default function Chat() {
  const [messages, setMessages] = useState([
    { role: "bot", text: "👋 Hi! I'm Priyanshu AI. Ask me anything about my background, skills, and experience." }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const suggestions = [
    "💼 Tell me about yourself",
    "🎯 What are your key skills?",
    "📄 Send me your resume",
    "🚀 What projects have you built?",
    "💬 How can I contact you?"
  ];

  const sendMessage = async (text) => {
    if (!text.trim()) return;

    const userMessage = { role: "user", text };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: newMessages
        })
      });

      if (!res.ok) throw new Error("Failed to get response");
      
      const data = await res.json();
      setMessages([...newMessages, { role: "bot", text: data.reply }]);
    } catch (error) {
      console.error("Error:", error);
      setMessages([...newMessages, { role: "bot", text: "Sorry, I encountered an error. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>🧠 Priyanshu AI Assistant</h1>
        <p>Ask me anything!</p>
      </div>

      <div className="chat-messages">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`message ${m.role}`}
          >
            <div className="message-bubble">
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message bot">
            <div className="message-bubble loading">
              ⏳ Thinking...
            </div>
          </div>
        )}
      </div>

      <div className="chat-suggestions">
        {suggestions.map((s, i) => (
          <button
            key={i}
            className="suggestion-btn"
            onClick={() => sendMessage(s.replace(/^[^\s]*\s/, ""))}
            disabled={loading}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="chat-input-box">
        <input
          type="text"
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !loading && sendMessage(input)}
          placeholder="Type your message..."
          disabled={loading}
        />
        <button
          className="chat-send"
          onClick={() => sendMessage(input)}
          disabled={loading}
        >
          {loading ? "..." : "▶"}
        </button>
      </div>
    </div>
  );
}
