# 技术架构详细笔记

## 目录结构（目标）
```
Fast-F1/
├── backend/                    # FastAPI 后端
│   ├── main.py                 # FastAPI 入口
│   ├── routers/
│   │   ├── telemetry.py        # 遥测对比接口
│   │   ├── laptimes.py         # 圈时分析接口
│   │   ├── qualifying.py       # 排位赛结果接口
│   │   ├── standings.py        # 积分榜接口
│   │   └── analysis.py         # AI 分析接口
│   ├── services/
│   │   ├── fastf1_service.py   # FastF1 数据获取封装
│   │   ├── rule_engine.py      # 规则引擎（弯角/赛段/油门/轮胎计算）
│   │   └── llm_client.py       # LLM API 调用（DeepSeek）
│   ├── models/                 # Pydantic 数据模型
│   └── cache/                  # FastF1 本地缓存目录
│
├── miniprogram/               # 微信小程序前端
│   ├── pages/
│   │   ├── index/             # 首页（赛历）
│   │   ├── event/             # 赛事详情
│   │   ├── telemetry/         # 遥测对比
│   │   ├── laptimes/          # 圈时分析
│   │   └── standings/         # 积分榜
│   └── components/
│       ├── echarts/           # ec-canvas 封装
│       └── ai-report/         # AI 报告 Markdown 渲染
│
├── memory/                    # Claude 记忆文件（本目录）
├── F1_miniprogram_design.md   # 产品设计文档
└── fastf1/                    # FastF1 库源码（已有）
```

## API 数据格式

### 遥测接口返回
```json
{
  "status": "ok",
  "data": {
    "driver_a": {"code": "ALB", "team": "Williams", "color": "#005AFF", "lap_time": "1:28.123"},
    "driver_b": {"code": "ALO", "team": "Aston Martin", "color": "#00665F", "lap_time": "1:28.456"},
    "gap": "+0.333s (ALB faster)",
    "corners": ["T1","T2",...,"T18"],
    "corner_distances": [0, 320, 650, ...],
    "telemetry": {
      "ALB": {"distance": [...], "speed": [...], "throttle": [...], "brake": [...], "gear": [...]},
      "ALO": {"distance": [...], "speed": [...], "throttle": [...], "brake": [...], "gear": [...]}
    },
    "note": null
  }
}
```

### AI 分析接口返回
```json
{
  "status": "ok",
  "data": {
    "metrics": {
      "corners": [...],
      "sectors": {...},
      "straights": {...},
      "tyre": {...}
    },
    "report": "## 总体结论\n...",
    "cached": false
  }
}
```

## 规则引擎核心逻辑

### 弯角分段
- 以每个弯角前 50m 到弯角后 50m 为窗口
- 计算：刹车点（Brake=True 的第一个点）、最低速（Speed min）、出弯速（弯角后 50m 的 Speed max）

### 赛段时间差
- 用 FastF1 的 Sector 时间字段（LapData 里有 S1/S2/S3）
- 直接对比两车各赛段时间

### 油门效率
- `Throttle > 98` 的时间占总圈时百分比
- 直线段（Speed > 250km/h）最高速对比

### 轮胎稳定性
- 取车手连续 stint 的圈时序列
- 用线性回归拟合衰退斜率（slope）
- 圈时标准差

## 关键依赖版本（llm_eval_new 环境）
- fastf1: 最新（from 项目本地源码）
- Python: 3.11
- matplotlib: 新版（需 Agg backend）
- fastapi, uvicorn: 待安装
- openai: 待安装（用于调 DeepSeek）
