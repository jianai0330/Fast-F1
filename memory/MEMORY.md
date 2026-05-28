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

## 当前阶段
**阶段 0：基础设施** — 正在进行
详见 memory/progress.md
