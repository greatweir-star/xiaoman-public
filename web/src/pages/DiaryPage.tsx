import { useState, useEffect } from "react";

interface DiaryEntry {
  date?: string;
  content?: string;
  locked?: boolean;
  unlock_hint?: string;
}

interface DiaryPageProps {
  userId: string;
  onBack: () => void;
}

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:18789";

export default function DiaryPage({ userId, onBack }: DiaryPageProps) {
  const [entries, setEntries] = useState<DiaryEntry[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/memory/${userId}/diary`)
      .then((r) => (r.ok ? r.json() : { entries: [] }))
      .then((d) => {
        const list: DiaryEntry[] = d.entries || [];
        list.sort((a, b) => (b.date || "").localeCompare(a.date || ""));
        setEntries(list);
      })
      .catch(() => setEntries([]));
  }, [userId]);

  return (
    <div className="sub-page">
      <div className="sub-page-header">
        <button className="sub-page-back" onClick={onBack}>‹ 返回</button>
        <h2>日记</h2>
        <div style={{ width: 40 }} />
      </div>

      <div className="diary-list">
        {entries.length === 0 && (
          <div className="diary-empty">今天还没有日记哦~</div>
        )}
        {entries.map((entry, i) => {
          const key = entry.date || String(i);
          const locked = !!entry.locked;
          const open = expanded === key && !locked;

          return (
            <div key={key} className={`diary-card ${locked ? "diary-card-locked" : ""}`}>
              <div className="diary-card-date">
                {entry.date}
                {locked && <span className="diary-lock-icon">🔒</span>}
              </div>
              {locked ? (
                <div className="diary-card-locked-hint">
                  {entry.unlock_hint || "关系升级后可查看更早日记"}
                </div>
              ) : (
                <>
                  <div className={`diary-card-content ${open ? "" : "diary-card-preview"}`}>
                    {entry.content}
                  </div>
                  {entry.content && entry.content.length > 120 && (
                    <button
                      type="button"
                      className="diary-toggle"
                      onClick={() => setExpanded(open ? null : key)}
                    >
                      {open ? "收起" : "展开"}
                    </button>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
