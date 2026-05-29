# 小满记忆模块

用户级记忆系统：提取 → 存储 → 召回 → 整理 → 联动。

## 目录结构

| 模块 | 职责 |
|------|------|
| `engine.py` | 统一入口 |
| `extractor.py` | 异步事实提取（cursor、互斥、批量） |
| `store.py` | JSONL/JSON 持久化 |
| `vector_store.py` | LanceDB 语义索引 |
| `search.py` | 混合召回 |
| `dreaming.py` | Light/REM 整理 |
| `promotion.py` | 短期→长期提升 |
| `lineage.py` | 血缘 DAG |
| `user_scope.py` | `data/users/{id}/memory/` 路径 |

## 环境变量

| 变量 | 说明 |
|------|------|
| `XIAOMAN_SECRET_KEY` | 秘密加密密钥 |
| `XIAOMAN_DREAMING_FAST=1` | Dreaming 跳过 LLM 去重 |
| `XIAOMAN_BATCH_EXTRACT=1` | 夜间合并 facts 单次 LLM 提取 |

## REST API

- `GET/POST /api/memory/{user_id}`
- `GET /api/memory/{user_id}/stats`
- `GET /api/memory/{user_id}/diary`
- `POST /api/memory/{user_id}/dreaming`
- `GET /api/memory/{user_id}/secrets?reveal=`
- `GET /api/memory/{user_id}/lineage/{node_id}`

## WebSocket 事件

见 `xiaoman/ws_events.py`：`memory_recall`、`linkage_triggered`、`skill_unlocked`、`typing`。

## 联动配置

`backend-py/config/linkages/*.yaml`
