# AGENTS.md — F1 小程序项目开发规范

## 项目简介
F1 数据可视化微信小程序。FastF1 获取数据 → FastAPI 后端 → ECharts 前端 + AI 分析报告。
详细设计见 `F1_miniprogram_design.md`。

## 记忆文件（每次启动必读）
路径：`/Users/aijian/Downloads/Fast-F1/memory/`
- `MEMORY.md` — 索引，每次对话优先读此文件
- `progress.md` — 当前进度和任务状态
- `architecture.md` — 目录结构和数据格式
- `llm_api.md` — 国内 LLM 接入方案（DeepSeek）

## 开发规范

### Python 环境
```bash
/Users/aijian/anaconda3/envs/llm_eval_new/bin/python
```

### 已知坑（必须遵守）
1. matplotlib 必须加 `matplotlib.use('Agg')`，否则 PyCharm 下报 `tostring_rgb` 错
2. 图片/文件统一保存到 `/Users/aijian/Downloads/Fast-F1/` 目录下
3. `plt.show()` 禁止使用，统一用 `plt.close()`
4. FastF1 `pick_lap()` 已废弃，用 `laps[laps['LapNumber'] == n].iloc[0]`
5. `LapTime` 是 timedelta，显示用自定义 `fmt_time()`，不要直接 str()
6. `circuit_info.corners['Distance']` 2026赛季为 NaN，用等间距 fallback
7. 遥测截断属正常现象，在 API `note` 字段说明，不报错

### 代码风格
- 后端：FastAPI + Pydantic，接口统一返回 `{"status": "ok", "data": {}, "note": null}`
- 新功能先写到对应 router/service 文件，不要堆在 main.py
- 缓存目录：`backend/cache/`，FastF1 数据缓存在此

### AI 分析流程
规则引擎（Python 计算）→ 结构化 JSON 指标 → Prompt 模板 → DeepSeek API → Markdown 报告
不要把原始遥测数组传给 LLM，只传计算后的摘要指标。

## 迭代节奏【强制规则】
⚠️ 每完成一个步骤，立刻更新 `memory/progress.md`，不等对话结束。
⚠️ 不更新 progress 就继续下一步 = 违规。
上下文不足时，把重要结论写入对应 memory 文件，下次对话从 MEMORY.md 恢复。
