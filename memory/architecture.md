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

## 网络性能优化方案（大陆→香港服务器延迟问题）

### 根因诊断（2026-04-21 实测）
```
DNS:     0.001s  ✅
TCP握手: 3.074s  ❌ 大陆→香港链路本身就慢
TTFB:    6.608s  ❌
Total:  22.474s  ❌（3.4KB 数据）
```
服务器本地测：首次 38ms，缓存命中 8ms。**代码没问题，是链路问题。**

### 方案对比

| 方案 | 效果 | 代价 | 状态 |
|---|---|---|---|
| 小程序前端本地缓存（wx.Storage）| 重复访问秒开，减少请求次数 | 实现简单 | ✅ 已落地 |
| 服务端内存缓存（TTL Cache）| 命中后服务器响应 <50ms | 已实现 | ✅ 已落地 |
| 大陆服务器 + ICP 备案 | 根治，延迟降到 <100ms | 备案周期 1-2 个月 | 待定 |
| 腾讯云 CDN 加速（国内节点）| 静态资源快，API 回源仍慢 | 成本低 | 待定 |
| WebSocket 长连接 | 复用 TCP，省掉每次 3s 握手 | 改造工程量中等 | 待定 |

### 前端缓存实现（stale-while-revalidate 模式）
已在 `miniprogram/utils/api.js` 统一封装，所有接口自动受益：

- 命中缓存 → 立即返回旧数据（秒开），同时后台静默刷新
- 未命中 → 正常请求，成功后写入缓存
- 各接口 TTL：standings/analysis=30min，events=1h，qualifying/laptimes/telemetry=10min

```js
// 核心逻辑（见 api.js cachedRequest）
const cached = cacheGet(key, ttl)
if (cached) {
  request(path, params).then(res => cacheSet(key, res)).catch(() => {})  // 后台刷新
  return Promise.resolve(cached)  // 立即返回
}
```

## 后端性能优化模式

### 1. 服务端内存缓存（TTL Cache）
适用场景：数据不需要实时刷新的接口（积分榜、赛历等）。

```python
import time

_cache: dict = {}
_CACHE_TTL = 1800  # 30 分钟

def _cache_get(key):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
    return None

def _cache_set(key, data):
    _cache[key] = (data, time.time())

# 在接口函数顶部：
cached = _cache_get(cache_key)
if cached is not None:
    return ok(cached)
# ...计算后：
_cache_set(cache_key, result)
```

命中缓存后响应 <50ms，已在 standings.py 中落地。

### 2. 并行 HTTP 请求（ThreadPoolExecutor）
适用场景：同一接口需要调多个独立外部 API（如 Ergast）。

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as ex:
    f1 = ex.submit(e.get_driver_standings, season=year)
    f2 = ex.submit(e.get_constructor_standings, season=year)
    f3 = ex.submit(e.get_race_results, season=year, result_type='driver')
    r1, r2, r3 = f1.result(), f2.result(), f3.result()
```

三个串行请求（~3s）→ 并行（~1s，取最慢者）。

### 3. 避免嵌套 iterrows 循环
反模式：5车手 × N轮 × iterrows → O(5·N·20) 次遍历。

正确做法：一次 pass 预计算 `{code: [pts_r1, pts_r2, ...]}` dict，再线性生成结果：

```python
pts_by_code = defaultdict(list)
for df_round in races_raw.content:
    code_pts = {row.get('driverCode',''): float(row.get('points',0))
                for _, row in df_round.iterrows()}
    for code in top5_codes:
        pts_by_code[code].append(code_pts.get(code, 0.0))
```

## 关键依赖版本（llm_eval_new 环境）
- fastf1: 最新（from 项目本地源码）
- Python: 3.11
- matplotlib: 新版（需 Agg backend）
- fastapi, uvicorn: 待安装
- openai: 待安装（用于调 DeepSeek）
