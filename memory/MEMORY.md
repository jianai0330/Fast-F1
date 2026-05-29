# 项目记忆索引

## 项目概况
F1 数据可视化微信小程序，工作目录：`/Users/aijian/Downloads/Fast-F1/`
Python 环境：`/Users/aijian/anaconda3/envs/llm_eval_new/bin/python`

## 关键文件
- `F1_miniprogram_design.md` — 产品设计文档（完整版）
- `CLAUDE.md` — 本项目开发规范与上下文（→ 详见下方）
- `memory/architecture.md` — 技术架构详细笔记
- `memory/progress.md` — 开发进度与任务状态
- `memory/llm_api.md` — 国内 LLM 接入方案

## 环境注意事项
- matplotlib 需要 `matplotlib.use('Agg')` 避免 PyCharm backend 报错
- 图片必须保存到 `/Users/aijian/Downloads/Fast-F1/` 目录下
- FastF1 `circuit_info.corners['Distance']` 2026赛季全为 NaN，需等间距 fallback
- 遥测数据偶发截断（如 ANT 铃鹿最快圈），属 F1 官方 API 丢包，原样展示+注释
- `LapTime` 返回 timedelta，format 用自定义 `fmt_time()`，避免显示 "0 days"

## 技术栈决策
- 后端：Python FastAPI
- 数据：FastF1
- 前端：微信小程序原生 or uni-app（待定）
- 图表：ECharts for 小程序 (ec-canvas)
- AI 分析：规则引擎 → 国内免费 LLM（待选型，见 memory/llm_api.md）
- 缓存：本地文件缓存 / Redis

## 后端性能规范
- **慢接口首查**：有没有加服务端缓存？有没有串行 HTTP 请求可并行化？
- 缓存模板 + 并行请求模板见 `memory/architecture.md § 后端性能优化模式`
- standings.py 已落地：并行请求（ThreadPoolExecutor）+ 30min 内存缓存 + 去嵌套 iterrows

## 网络延迟规范
- 大陆→香港 TCP 握手本身 ~3s，代码再快也没用，需前端缓存兜底
- 前端缓存已在 `miniprogram/utils/api.js` 统一封装（stale-while-revalidate）
- 详细方案对比见 `memory/architecture.md § 网络性能优化方案`

## 当前阶段
**Phase 4：资讯+AI分析+论坛 — 已上线，持续优化中**
详见 memory/progress.md

## 微信小程序
- AppID: wx8198848f733aa5b2
- 框架: 原生小程序
- 图表: ECharts for 小程序 (ec-canvas)
- 前端目录: /Users/aijian/Downloads/Fast-F1/miniprogram/

## 服务器
- 地址：43.129.185.165（腾讯云香港）
- 服务：`sudo systemctl restart f1api`（WorkingDirectory: `/home/ubuntu/Fast-F1/backend/`）
- venv：`/home/ubuntu/Fast-F1/backend/venv/bin/python`
- 部署方式：rsync 本地 backend/ → 服务器，不覆盖 f1.db 和 cache/

## 新闻 AI 分析架构（最新）
- **输入**：trafilatura 抓全文（前 2000 字），失败降级用 RSS 摘要
- **积分 RAG**：仅含"积分/championship/standings"关键词的新闻才注入；不注入时 prompt 直接省略该段（不传任何提示，避免 AI 误说"数据待更新"）
- **输出格式**：🔬核心要点（必有）+ 🏎️通俗解释（技术类才有，AI 自判断）+ 📊赛况影响（必有）
- **重新分析**：`POST /news/{id}/analyze-public?force=true` 清旧记录后重跑；前端详情页有「🔄 重新分析」按钮

## 定时任务
- APScheduler 每小时爬取新闻（不分析）
- AI 分析严格由用户点击触发
- 关键：apscheduler 需装在服务器 venv 里，否则静默失败


## 已知坑（新增）

### ⚠️【ec-canvas "canvas node not found, res=[null]"】
回调里加 `wx.nextTick`，等一帧再查节点。文件：`ec-canvas.js` init 方法。

### ⚠️【ec-canvas onInit 为 null 导致图表不渲染】
凡是 ec-canvas 在条件块（wx:if/wx:else）内，必须用 `lazyLoad:true` + 手动 init。
文件：`telemetry.js`，详见 memory/architecture.md。

### ⚠️【AI 分析车手名幻觉（ANT→汉密尔顿）】
prompt 顶部加车手身份映射区块，从 FastF1 `s.results['FullName']` 取全名。
重新生成时删 `backend/cache/analysis/*.json`。

### ⚠️【apscheduler 未装到服务器 venv → 定时任务静默失败】
症状：journalctl 显示 `No module named 'apscheduler'`，scheduler 从未执行。
修复：`/home/ubuntu/Fast-F1/backend/venv/bin/pip install apscheduler==3.10.4`

### ⚠️【术语标签误打（管理新闻贴上"安全车"）】
`terms_by_news()` 原来搜索包含 AI 生成文本 → AI 泛泛提及的词被误打为标签。
修复：只对 `title+summary` 做匹配，不含 `tech_points/plain_explain/race_impact`。

### ⚠️【新闻分析 "数据待更新" 僵化输出】
原因：积分不注入时传了 "（本条新闻无需积分榜数据）" → AI 误判为数据不可用。
修复：不需注入时直接省略 prompt 中的积分段落（`standings_block = ""`），不传任何提示。

### ⚠️【服务器部署路径踩坑】
systemd 服务 WorkingDirectory = `/home/ubuntu/Fast-F1/backend/`（不是 f1api/）。
rsync 目标必须是 `ubuntu@43.129.185.165:/home/ubuntu/Fast-F1/backend/`。

### ⚠️【生产环境 DDL 迁移：旧表加列必须在索引之前】
`CREATE TABLE IF NOT EXISTS` 不会修改已有表结构。如果新 DDL 在已有表上加索引引用新列（如 `CREATE INDEX ON comments(parent_id)`），
`conn.executescript(DDL)` 会因 `no such column` 崩溃导致服务 502。
**修复**：在 `executescript(DDL)` 之前加 `ALTER TABLE` 兼容迁移。
参考 `init_db()` 中的 `parent_id` 兼容模式。

