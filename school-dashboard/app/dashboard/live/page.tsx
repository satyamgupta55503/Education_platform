"use client";
// app/dashboard/live/page.tsx — Start Live Lesson page with AI Q&A
import { useState, useRef, useEffect } from "react";
import toast from "react-hot-toast";
import api from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────
interface Message {
  role: "teacher" | "ai";
  content: string;
}

const SUBJECTS = [
  { value: "science", label: "🔬 Science" },
  { value: "maths", label: "📐 Maths" },
  { value: "hindi", label: "🔤 Hindi" },
  { value: "english", label: "📖 English" },
  { value: "sst", label: "🌍 SST" },
  { value: "gk", label: "🌟 GK" },
];

const GRADES = Array.from({ length: 10 }, (_, i) => i + 1);

export default function LiveLessonPage() {
  const [lessonStarted, setLessonStarted] = useState(false);
  const [lessonId, setLessonId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [askingAI, setAskingAI] = useState(false);

  // Form state
  const [subject, setSubject] = useState("");
  const [topic, setTopic] = useState("");
  const [grade, setGrade] = useState("");
  const [className, setClassName] = useState("");

  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Start Lesson ────────────────────────────────────────────────────────────
  const handleStartLesson = async () => {
    if (!subject || !topic || !grade || !className) {
      toast.error("Please fill all fields");
      return;
    }

    setLoading(true);
    try {
      const res = await api.post("/teacher/lesson/start", {
        subject,
        topic,
        grade: parseInt(grade),
        class_name: className,
      });

      const data = res.data;
      setLessonId(data.lesson_id);
      setLessonStarted(true);
      setMessages([
        {
          role: "ai",
          content: `🎓 Lesson started! Topic: "${topic}" for Grade ${grade}, ${className}.\n\nAsk me anything about ${topic} — I'm ready to help teach!`,
        },
      ]);
      toast.success("Lesson started successfully! 🎓");
    } catch (err: unknown) {
      const errorMsg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || "Failed to start lesson"
          : "Failed to start lesson";
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // ── Ask AI ──────────────────────────────────────────────────────────────────
  const handleAskAI = async () => {
    if (!question.trim() || !lessonId) return;

    const userQuestion = question.trim();
    setQuestion("");
    setMessages((prev) => [...prev, { role: "teacher", content: userQuestion }]);
    setAskingAI(true);

    try {
      const res = await api.post(`/teacher/lesson/${lessonId}/question`, {
        question: userQuestion,
        language: "hi",
      });

      const data = res.data;
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: data.answer || data.response || "No response received" },
      ]);
    } catch (err: unknown) {
      const errorMsg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || "Failed to get response"
          : "Failed to get response";
      toast.error(errorMsg);
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "⚠️ Sorry, I couldn't process that question. Please try again." },
      ]);
    } finally {
      setAskingAI(false);
    }
  };

  // ── Handle Enter Key ────────────────────────────────────────────────────────
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAskAI();
    }
  };

  // ── Lesson Form View ────────────────────────────────────────────────────────
  if (!lessonStarted) {
    return (
      <div className="space-y-6 max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center">
          <div
            className="w-16 h-16 rounded-2xl mx-auto mb-4 flex items-center justify-center text-3xl shadow-lg"
            style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}
          >
            🎓
          </div>
          <h1 className="text-2xl font-bold text-white">Start Live Lesson</h1>
          <p className="text-slate-400 text-sm mt-2">
            Configure your lesson and let EduCat AI assist you in real-time
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-slate-800/50 rounded-2xl border border-white/5 p-6 space-y-5">
          {/* Subject */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Subject
            </label>
            <select
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-slate-700/50 border border-white/10 text-white text-sm focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/30 transition-colors"
            >
              <option value="" className="bg-slate-800">Select a subject...</option>
              {SUBJECTS.map((s) => (
                <option key={s.value} value={s.value} className="bg-slate-800">
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          {/* Topic */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Topic
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., Photosynthesis, Quadratic Equations..."
              className="w-full px-4 py-3 rounded-xl bg-slate-700/50 border border-white/10 text-white text-sm placeholder:text-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/30 transition-colors"
            />
          </div>

          {/* Grade & Class Name row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Grade
              </label>
              <select
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-slate-700/50 border border-white/10 text-white text-sm focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/30 transition-colors"
              >
                <option value="" className="bg-slate-800">Select grade...</option>
                {GRADES.map((g) => (
                  <option key={g} value={g} className="bg-slate-800">
                    Grade {g}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Class Name
              </label>
              <input
                type="text"
                value={className}
                onChange={(e) => setClassName(e.target.value)}
                placeholder="e.g., 8-A, 10-B..."
                className="w-full px-4 py-3 rounded-xl bg-slate-700/50 border border-white/10 text-white text-sm placeholder:text-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/30 transition-colors"
              />
            </div>
          </div>

          {/* Start Button */}
          <button
            onClick={handleStartLesson}
            disabled={loading || !subject || !topic || !grade || !className}
            className="w-full py-4 rounded-xl text-white font-bold text-lg shadow-lg disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-all active:scale-[0.98]"
            style={{
              background: "linear-gradient(135deg, #3B82F6, #8B5CF6)",
            }}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Starting...
              </span>
            ) : (
              "Start Lesson 🎓"
            )}
          </button>
        </div>

        {/* Info note */}
        <div className="bg-slate-800/30 rounded-xl border border-white/5 p-4 flex items-start gap-3">
          <span className="text-lg">💡</span>
          <div>
            <p className="text-sm text-slate-300 font-medium">How it works</p>
            <p className="text-xs text-slate-500 mt-1">
              Once you start a lesson, you can ask EduCat AI questions in real-time.
              The AI will respond with explanations tailored to your students&apos; level.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ── Projector / Chat View ───────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-4xl mx-auto">
      {/* Lesson header bar */}
      <div className="shrink-0 bg-slate-800/50 rounded-2xl border border-white/5 p-4 mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
            style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}
          >
            🎓
          </div>
          <div>
            <p className="text-white font-semibold text-sm capitalize">
              {subject} — {topic}
            </p>
            <p className="text-xs text-slate-500">
              Grade {grade} · {className}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Live
          </span>
          <button
            onClick={() => {
              setLessonStarted(false);
              setLessonId(null);
              setMessages([]);
              toast.success("Lesson ended");
            }}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-red-400 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 transition-colors"
          >
            End Lesson
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-2 pb-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex items-start gap-3 ${
              msg.role === "teacher" ? "flex-row-reverse" : ""
            }`}
          >
            {/* Avatar */}
            <div
              className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm shrink-0 shadow-md ${
                msg.role === "ai"
                  ? ""
                  : "bg-gradient-to-br from-blue-500 to-violet-500 text-white font-bold"
              }`}
              style={
                msg.role === "ai"
                  ? { background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }
                  : undefined
              }
            >
              {msg.role === "ai" ? "🐱" : "👤"}
            </div>

            {/* Message bubble */}
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "ai"
                  ? "bg-slate-800/70 border border-white/5 text-slate-200"
                  : "bg-blue-500/20 border border-blue-500/20 text-blue-100"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {/* AI typing indicator */}
        {askingAI && (
          <div className="flex items-start gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center text-sm shrink-0 shadow-md"
              style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}
            >
              🐱
            </div>
            <div className="bg-slate-800/70 border border-white/5 rounded-2xl px-4 py-3">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input area */}
      <div className="shrink-0 bg-slate-800/50 rounded-2xl border border-white/5 p-3 flex items-center gap-3">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask EduCat AI a question..."
          disabled={askingAI}
          className="flex-1 px-4 py-3 rounded-xl bg-slate-700/50 border border-white/10 text-white text-sm placeholder:text-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/30 transition-colors disabled:opacity-50"
        />
        <button
          onClick={handleAskAI}
          disabled={askingAI || !question.trim()}
          className="px-5 py-3 rounded-xl text-white font-semibold text-sm shadow-lg disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-all active:scale-[0.97]"
          style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}
        >
          {askingAI ? "..." : "Ask AI 🐱"}
        </button>
      </div>
    </div>
  );
}
