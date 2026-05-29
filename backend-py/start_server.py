"""小满后端启动脚本"""

import os
import sys

# 设置 API Key
os.environ.setdefault("LLM_API_KEY", "pipe-f0de69bc8255f7b71d0613337e4b7b686b38a545a7e8d602d1887030103df845")
os.environ.setdefault("OPENAI_API_KEY", "pipe-f0de69bc8255f7b71d0613337e4b7b686b38a545a7e8d602d1887030103df845")

# 启动服务器
import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=18789)
