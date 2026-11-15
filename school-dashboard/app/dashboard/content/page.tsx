"use client";
// app/dashboard/content/page.tsx
import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Upload, Youtube, Image, FileText, ChevronDown } from "lucide-react";
import { format, parseISO } from "date-fns";
import { contentApi, ContentItem } from "@/lib/api";
// Layout is provided by app/dashboard/layout.tsx
import { clsx } from "clsx";

const SUBJECTS = ["science", "maths", "hindi", "english", "sst", "gk"];
const GRADES   = [1,2,3,4,5,6,7,8,9,10];

const SUBJECT_ICONS: Record<string, string> = {
  science: "🔬", maths: "📐", hindi: "🔤", english: "📖", sst: "🌍", gk: "🌟",
};

export default function ContentPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"list" | "upload">("list");
  const [uploadType, setUploadType] = useState<"pdf" | "video" | "image">("pdf");
  const [subject, setSubject] = useState("science");
  const [grade, setGrade]     = useState(8);
  const [ytUrl, setYtUrl]     = useState("");
  const [filterSubject, setFilterSubject] = useState<string | undefined>();
  const fileRef = useRef<HTMLInputElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["content-list", filterSubject],
    queryFn: () =>
      contentApi.list({ subject: filterSubject, limit: 30 }).then((r) => r.data?.data || r.data),
  });

  const uploadPDF = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("subject", subject);
      fd.append("grade", grade.toString());
      return contentApi.uploadPDF(fd);
    },
    onSuccess: () => {
      toast.success("PDF uploaded and processing started!");
      qc.invalidateQueries({ queryKey: ["content-list"] });
      setTab("list");
    },
    onError: () => toast.error("Upload failed. Try again."),
  });

  const uploadVideo = useMutation({
    mutationFn: () =>
      contentApi.uploadVideo(ytUrl, subject, grade),
    onSuccess: () => {
      toast.success("Video added! Processing transcript...");
      setYtUrl(""); qc.invalidateQueries({ queryKey: ["content-list"] });
    },
    onError: () => toast.error("Invalid YouTube URL or no transcript available."),
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadPDF.mutate(file);
  };

  return (
    <>
      <div className="space-y-5">
        {/* Header + tabs */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Content Library</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {(data?.items || data?.content || []).length || "—"} published items
            </p>
          </div>
          <div className="flex rounded-xl overflow-hidden border border-gray-200 bg-white">
            {(["list", "upload"] as const).map((t) => (
              <button key={t} onClick={() => setTab(t)}
                className={clsx("px-5 py-2 text-sm font-semibold transition-all capitalize",
                  tab === t ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-50")}>
                {t === "list" ? "📚 Library" : "⬆️ Upload"}
              </button>
            ))}
          </div>
        </div>

        {tab === "list" ? (
          <>
            {/* Subject filter */}
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setFilterSubject(undefined)}
                className={clsx("px-3 py-1.5 rounded-lg text-xs font-semibold transition-all",
                  !filterSubject ? "bg-gray-800 text-white" : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50")}>
                All
              </button>
              {SUBJECTS.map((s) => (
                <button key={s} onClick={() => setFilterSubject(s === filterSubject ? undefined : s)}
                  className={clsx("px-3 py-1.5 rounded-lg text-xs font-semibold transition-all",
                    filterSubject === s ? "text-white shadow-sm" : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50")}
                  style={filterSubject === s ? { background: subjectColor(s) } : {}}>
                  {SUBJECT_ICONS[s]} {s}
                </button>
              ))}
            </div>

            {/* Content grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {isLoading
                ? [...Array(6)].map((_, i) => (
                    <div key={i} className="card p-4 h-28 skeleton rounded-2xl" />
                  ))
                : (data?.items || data?.content || []).map((item: ContentItem) => (
                    <ContentCard key={item.content_id} item={item} />
                  ))}
            </div>
          </>
        ) : (
          /* Upload panel */
          <div className="card p-6 max-w-2xl">
            <h2 className="font-bold text-gray-900 mb-5">Upload Content</h2>

            {/* Type selector */}
            <div className="flex rounded-xl overflow-hidden border border-gray-200 mb-5 bg-gray-50">
              {([
                { k: "pdf",   icon: FileText, label: "PDF Lesson" },
                { k: "video", icon: Youtube,  label: "YouTube Video" },
                { k: "image", icon: Image,    label: "Image / Diagram" },
              ] as const).map(({ k, icon: Icon, label }) => (
                <button key={k} onClick={() => setUploadType(k)}
                  className={clsx("flex-1 flex items-center justify-center gap-2 py-3 text-sm font-semibold transition-all",
                    uploadType === k ? "bg-white shadow-sm text-blue-600" : "text-gray-500 hover:text-gray-700")}>
                  <Icon size={15} />{label}
                </button>
              ))}
            </div>

            {/* Subject + Grade */}
            <div className="grid grid-cols-2 gap-4 mb-5">
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 block">Subject</label>
                <select value={subject} onChange={(e) => setSubject(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 bg-white">
                  {SUBJECTS.map((s) => (
                    <option key={s} value={s}>{SUBJECT_ICONS[s]} {s.charAt(0).toUpperCase() + s.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 block">Class</label>
                <select value={grade} onChange={(e) => setGrade(Number(e.target.value))}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 bg-white">
                  {GRADES.map((g) => (
                    <option key={g} value={g}>Class {g}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Upload area */}
            {uploadType === "pdf" && (
              <div
                onClick={() => fileRef.current?.click()}
                className="border-2 border-dashed border-gray-200 rounded-xl p-10 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/50 transition-all group">
                <Upload size={28} className="mx-auto text-gray-300 group-hover:text-blue-400 transition-colors mb-3" />
                <p className="font-semibold text-gray-600 group-hover:text-blue-600 text-sm">
                  {uploadPDF.isPending ? "Uploading..." : "Click to upload NCERT PDF"}
                </p>
                <p className="text-xs text-gray-400 mt-1">Max 50MB · PDF only</p>
                <input ref={fileRef} type="file" accept=".pdf"
                  className="hidden" onChange={handleFileSelect} />
              </div>
            )}

            {uploadType === "video" && (
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 block">
                    YouTube URL
                  </label>
                  <input value={ytUrl} onChange={(e) => setYtUrl(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=..."
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all" />
                </div>
                <button onClick={() => uploadVideo.mutate()}
                  disabled={!ytUrl || uploadVideo.isPending}
                  className="w-full py-3 rounded-xl font-semibold text-white text-sm transition-all disabled:opacity-50"
                  style={{ background: "linear-gradient(135deg, #EF4444, #DC2626)" }}>
                  {uploadVideo.isPending ? "Adding video..." : "Add YouTube Video →"}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}

function ContentCard({ item }: { item: ContentItem }) {
  const color = subjectColor(item.subject);
  const icon  = SUBJECT_ICONS[item.subject] ?? "📚";
  const srcIcon = item.source_type === "video" ? "🎬" : item.source_type === "pdf" ? "📄" : "🖼️";

  return (
    <div className="card p-4 card-hover" style={{ borderTop: `3px solid ${color}` }}>
      <div className="flex items-start gap-3">
        <span className="text-2xl">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-gray-800 text-sm truncate">{item.title}</p>
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            <span className="badge badge-blue text-xs">Class {item.grade}</span>
            <span className="text-xs text-gray-400">{srcIcon} {item.source_type}</span>
          </div>
          <p className="text-xs text-gray-400 mt-1.5">
            {item.chunk_count} chunks · {format(parseISO(item.created_at), "dd MMM yyyy")}
          </p>
        </div>
      </div>
    </div>
  );
}

function subjectColor(s: string) {
  const map: Record<string, string> = {
    science: "#10B981", maths: "#8B5CF6", hindi: "#EF4444",
    english: "#3B82F6", sst: "#F59E0B", gk: "#06B6D4",
  };
  return map[s] ?? "#94A3B8";
}
