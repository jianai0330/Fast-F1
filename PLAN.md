# 执行计划

## Phase 0：基础设施（当前）

### 任务清单
- [x] FastF1 数据验证
- [x] 遥测对比脚本原型
- [x] 产品设计文档
- [x] 记忆体系（CLAUDE.md + memory/）
- [ ] **项目目录结构初始化**
- [ ] **安装后端依赖**（fastapi, uvicorn, openai）
- [ ] **DeepSeek API Key 申请**（用户操作）

---

## Phase 1：后端 API（遥测 + AI 分析）

### Step 1.1 — FastAPI 骨架
- `backend/main.py` 启动入口
- 统一返回格式 Pydantic 模型
- FastF1 cache 初始化

### Step 1.2 — 遥测接口
- `GET /telemetry?year=&round=&d1=&d2=&session=Q`
- FastF1 数据 → 清洗 → JSON
- 处理遥测截断、NaN、弯角距离 fallback

### Step 1.3 — 规则引擎
- 弯角分段：刹车点 / 最低速 / 出弯速
- 赛段时间差：S1 / S2 / S3
- 油门效率：全开时间占比 / 直线最高速
- 轮胎稳定性：圈时标准差 / 衰退斜率

### Step 1.4 — AI 分析接口
- `GET /analysis?year=&round=&d1=&d2=&session=Q`
- 规则引擎计算指标
- 拼 Prompt → DeepSeek API
- 缓存结果（避免重复调用）

### Step 1.5 — 其他接口
- `/qualifying` 排位赛结果
- `/laptimes` 正赛圈时
- `/standings` 积分榜
- `/events` 赛历

---

## Phase 2：微信小程序前端

### Step 2.1 — 框架搭建
- 选型确认（原生 / uni-app）
- ECharts ec-canvas 接入验证
- 全局样式、颜色体系（F1 暗色风格）

### Step 2.2 — 遥测对比页
- 车手选择器（含车队颜色）
- 4 联动子图（Speed / Throttle / Brake / Gear）
- 横轴弯角编号
- 圈时 + 差距显示

### Step 2.3 — AI 报告页
- Markdown 渲染组件
- 各维度折叠展开
- 数据不完整提示

### Step 2.4 — 其他页面
- 首页赛历
- 排位赛结果
- 圈时分析 + 轮胎策略
- 积分榜

---

## Phase 3：部署 & 上线

- 云服务器环境配置
- Nginx + uvicorn 部署
- 微信小程序审核
- 域名 HTTPS 配置

---

## 立即开始：Phase 0 剩余任务

```bash
# 1. 初始化项目目录
mkdir -p /Users/aijian/Downloads/Fast-F1/backend/{routers,services,models,cache}
mkdir -p /Users/aijian/Downloads/Fast-F1/miniprogram/{pages,components}

# 2. 安装后端依赖
/Users/aijian/anaconda3/envs/llm_eval_new/bin/pip install fastapi uvicorn openai pydantic scipy

# 3. 申请 DeepSeek API Key（用户手动）
# → https://platform.deepseek.com
```

下一步执行：Step 1.1 FastAPI 骨架搭建
