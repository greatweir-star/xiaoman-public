# 小满后端（Python）

## Python 版本要求

**必须使用 Python 3.14**（Alice 系统自带的 Python 3.11 不兼容 LanceDB）

```bash
# Python 3.14 路径
C:\Python314\python.exe

# 安装依赖
C:\Python314\python.exe -m pip install -r requirements.txt
```

## 启动方式

### 方式一：直接启动

```bash
# Windows
start_server.bat

# 或手动
C:\Python314\python.exe main.py
```

### 方式二：Docker

```bash
docker-compose up --build
```

## 环境变量

```bash
# 必需
LLM_API_KEY=your_api_key_here

# 可选 — 对话 LLM
LLM_BASE_URL=https://api.pipellm.ai/openai/v1
LLM_MODEL=gpt-4o-mini
LOG_LEVEL=INFO

# 可选 — 每日形象生图（无配置时使用 /styles/*.svg 轮换）
# 方式 A：固定 CDN 图（不调用远端）
DAILY_AVATAR_IMAGE_HOOK=https://cdn.example.com/xiaoman-today.png

# 方式 B：OpenAI 兼容 images/generations（需同时设置 base + key）
DAILY_AVATAR_IMAGE_API_URL=https://api.openai.com/v1
XIAOMAN_IMAGE_API_KEY=sk-...
# 可选细化
XIAOMAN_IMAGE_MODEL=dall-e-3
XIAOMAN_IMAGE_SIZE=1024x1024
```

也可在 `xiaoman.json` 的 `dailyAvatar.imageApiHook` 写入静态图 URL。

## 项目结构

```
backend-py/
├── main.py                 # FastAPI WebSocket 入口
├── requirements.txt        # 依赖（含 LanceDB）
├── start_server.bat        # Windows 启动脚本
├── xiaoman/
│   ├── chunk.py           # ChunkTable/ChunkRow
│   ├── session.py         # XiaomanSession
│   ├── tool_registry.py   # Tool 注册表
│   ├── loop.py            # Session-first Loop
│   ├── llm_service.py     # LLM 封装
│   ├── prompts.py         # System Prompt
│   ├── compaction.py      # Session 压缩
│   ├── persistence.py     # JSONL 持久化
│   ├── errors.py          # 错误处理
│   ├── memory/            # 记忆模块
│   │   ├── engine.py      # 记忆引擎
│   │   ├── store.py       # 存储层
│   │   ├── extractor.py   # Forked Agent 提取
│   │   ├── dreaming.py    # 自动整理
│   │   ├── search.py      # 混合搜索
│   │   ├── lineage.py     # 血缘追踪
│   │   ├── promotion.py   # 记忆提升
│   │   └── vector_store.py # LanceDB 向量存储
│   └── tools/             # Tool 实现
│       ├── memory_update.py
│       ├── emotion_detect.py
│       ├── time_sense.py
│       └── night_guard.py
└── data/                   # 数据目录
    ├── memory/             # 记忆文件
    ├── sessions/           # 会话文件
    ├── life-log/           # 生活日志
    └── lancedb/            # LanceDB 向量数据库
```

## LanceDB 向量数据库

- **存储路径**：`data/lancedb/`
- **维度**：3072（OpenAI text-embedding-3-large）
- **表结构**：每个 session 独立一张表
- **混合搜索**：向量 + 全文（FTS）
