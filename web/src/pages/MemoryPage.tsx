import { apiJson, apiPostJson } from "../lib/backend";
import { useState, useEffect, useCallback } from "react";

interface MemoryPageProps {
  userId: string;
  onBack: () => void;
}

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
      const [statsData, memoryData] = await Promise.all([
        apiJson<MemoryStats | null>(`/api/memory/${userId}/stats`, null),
        apiJson<{ organized?: MemoryItem[]; facts?: MemoryItem[] }>(`/api/memory/${userId}`, {}),
      ]);
      if (statsData) setStats(statsData);
      const list = memoryData.organized?.length ? memoryData.organized : memoryData.facts || [];
      setOrganized(list);
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
      const data = await apiJson<{ memories?: MemoryItem[] }>(`/api/memory/${userId}?query=${encodeURIComponent(searchQuery)}&top_k=8`, { memories: [] });
      setSearchResults(data.memories || []);
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
      const isSelfName = /(?:\u6211|\u4f60)(?:\u7684\u540d\u5b57)?(?:\u662f|\u53eb)[\u4e00-\u9fa5a-zA-Z\u00b7]{1,12}/.test(text);
      const data = await apiPostJson<{ deduplicated?: boolean } | null>(
        `/api/memory/${userId}`,
        isSelfName
          ? { fact: text, category: "identity", layer: "L1" }
          : { fact: text, category: "preference", layer: "L7" },
        null
      );
      if (data) {
        setNewFact("");
        setMessage(data.deduplicated ? "\u5df2\u5b58\u5728\u76f8\u540c\u8bb0\u5fc6" : "\u5df2\u4fdd\u5b58");
        loadData();
      } else {
        setMessage("\u4fdd\u5b58\u5931\u8d25");
      }
    } catch {
      setMessage("\u4fdd\u5b58\u5931\u8d25");
    } finally {
      setAdding(false);
    }
  };
  const handleDreaming = async () => {
    setDreaming(true);
    setMessage("");
    try {
      const data = await apiPostJson<{ promoted_count?: number } | null>(`/api/memory/${userId}/dreaming`, undefined, null);
      if (data) {
        setMessage(`\u6574\u7406\u5b8c\u6210 \u00b7 \u63d0\u5347 ${data.promoted_count ?? 0} \u6761\u957f\u671f\u8bb0\u5fc6`);
        loadData();
      } else {
        setMessage("\u6574\u7406\u5931\u8d25");
      }
    } catch {
      setMessage("\u65e0\u6cd5\u8fde\u63a5\u540e\u7aef");
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
