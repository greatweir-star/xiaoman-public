import { useState, useEffect, useCallback } from "react";

interface MemoryPageProps {
  userId: string;
  onBack: () => void;
}

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:18789";

interface MemoryItem {
  fact?: string;
  content?: string;
  category?: string;
  layer?: string;
  tier?: string;
  timestamp?: string;
  weight?: number;
}

interface MemoryStats {
  total_facts: number;
  total_organized: number;
  total_long_term: number;
}

export default function MemoryPage({ userId, onBack }: MemoryPageProps) {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [organized, setOrganized] = useState<MemoryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<MemoryItem[] | null>(null);
  const [newFact, setNewFact] = useState("");
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [dreaming, setDreaming] = useState(false);
  const [message, setMessage] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, memRes] = await Promise.all([
        fetch(`${API_URL}/api/memory/${userId}/stats`),
        fetch(`${API_URL}/api/memory/${userId}`),
      ]);
      if (statsRes.ok) setStats(await statsRes.json());
      if (memRes.ok) {
        const data = await memRes.json();
        const list = data.organized?.length ? data.organized : data.facts || [];
        setOrganized(list);
      }
    } catch {
      setMessage("加载失败，请确认后端已启动");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }
    try {
      const res = await fetch(
        `${API_URL}/api/memory/${userId}?query=${encodeURIComponent(searchQuery)}&top_k=8`
      );
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.memories || []);
      }
    } catch {
      setMessage("搜索失败");
    }
  };

  const handleAdd = async () => {
    const text = newFact.trim();
    if (!text || adding) return;
    setAdding(true);
    setMessage("");
    try {
      const isSelfName = /我(?:的名字)?叫[\u4e00-\u9fa5a-zA-Z·]{1,12}/.test(text);
      const res = await fetch(`${API_URL}/api/memory/${userId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          isSelfName
            ? { fact: text, category: "identity", layer: "L1" }
            : { fact: text, category: "preference", layer: "L7" }
        ),
      });
      if (res.ok) {
        const data = await res.json();
        setNewFact("");
        setMessage(data.deduplicated ? "已存在相同记忆" : "已保存");
        loadData();
      } else {
        setMessage("保存失败");
      }
    } catch {
      setMessage("保存失败");
    } finally {
      setAdding(false);
    }
  };

  const handleDreaming = async () => {
    setDreaming(true);
    setMessage("");
    try {
      const res = await fetch(`${API_URL}/api/memory/${userId}/dreaming`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        setMessage(`整理完成 · 提升 ${data.promoted_count ?? 0} 条长期记忆`);
        loadData();
      } else {
        setMessage("整理失败");
      }
    } catch {
      setMessage("无法连接后端");
    } finally {
      setDreaming(false);
    }
  };

  const displayList = searchResults ?? organized;
  const factText = (m: MemoryItem) => m.fact || m.content || "";

  return (
    <div className="sub-page memory-page">
      <div className="sub-page-header">
        <button className="sub-page-back" onClick={onBack}>‹ 返回</button>
        <h2>记忆</h2>
        <div style={{ width: 40 }} />
      </div>

      {stats && (
        <div className="memory-stats">
          <span>事实 {stats.total_facts}</span>
          <span>整理 {stats.total_organized}</span>
          <span>长期 {stats.total_long_term}</span>
        </div>
      )}

      <div className="memory-toolbar">
        <input
          className="memory-search-input"
          placeholder="搜索记忆，如：名字、喜好…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <button type="button" className="memory-btn" onClick={handleSearch}>搜</button>
      </div>

      <div className="memory-add-row">
        <input
          className="memory-search-input"
          placeholder="手动添加一条记忆…"
          value={newFact}
          onChange={(e) => setNewFact(e.target.value)}
        />
        <button
          type="button"
          className="memory-btn primary"
          disabled={adding || !newFact.trim()}
          onClick={handleAdd}
        >
          {adding ? "…" : "加"}
        </button>
      </div>

      <div className="memory-actions">
        <button
          type="button"
          className="memory-dream-btn"
          disabled={dreaming}
          onClick={handleDreaming}
        >
          {dreaming ? "整理中…" : "🌙 整理记忆（Dreaming）"}
        </button>
      </div>

      {message && <p className="memory-toast">{message}</p>}

      <div className="memory-list">
        {loading && <div className="loading">加载中…</div>}
        {!loading && displayList.length === 0 && (
          <div className="diary-empty">还没有记忆，多聊几句吧~</div>
        )}
        {displayList.map((item, i) => (
          <div
            key={i}
            className={`memory-card ${item.tier === "long_term" ? "long-term" : ""}`}
          >
            <div className="memory-card-meta">
              {item.tier === "long_term" && <span className="memory-badge">长期</span>}
              {item.category && <span className="memory-tag">{item.category}</span>}
              {item.layer && <span className="memory-tag">{item.layer}</span>}
            </div>
            <div className="memory-card-text">{factText(item)}</div>
            {item.timestamp && (
              <div className="memory-card-time">{item.timestamp.slice(0, 16)}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
