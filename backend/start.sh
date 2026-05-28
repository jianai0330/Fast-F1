#!/bin/bash
# 服务器启动脚本
# 用法: bash start.sh

set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

echo "=== F1 Data API 启动脚本 ==="

# 创建 cache 目录
mkdir -p cache
mkdir -p cache/analysis

# 读取环境变量
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
  echo "已加载 .env"
fi

# 启动 uvicorn
echo "启动服务器，监听 0.0.0.0:8000 ..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
