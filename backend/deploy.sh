#!/bin/bash
# Fast-F1 后端部署脚本（含自动备份）

SERVER="ubuntu@43.129.185.165"
SSH_KEY="~/.ssh/id_rsa"
REMOTE_DIR="~/Fast-F1/backend"
LOCAL_DIR="$(dirname "$0")/"

echo "=== Step 1: 备份服务器数据库 ==="
ssh -i $SSH_KEY $SERVER "cp $REMOTE_DIR/db/f1.db $REMOTE_DIR/db/f1.db.backup.\$(date +%Y%m%d_%H%M%S)"
echo "备份完成"

echo "=== Step 2: 同步代码 ==="
rsync -avz -e "ssh -i $SSH_KEY" $LOCAL_DIR $SERVER:$REMOTE_DIR/ \
    --exclude '__pycache__/' \
    --exclude 'cache/' \
    --exclude '*.db' \
    --exclude '*.db-shm' \
    --exclude '*.db-wal'
echo "同步完成"

echo "=== Step 3: 重启服务 ==="
ssh -i $SSH_KEY $SERVER "sudo systemctl restart f1api"
sleep 2
ssh -i $SSH_KEY $SERVER "sudo systemctl status f1api --no-pager"
echo "=== 部署完成 ==="
