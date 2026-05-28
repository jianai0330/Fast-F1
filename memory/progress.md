# 开发进度

## 当前阶段：Phase 4 — 资讯+AI分析 & 论坛模块（进行中，2026-04-21 启动）

---

### 优化审查记录（2026-05-28）
- [x] 首页赛历第四轮回调已完成：根据用户反馈继续提高赛历主副信息字号，并增强赛道 SVG 的线宽与颜色对比度，提升滚动时的可读性与识别度。
- [x] 首页赛历第六轮回调已完成：赛道图改为统一画布中的居中缩放渲染，解决不同赛道线条粗细视觉不一致和位置偏移的问题。
- [x] 首页赛历第七轮回调已完成：继续下调赛道 SVG 固定线宽，避免小型赛道预览被过粗描边吞掉细节。
- [ ] 首页赛历第三轮回调：用户确认当前问题变成“赛道图显示不完整”和“赛历字号过小”；本轮优先恢复赛历卡片字号到接近初版，并修正赛道 SVG 的 viewBox 生成逻辑，确保整条赛道完整显示。
- [x] 首页赛道图渲染机制已切换：移除滚动列表中的异步 `canvas` 逐项绘制，改为在数据层预生成稳定 SVG 缩略图并随赛历项同步渲染，优先解决滚动时赛道图与对应卡片延迟、错位的问题。
- [x] 首页赛历第二轮回调已调整方向：保留赛历卡片中的赛道图功能，但不再采用右侧硬占位挤压文字区；改为更稳的卡片内嵌布局，优先保证标题/日期可读性，同时让赛道图作为辅助视觉存在。
- [x] 首页赛历第二轮回调已收敛：不再移除赛道图功能，改为恢复更舒适的赛历字号，并通过稳定图片渲染和更合理的卡片内布局解决错位与延迟问题。
- [x] 首页赛历布局第一轮修正已落地：压缩标题、倒计时、赛季摘要、最近一站和快捷入口的垂直占用；赛历列表卡片改为更紧凑密度，并为文字区/赛道图加上更严格的宽度与收缩约束，优先解决“小屏下赛历被挤下去”和“右侧赛道图错位”的问题。
- [ ] 首页赛历布局回调修正：用户实机反馈首页驾驶舱区块过高、压缩赛历可视面积，且小屏下倒计时/状态与赛道图存在右侧挤压错位；本轮优先压缩顶部模块高度并修正赛历卡片布局约束。
- [ ] Phase 4 AI 复盘承接面启动：下一步优先升级 `analysis` 页的信息结构与视觉层次，把当前折叠内容页推进为更像“专业比赛复盘报告”的展示形态。
- [x] Phase 2 / 3 视觉语言升级启动：全局按钮与卡片样式抬升到更高端的产品质感；`news` 页开始转向 editorial feed 排版；`event` 页新增赛事 Hero 头图层与更强 tab 视觉层级，逐步从“工具页”过渡到“专业内容页”。
- [x] Phase 2 首页驾驶舱第二步已落地：首页新增 4 个高频快捷入口（积分榜 / 资讯 / 词典 / 论坛），首页信息结构从“单一赛历列表”升级为“状态摘要 + 最近一站 + 高频动作 + 赛历流”。
- [ ] Phase 2 首页驾驶舱继续推进：在已完成的赛季摘要基础上，继续补强首页快速入口与信息导航；`term/glossary` 性能链路因混有历史未提交改动，先保留在工作区继续整理，不与首页这批安全提交混推。
- [x] Phase 1 第二批术语详情性能继续收敛：`term` 页在命中目录缓存后，当前术语、相关术语、辐射图节点和面包屑改为一次性组装并单次 `setData`，减少详情页切换时的重复渲染与多次桥接开销。
- [x] Phase 2 首页“比赛驾驶舱”第一步已落地：首页新增赛季摘要条（已完成/待进行/总分站）和最近一站卡片，提升信息层级；同时对赛道简笔图增加绘制签名拦截，避免重复 `canvas` 绘制造成的无效开销。
- [ ] 继续无中断优化：先收尾 Phase 1 第二批剩余的 `term/glossary` 详情缓存与重复渲染热点，再切入 Phase 2 首页“比赛驾驶舱”体验升级；提交仍按 path-limited 安全策略执行。
- [x] Phase 1 第二批第二步已落地：术语链路新增 `getTermsCatalog()` 轻缓存，`glossary` 改为优先复用全量术语目录缓存；`term` 详情页改为基于目录缓存本地拼装当前术语、相关术语与面包屑，显著减少碎片化详情请求。顺手补了 `news` 页搜索防抖定时器的 `onUnload` 清理，避免页面退出后残留触发刷新。
- [x] Phase 1 第二批第一步已落地：`telemetry` 页面新增图表数据降采样（默认压到约 420 点）以减轻 ECharts 渲染压力；术语查词从“页面进入即加载”改为“点击悬浮按钮后按需加载”，进一步缩短首屏初始化路径。
- [ ] 开始 Phase 1 第二批流畅度优化：优先处理 telemetry 图表数据降采样、术语页更轻量加载路径，并继续坚持 path-limited commit，避免把工作区内其他历史改动带入提交。
- [x] Git 提交事故补救：第二次本地 commit `Update project progress log` 因仓库已有大量 staged 文件，被意外带入 `.env`、缓存、数据库和运行态文件；已通过后续 commit `Remove runtime and sensitive files from tracking` 将这些文件从版本库索引移除，并保留本地文件不删除。
- [x] `jianai0330/Fast-F1` 已由用户创建：本地已按该仓库完成首次 commit 与 push。
- [x] 首次提交准备中：已仅 stage 本轮真实改动文件（流畅度优化、仓库治理、路线图），明确排除 `.env`、cache、数据库与其他运行态文件。
- [x] 已完成首次定向 commit：提交信息 `Improve app responsiveness and repo hygiene`，仅包含本轮明确处理的流畅度优化、仓库治理与路线图文件；其他已暂存运行态/历史文件保持未随本次 commit 提交。
- [ ] 尝试直接代建 GitHub 仓库：基于已打通的 `jianai0330` SSH 身份，通过本机浏览器检查 GitHub 登录态并创建 `jianai0330/Fast-F1` 空仓库，成功后再执行首次 commit/push。
- [ ] 开始为 GitHub 账号 `jianai0330` 生成专用 SSH key：本轮仅创建新 key，不修改现有 GitHub SSH 配置与仓库 remote；待用户把公钥加到 GitHub 后再切换。
- [x] 已生成 `jianai0330` 专用 SSH key：私钥 `~/.ssh/id_ed25519_jianai0330_github`，公钥 `~/.ssh/id_ed25519_jianai0330_github.pub`，指纹 `SHA256:ovEi4diccf+2FJTPhMOhrHBgyAYOnGKsZCSubdv94Ic`；待用户把公钥添加到 GitHub 账号 `jianai0330` 后，再修改 `~/.ssh/config` 与仓库 remote。
- [x] `jianai0330` SSH key 已添加到 GitHub：专用 SSH host 已写入并验证通过。
- [x] `jianai0330` SSH host 已切换到新 key，SSH 认证返回 `Hi jianai0330!`；当前仓库 remotes 已调整为 `origin=git@jianai0330:jianai0330/Fast-F1.git`、`upstream=git@github.com:theOehrly/Fast-F1.git`。验证发现 GitHub 上 `jianai0330/Fast-F1` 目前不存在，需创建后才能 push。
- [x] API 代建仓库账户边界已确认：命令行可用的 GitHub token 实际属于 `aijiangientech`，因此 API 建仓落在 `aijiangientech/Fast-F1`；最终已改由用户创建 `jianai0330/Fast-F1` 并成功接通 `origin/main`。
- [ ] GitHub 仓库接管检查：当前仓库 `origin` 指向 `git@github.com:theOehrly/Fast-F1.git`（上游仓库），本机未安装 `gh`；后续需改为用户自己的 GitHub 仓库再执行常规 commit/push 流程。
- [x] 本机 GitHub 身份核对完成：`~/.ssh/config` 中 `jianai0330`、`ajn2020`、`github.com-aijiangientech` 三个别名均可成功 SSH 认证到 GitHub 账号 `aijiangientech`；当前仓库本地 git 用户仍是 `aijian_max <ai.jian.gientech@outlook.com>`。
- [x] Git 身份配置已调整：全局个人身份改为 `aijian_mac <ai.jian.gientech@outlook.com>`；`/Users/aijian/Documents/company-repos/` 路径规则改为 `简爱 <p6063391@gientech.com>`；当前仓库本地 git 用户也已设置为 `简爱 <p6063391@gientech.com>`。
- [x] 当前仓库本地 git 身份已纠正回个人：`aijian_mac <ai.jian.gientech@outlook.com>`；经核对，GitHub 账号 `jianai0330` 与 `aijiangientech` 均存在，但本机现有 GitHub SSH key 当前都认证到了 `aijiangientech`。
- [ ] 开始 Phase 1 流畅度专项：优先处理 `telemetry/laptimes` 大对象移出 `setData`、event/standings 图表 lazy init、news/forum 脏标记刷新。
- [ ] 启动商用级产品升级规划：目标覆盖可视化、流畅度、功能、架构、竞品、商业化与合规；已派出 UI/性能审查 subagent 与商用架构审查 subagent，并开始竞品调研。
- [ ] 竞品调研初步结论：官方 F1 App/F1 TV 强在实时 live timing/driver tracker/多视角；民间产品 Formuletry/LumiLine/F101/F1Dash/Pitwall 强在 telemetry、race control、strategy、replay；本项目应主打中文数据解释、赛后复盘、AI 辅助理解与轻量社区。
- [ ] 合规调研初步结论：商用前必须处理 Formula 1 商标/结果与计时数据/AI 使用授权风险；产品应避免官方关联表达，商业化阶段需改用授权数据或明确限定为非官方学习/资讯工具。
- [ ] Subagent 审查完成：UI/性能侧确认大数组 `setData`、ec-canvas 条件渲染、onShow 过度刷新是流畅度核心瓶颈；架构侧确认任务队列、可观测性、安全鉴权、部署回滚、数据合规是商用核心缺口。
- [x] 已新增 `COMMERCIAL_ROADMAP.md`：沉淀商用级定位、竞品基准、体验框架、流畅度优化框架、工程治理框架、阶段计划与北极星指标。
- [x] Phase 1 第一批代码已落地：`telemetry` 遥测大对象移出 `setData`；`event` 正赛图与 `standings` 趋势图改为 `lazyLoad + 手动 init`；`news/forum` 改为基于脏标记的按需刷新；新闻列表点击改为只传 `id`，预览数据走 storage。
- [x] Phase 1 第一批验证完成：CommonJS 页面脚本 `node --check` 通过；本次改动文件 `git diff --check` 通过；残留旧字段引用（`raceChartInit/trendChartInit/laptimes` 等）已清理。ESM 语法文件因本机 Node 参数限制未做同方式检查。
- [ ] 已启动项目优化审查：完成记忆文件、项目结构和 git 工作区初扫；下一步检查后端路由/数据库/前端 API 封装，输出按优先级排序的优化建议。
- [ ] 已检查架构文档、`backend/main.py`、`miniprogram/utils/api.js`：发现前端缓存 key 缺年份、精选 API 方法重复定义、后台 token 硬编码、redirect 未限制目标域名等优化点。
- [ ] 已检查 `backend/db/database.py`、`backend/routers/forum.py`、`backend/routers/curated.py`、新闻/管理路由：确认全新数据库初始化、论坛分区热榜、精选 tags 格式不一致仍是优先修复项。
- [ ] 已用临时 fresh SQLite 复现 `init_db()` 失败：全新库初始化报 `no such table: sections`；`python -m compileall backend` 通过，当前主要是行为/架构优化而非语法错误。
- [x] 优化审查完成：已形成 P0/P1/P2 建议清单，建议先修数据库初始化、运行态文件入库、论坛热榜过滤、缓存 key、精选 tags、安全配置。
- [ ] 开始修复 P0/P1：按顺序处理 `init_db()`、论坛热榜分区过滤、前端年份缓存 key、精选 tags 格式、redirect 白名单与 API 重复定义。
- [x] 已修复 `backend/db/database.py:init_db()`：改用 `conn.executescript(DDL)`，避免注释导致建表语句被跳过；`idx_posts_curated` 改为兼容逻辑后统一创建。
- [x] 已修复论坛热榜分区过滤：`get_hot_posts()` 支持 `section_id`，`GET /forum/posts?sort=hot&section_id=...` 不再混入全站热门帖。
- [x] 已修复前端缓存 key：`getEvents()` / `getStandings()` 缓存 key 加入年份，避免切换赛季读取旧缓存；同时清理 `submitCurated/getCuratedDetail` 重复定义。
- [x] 已修复精选手动投稿：`tags` 统一保存为 JSON 字符串；空 URL 改为按标题+摘要生成稳定 `manual://` 去重键，避免所有手动投稿共用空字符串 URL。
- [x] 已修复 `/redirect` 开放跳转风险：限制 scheme 为 `http/https`，目标 host 必须在新闻来源白名单内。
- [x] 已更新 `.gitignore`：修复 `.DS_Store.env` typo，并补充 `cache/`、`backend/db/*.db*`、`backend/static/covers/` 等运行态文件忽略规则；未自动取消已暂存文件。
- [x] 验证：`python -m compileall backend` 通过；fresh SQLite 初始化通过（核心表齐全，sections=35，terms=105）；论坛热榜分区过滤脚本通过；`node --check miniprogram/utils/api.js` 通过；本次触碰文件 `git diff --check` 通过。
- [x] 环境修复：已在 `/Users/aijian/anaconda3/envs/llm_eval_new/` 安装 `beautifulsoup4==4.13.4`（含 `soupsieve`），使本地环境与 `backend/requirements.txt` 对齐。
- [x] 补充验证：`backend/main.py` 可导入；`/redirect` 白名单域名返回 302，非白名单域名返回 400；精选投稿 tags JSON 序列化路径验证通过。

### Bug 审查记录（2026-05-13）
- [ ] `backend/db/database.py:init_db()` 全新数据库初始化失败：DDL 分号切分后跳过以注释开头的建表语句，临时 fresh.db 复现为 `no such table: sections`
- [ ] `backend/routers/forum.py` 热门排序忽略 `section_id`：分区页 hot 模式会混入全站热门帖
- [ ] 精选内容手动投稿 tags 格式不一致：`submit_manual()` 写逗号字符串，详情页按 JSON 解析，标签显示/筛选会失效
- [ ] `miniprogram/utils/api.js` events/standings 缓存 key 未包含 year，切换年份时可能读到旧年份缓存

### 已完成

#### Phase 1-2 基础功能
- [x] 后端全接口联调
- [x] 小程序骨架（首页/赛事详情/遥测/AI分析/积分榜）
- [x] 真机/开发者工具联调成功（IP: 192.168.84.140）
- [x] ECharts 遥测页4个 tab（单 canvas 复用）
- [x] 正赛圈时 ECharts 折线图（event 页 race tab）
- [x] 积分榜页面（standings）
- [x] 车手选择改为 Picker 滑动选择

#### Phase 3 云端部署
- [x] 购买腾讯云香港轻量服务器（IP: 43.129.185.165）✅ 2026-04-10
- [x] SSH 公钥配置成功（ubuntu@43.129.185.165 可连通）✅ 2026-04-10
- [x] 后端代码上传并部署到云服务器 ✅ 2026-04-10
  - systemd 守护进程（f1api.service），开机自启
  - http://43.129.185.165:8000 外网可访问
- [x] BASE_URL 切换为线上地址 ✅ 2026-04-10

#### Phase 3 UI 品质提升
- [x] 遥测页弯角标注颜色修复（markLine #333→#555，label #555→#aaa）✅ 2026-04-13
- [x] 正赛页面全面重设计 ✅ 2026-04-13
  - 上半：名次变化折线图（Y轴翻转，P1在顶，进站圈标圆点）
  - 中：车手选择徽章面板（默认前3，点击切换）
  - 下半：每车手数据卡片（排名/最快圈/进站次/轮胎策略横条）
  - 后端 laptimes 接口新增 position、summary 字段
- [x] 正赛图例条修复 ✅ 2026-04-13
  - 删除错误的轮胎颜色徽章（S/M/H/I）和"轮胎颜色图例"文字
  - 名次变化图只用车手颜色区分，无轮胎颜色，图例改为"线色=车手  ○=进站圈  P1在顶"说明
  - 同步清理 wxss 中废弃的 .tyre-badge / .tyre-label 样式
- [x] Tab 栏吸顶 ✅ 2026-04-13
  - .container 改为 height:100vh flex列方向，tab-bar flex-shrink:0
  - 内容区改用 scroll-view.content-scroll（flex:1，scroll-y）承载，tab-bar 始终置顶
- [x] 正赛名次图优化 ✅ 2026-04-13
  - Y轴去掉刻度标签（axisLabel: show:false），左侧grid从36→8，图表更宽
  - Y轴范围自动贴合所选车手实际名次区间（±0.6 padding），不再写死1-20
  - 每条线右端 endLabel 直接标注"车手码\nP名次"，颜色跟线一致，替代Y轴标签
  - 进站圈空心圆点 borderWidth 1.5，视觉更精致

---

### Phase 4 进行中（资讯 + 论坛）

#### Phase E：Bug 修复（2026-04-23）
- [x] 分析缓存强制刷新 ✅
  - 后端 `analysis.py` 加 `force: bool = False` 参数，force=True 时跳过缓存重新生成
  - 前端 `onRefresh()` 改为 `loadAnalysis(true)`，同时清除本地 Storage 缓存
  - `api.js` `getAnalysis` 加 `force` 参数支持
- [x] 资讯来源名显示修复 ✅
  - `news.wxs` / `news-detail.wxs` 加 `source()` 格式化函数
  - "Motorsport.com" → "Motorsport"，其他来源同理
  - `news.wxml` / `news-detail.wxml` 改用 `fmt.source(item.source)`
- [x] 车手评分接入后端 ✅
  - 数据库加 `driver_ratings` 表（每人每车手唯一，可更新）
  - `database.py` 加 `driver_rating_upsert / get_mine / aggregate` 三个函数
  - `driver.py` 加 `GET /driver/{code}/rating` 和 `POST /driver/{code}/rating` 接口
  - `api.js` 加 `getDriverRating / postDriverRating`
  - `driver.js` 评分逻辑全部改为调用后端，`_renderCommunity` 适配新 agg 格式
  - 本地 `init_db()` 已执行，`driver_ratings` 表已创建
- [x] 后端 `GET /events/{round}/circuit` 接口 ✅ 2026-04-22
  - CIRCUIT_INFO 静态数据覆盖 2026 赛历全部站点
  - 字段：name_cn / length_km / laps / turns / drs_zones / type / direction / first_gp / lap_record / highlights / tyre_strategy / weather
- [x] 前端 event 页新增"赛道信息" tab（排位赛左边，默认选中）✅ 2026-04-22
  - 基础参数卡片（长度/圈数/弯角/DRS）
  - 最快圈记录（大字时间 + 车手 + 年份）
  - 赛道特点标签 + 赛道亮点列表
  - 轮胎策略 + 天气说明
  - tab 字号缩小至 22rpx 适配 4 个 tab
- [x] Bug 修复 ✅ 2026-04-22
  - `api(...)` 误当函数调用 → 改为 `api.getCircuit(year, round)`，api.js 新增该方法
  - `onLoad` 中 `setData` 异步导致 round=null → 直接将 round/year 传参给 loadCircuit
  - 云服务器未同步新代码 → rsync 推送 events.py 并重启服务
  - terms 表缺 status/submitted_by 列 → ALTER TABLE 补列（本地 db）

#### Phase A：基础设施（两模块公用）
- [x] 建 SQLite 数据库层 `backend/db/database.py` ✅ 2026-04-21
  - 表：news / news_analysis / sections / users / posts / comments
  - 默认分区：24个赛事分区 + 10个车队分区 + 综合讨论
  - 封装全部 CRUD 函数（news_insert/list/get、post_create/list/get、comment_*、user_upsert 等）
- [x] 在 main.py 注册新路由（news / forum / admin）+ 启动时 init_db() ✅ 2026-04-21

#### Phase B：资讯 + AI 专业分析
- [x] RSS 爬虫 `backend/services/news_crawler.py` ✅ 2026-04-21
  - 支持 The Race + Motorsport.com 两个 RSS 源
  - 去重（url UNIQUE）、feedparser 解析、httpx 兜底
- [x] 资讯 API `backend/routers/news.py` ✅ 2026-04-21
  - GET /news（分页）、GET /news/{id}、POST /news/crawl、POST /news/{id}/analyze
- [x] AI 分析服务 `backend/services/news_analyzer.py` ✅ 2026-04-21
  - DeepSeek API 三段式分析（🔬技术要点 / 🏎️通俗解释 / 📊赛况影响）
  - 分析完自动作为种子帖同步至对应论坛分区（is_seeded=True，status=approved）
- [x] 前端资讯列表页 `miniprogram/pages/news/` ✅ 2026-04-21
- [x] 前端资讯详情页 `miniprogram/pages/news-detail/` ✅ 2026-04-21
  - 3s 轮询等待 AI 分析，最多 10 次；骨架屏过渡

#### Phase C：论坛
- [x] 论坛用户接口（注册昵称）✅ 2026-04-21
  - POST /forum/users/register（wx.login code → openid → upsert user）
- [x] 论坛帖子接口 ✅ 2026-04-21
  - GET/POST /forum/posts，GET /forum/posts/{id}
- [x] 评论接口 ✅ 2026-04-21
  - GET/POST /forum/posts/{id}/comments
- [x] 管理员审核接口 `backend/routers/admin.py` ✅ 2026-04-21
  - X-Admin-Token 鉴权；approve/reject posts & comments；触发爬取+分析
- [x] AI 种子内容自动同步到论坛 ✅ 2026-04-21
  - news_analyzer.py 分析后调用 _seed_to_forum()，ai_bot 身份直接 approved
- [x] 前端论坛页面 `miniprogram/pages/forum*/` ✅ 2026-04-21
  - forum/（赛事/车队 Tab 分区入口）
  - forum-section/（分区帖子列表 + FAB 发帖）
  - forum-post/（帖子详情 + 评论 + 底部输入栏）
  - forum-create/（发帖表单，字数统计）
  - forum-register/（昵称注册，wx.login 换 openid）
- [x] 前端审核后台页 `miniprogram/pages/admin/` ✅ 2026-04-21
  - 长按🔒解锁，showModal 输入密码
  - Tab 切换帖子/评论审核，一键爬取+AI分析
- [x] `miniprogram/utils/api.js` 新增所有 API 方法 ✅ 2026-04-21
  - POST 封装、admin header 注入、news/forum/admin 全部接口
- [x] `miniprogram/app.json` 注册所有新页面 + tabBar 加资讯/论坛 ✅ 2026-04-21

#### Phase D：新闻↔论坛联动 + 互动功能
- [x] 新闻详情页底部「讨论区」模块 ✅ 2026-04-21
  - 展示关联帖子（最多3条）+ 「查看全部」+ 「去论坛讨论」红色按钮
  - onShow 钩子：从 forum-create 返回后自动刷新关联帖子列表（实时可见新帖）
- [x] 引用功能（新闻→论坛）✅ 2026-04-21
  - AI 分析各段落右端「💬 引用到讨论」按钮
  - 内容通过 wx.setStorageSync('f1_pending_quote') 传递（避免 URL 长度限制）
  - forum-create 读取后展示蓝色引用卡片（background:#0d1f33，border-left:#4a9eff）
  - 正文预填 `> ${quote}\n\n`，读取后立即清除 Storage
- [x] 帖子详情页来源新闻卡片 ✅ 2026-04-21
  - 顶部展示来源新闻标题/来源，点击跳转新闻详情
- [x] 点赞/点踩功能 ✅ 2026-04-21
  - 同类型再点=取消，切换类型=直接替换
  - 数据库 post_likes 表（UNIQUE post_id+openid）
  - 前端乐观更新，视觉区分已投票状态（.voted / .voted-down）
- [x] 作者删帖功能 ✅ 2026-04-21
  - 仅作者可见删除按钮，showModal 二次确认
  - 后端级联删除 comments + post_likes，再删 post（避免 FK 约束报错）
- [x] 评论乐观更新 ✅ 2026-04-21
  - 提交成功后立即本地插入评论，1s 后静默刷新服务端数据
- [x] RSS 爬虫扩展 ✅ 2026-04-21
  - 新增 Crash.net + F1i.com 两个技术向 RSS 源
  - 修复摘要末尾「keep reading / read more」等截断词（正则清理）
  - 手动执行 Python 脚本清理服务器上已有的 50 条旧摘要
- [x] AI 分析 RAG 增强 ✅ 2026-04-21
  - 关键词检测（standings/积分/championship 等）→ 选择性注入 Ergast 实时积分数据
  - 2026 赛季车手阵容注入 prompt，禁止引用历史赛季数据
  - temperature 从 0.6 降至 0.4

---

### 暂缓（等功能开发完再做）

- [ ] ~~HTTPS 配置（域名 + Let's Encrypt + Nginx，微信小程序正式版必须）~~ ✅ 已完成（2026-04-22）
  - 域名：aifuwan.site，API 地址：https://api.aifuwan.site
  - Nginx 反向代理 + Let's Encrypt 证书（自动续期）
  - 微信公众平台合法域名已配置
  - app.js BASE_URL 已更新

#### Phase 3 性能优化
- [x] 前端本地缓存（stale-while-revalidate）✅ 2026-04-21
  - api.js 统一封装 cachedRequest，所有接口自动受益
  - standings/analysis=30min，events=1h，qualifying/laptimes/telemetry=10min
  - standings.js 改为"有缓存不显示 loading"，首次打开秒出旧数据
  - 三个 Ergast API 请求改为 ThreadPoolExecutor 并行拉取
  - 添加服务端内存缓存（TTL=30min），命中缓存后响应 <50ms
  - 修复 driver_trend 三层嵌套循环 → 一次 pass 预计算
  - 申请域名 or 自签证书
  - 配置 nginx 反向代理 + Let's Encrypt 证书
  - 在微信公众平台配置合法域名

---

#### Phase E：知识标签 + 概念卡片（P1-2）
- [x] 后端 `terms` 表 + 15条种子术语（基础/进阶/高阶各5个）✅ 2026-04-22
  - 基础：drs / sc / vsc / dnf / pit_stop
  - 进阶：undercut / overcut / graining / deg / parc_ferme
  - 高阶：boost_limit / mgu_k / torque_limit / porpoising / ground_effect
- [x] `terms_by_news()` 全文匹配（title+summary+AI分析 vs aliases）✅ 2026-04-22
- [x] 新路由 `routers/terms.py`（GET /terms、/terms/{slug}、/terms/news/{news_id}）✅ 2026-04-22
- [x] 新闻详情页横向术语标签栏（category 颜色区分）✅ 2026-04-22
- [x] 点击标签弹出底部卡片（short_def + full_def + example + 跳转按钮）✅ 2026-04-22
- [x] 新页面 `pages/term/term`：完整术语详情页（别名/解释/案例/相关术语）✅ 2026-04-22

#### Phase F：车队标签 + pole/podium 术语（2026-04-22）
- [x] 术语库新增 `pole`（杆位）和 `podium`（领奖台）两条 level=1 种子词 ✅
- [x] `terms_by_news()` 英文词边界匹配修复（`\b...\b`），避免 "ers" 误中 "drivers" ✅
- [x] ERS aliases 删除 "energy recovery"（过宽，误匹配太多文章）✅
- [x] 后端 `news.py` 新增 `GET /news/{id}/teams` 接口（实时匹配车队标签）✅
- [x] 后端 `news.py` `GET /news` 支持 `?team=xxx` 过滤参数 ✅
- [x] 后端 `database.py` 新增 `news_list_by_team()` 函数（LIKE 匹配 title+summary）✅
- [x] 前端 `api.js` 新增 `getTeamsByNews()`，`getNews()` 支持 team 参数 ✅
- [x] 前端 `news-detail` 标签栏：车队标签（方形，点击跳转筛选）+ 术语标签（圆形，点击弹卡片）并排显示 ✅
- [x] 前端 `news` 列表页支持车队筛选模式（标题变「法拉利 资讯」，右上角「← 全部」返回按钮）✅
- 💡按钮加脉冲光晕动画（roadmapGlow + iconBounce，每2.6s一次）
- "已上线"扩充至12条，含 RAG/SWR/APScheduler/规则引擎等技术细节
- 新增"🧠 AI 引擎进化"独立 section（紫色 #a78bfa），含 Skills约束/知识库/CoT/双通道
- "计划中"扩充至6条，含热力图/跨赛季/WebSocket/3D可视化

### 1.0 发布后持续优化（2026-04-22）

#### 新闻 AI 解读质量提升
- **术语标签误打修复** → `terms_by_news()` 改为只匹配 `title+summary`，不含 AI 生成文本；最多 3 个标签，level 低优先
- **AI 段落自适应** → 三段改为两段必填+一段条件：
  - 🔬 核心要点（必有）
  - 🏎️ 通俗解释（仅技术/规则类新闻，AI 自判断，人事/商业类省略）
  - 📊 赛况影响（必有，直接基于文章内容分析，不说"待更新"废话）
- **积分 RAG 改进** → 选择性注入保留（仅积分/排名相关新闻注入），但不注入时直接省略 prompt 段落，避免 AI 误判"数据不可用"
- **旧分析清空** → `DELETE /admin/analyses` 接口，清空后用新 prompt 重新生成
- **重新分析按钮** → 新闻详情页 AI 解读下方「🔄 重新分析」，Modal 二次确认，force=true 清旧记录后重跑

#### 新闻全文抓取
- **trafilatura** 加入依赖（v2.0.0），已安装到服务器 venv
- `analyze_one(url=)` 触发分析时先抓原文，截取前 2000 字送 AI
- 抓取失败自动降级用 RSS 摘要，不影响分析流程

#### 定时爬虫修复
- **根因**：`apscheduler` 未安装到服务器 venv，scheduler 启动静默失败，从未执行
- **修复**：`pip install apscheduler==3.10.4`，重启后确认每小时正常爬取
- **逻辑明确**：定时任务只爬取，**不自动分析**；AI 分析严格由用户点击触发

#### 新闻列表已解读状态同步
- `news.js` 加 `onShow` + `_syncAnalyzed()`：从详情页返回后静默刷新第一页，只更新各条 `analyzed` 字段，不重排列表

#### AI 年份认知加强（NEWS_SYSTEM）
- 加「时间认知」段：当前 2026年，2025赛季已结束
- 给出正/反例："此事件将影响2026赛季" vs "不会影响2025赛季（错误）"



---

## Bug 修复记录（1.0 上线前审查，2026-04-23）

### 前端修复
- **glossary.wxml 中英文字段显示反了** → `term-zh` class 改回显示 `name_en`（英文大字），`term-en` 改回显示 `name_zh`（中文小字），符合设计意图
- **glossary.js / news-detail.js 缺 `noop()` 函数** → 两个文件均补充 `noop() {}`，消除 `catchtap="noop"` 的 handler not found warning
- **news-detail.js `already_done` 逻辑死分支** → `_doRequest` 只在 `status=ok` 时 resolve，`already_done` 实际走 catch 导致报错。改为：触发成功直接开始轮询，catch 里直接 `loadDetail()` 刷新（覆盖已分析场景），逻辑正确
- **forum.wxml 帖子时间显示原始时间戳** → 新建 `pages/forum/forum.wxs`（复用 forum-post.wxs 的 `fmt.time` 逻辑），wxml 引入 wxs 并改为 `{{fmt.time(item.created_at)}}`

### 车手评论页修复（2026-04-23）
- **注册后仍跳注册页** → `driver.js` 读 Storage key 错误（`forum_openid` → `f1_openid`）；加 `onShow` 每次返回刷新登录状态
- **星星点击错行** → 嵌套 `wx:for` 内层覆盖外层 `index`；外层加 `wx:for-index="dimIdx"`，`data-dim` 改用 `dimIdx`
- **留言后不显示** → `onCommentSend` 里 `_loadComments` 未 `await`，改为 `await` 确保顺序执行
- **评论区用户/内容无区分** → 重构评论卡片：加头像圆圈（昵称首字）、昵称改红色、正文缩进对齐头像右侧

### 赛历未来赛事优化（2026-04-23）
- `index.js` 跳转带 `race_time_utc`；`event.js` 判断 `raceHappened`；排位赛/正赛/数据对比三个 tab 未发生时直接显示"尚未发生"，不发请求

### 车手数据更新（2026-04-23）
- VER: #1 → **#3**（2026赛季换号）
- NOR: #4 → **#1**（卫冕冠军）
- BOR: 错误数据（德国人 Börschke）→ **Gabriel Bortoleto**（巴西人，#5，麦克拉伦青训，2024 F2冠军）
- 后端 VALID_CODES 移除不在 2026 赛季的 MAG、DOO

---

## Bug 修复记录（2026-04-22）

### 1.0 发布前全面审查修复（2026-04-22）
- **api.js `adminRequest`/`adminPost` 未定义** → 改为 `request/post + adminHeader()`（管理员术语 tab 崩溃）
- **forum-section URL 参数错配** → `news-detail.js` onViewAllPosts 从 `sectionId/sectionName` 改为 `id/name`，与 forum-section.js 的 `options.id/name` 对齐
- **webview 页面不存在** → onOpenUrl 改为 `wx.setClipboardData` 复制链接
- **triggerLoading 永不重置** → onTriggerAnalyze `already_done` 分支补 `setData({ triggerLoading: false })`
- **admin.js added 计数错误** → 改为 `data.crawl?.added || data.added || 0`
- **forum-section 首次双重请求** → onShow 加 `!this.data.loading` 保护
- **news.js 死代码 getter** → 删除无效 `get itemsWithTime()`

### AI 分析报告车手名错误
- **现象**：ANT（安东内利）被 DeepSeek 幻觉成"汉密尔顿"
- **根因**：prompt 只传三字码，DeepSeek 不认识 2026 新车手
- **修复文件**：
  - `backend/routers/analysis.py`：从 `s.results['FullName']` 取全名
  - `backend/services/llm_client.py`：prompt 加车手身份区块 + metrics 三字码替换 + temperature 0.7→0.4
- **附操作**：清空 `backend/cache/analysis/*.json` 旧缓存

### ec-canvas "canvas node not found, res=[null]"
- **现象**：遥测页图表报错，图表不渲染
- **根因 1**：ec-canvas.js `setData({isUseNewCanvas}, cb)` 回调里渲染未完成，selector 返回 null
- **根因 2**：`loading:false` 和 `ecInit` 是两次 setData，canvas 挂载时 `onInit=null`
- **修复文件**：
  - `miniprogram/components/ec-canvas/ec-canvas.js`：回调里加 `wx.nextTick`
  - `miniprogram/pages/telemetry/telemetry.js`：改用 `lazyLoad:true` + 手动 init + `wx.nextTick`

---

## 微信小程序信息
- AppID: wx8198848f733aa5b2
- 前端目录: /Users/aijian/Downloads/Fast-F1/miniprogram/
- 后端地址（本地开发）: http://192.168.84.140:8000
- 后端地址（云服务器）: https://api.aifuwan.site ✅ HTTPS 已配置（2026-04-22）
- systemd 服务名：f1api.service
#### 性能优化（2026-04-23）
- [x] 后端启动时预热 events + standings 缓存（`_warmup_api_cache`，2s 延迟后执行）
- [x] standings 缓存 TTL 从 30min 提升到 2h
- [x] APScheduler 每 2h 自动刷新 standings 缓存（`standings_refresh` job）
- [x] 修复 main.py 中重复的 `/redirect` 路由定义

## 已知坑
- 开发者工具必须勾选「不校验合法域名」
- IP 换网络会变，改 app.js 里的 BASE_URL
- 所有 router 参数用 round_num，不用 round
- uvicorn 必须在 backend/ 目录下启动
- 腾讯云 Lighthouse Ubuntu 系统密钥绑定到 ubuntu 用户，不是 root
- ⚠️【ECharts Y轴标签消失】interval:1 时 min/max 必须是整数，浮点数（如0.4/8.6）会导致轴标签完全不渲染。正确做法：padding 用整数（posMin-1 / posMax+1），formatter 直接写 `val => \`P${val}\``
- ⚠️【ECharts 图表颜色随选择漂移】用排序索引 i 分配颜色时，不同选择组合导致同一车手颜色不一致。正确做法：建立车手三字码→颜色的固定映射表，未收录车手走 fallback 数组兜底
- 腾讯云防火墙添加自定义端口后，SSH 22 端口不会自动保留，必须手动添加 22 端口规则否则 SSH 断连
- FastF1 第一次请求某站数据很慢（需从 F1 官方下载），缓存后才快。上线前需把本地 cache/ 同步到服务器做预热：rsync -avz -e "ssh -i ~/.ssh/id_rsa" backend/cache/ ubuntu@43.129.185.165:~/Fast-F1/backend/cache/ --exclude 'analysis/'
- qualifying.py 的 Position 字段是 float64，NaN 车手（被淘汰/未参加）直接 int() 会崩，需用 row['Position'] == row['Position'] 判断非 NaN
- ⚠️【wx.redirectTo 跳转黑屏】`redirectTo` 会销毁当前页面，若目标页调用 `navigateBack()` 时页面栈只剩 1 层则黑屏。正确做法：凡是需要"返回继续"的场景（如登录注册插屏）一律用 `navigateTo`，并在原页面加 `onShow` 钩子重新读缓存恢复状态。兜底：注册页用 `getCurrentPages().length > 1` 判断，栈为空时改 `switchTab` 跳首页。
- ⚠️【tabBar 页面图标必须提前存在】`app.json` tabBar 里引用的 iconPath/selectedIconPath 若文件不存在，整个小程序编译失败、四个页面全空白。新增 tabBar 页时先用已有图标占位，再替换正式图。
- ⚠️【页面空白必查项】微信小程序 JS 文件中，`import` 必须放在 `require` 之前，同一文件不能混用 CommonJS/ESM（import 放首行，require 放后面）。违反此规则会导致整个页面 JS 加载失败、页面完全空白，且没有任何明显报错提示。
- ⚠️【rsync 同步前端样式不生效】rsync 路径必须精确到子目录，例如 `rsync ... miniprogram/pages/forum-create/forum-create.wxss ubuntu@host:/home/ubuntu/Fast-F1/miniprogram/pages/forum-create/`。若只写到 `miniprogram/` 根目录，文件会放错位置，开发者工具看到的还是旧样式。同步后前端样式无需重启服务，直接在开发者工具重新编译即可生效。
- ⚠️【SQLite 表结构迭代后旧 DB 缺列】DDL 用 `CREATE TABLE IF NOT EXISTS`，已存在的表不会自动加新列。新增字段后需手动 `ALTER TABLE posts ADD COLUMN news_id INTEGER`，否则 `post_get()` 的 JOIN SQL 报错，帖子加载失败。部署到云服务器时同样需要执行 ALTER。
- ⚠️【删帖按钮不显示 / openid 比较失败】原因：`onLoad` 先读 Storage 存 openid，再异步 `loadPost()`；若 Storage 为空（开发者工具清缓存编译），帖子加载完后 `post.author_openid` 有值但 `this.data.openid` 是空，`===` 比较失败，删除按钮不渲染。修法：在 `loadPost()` 完成时同步刷新 openid（在同一个 `setData` 里把 openid/nickname 一起更新），确保比较时机对齐。调试方法：Console 输入 `getCurrentPages().pop().data.openid` 和 `getCurrentPages().pop().data.post.author_openid` 对比两值。
- ⚠️【FastAPI 路由 prefix 重复】`APIRouter(prefix="/xxx")` + `app.include_router(..., prefix="/xxx")` 会导致路径变成 `/xxx/xxx/...`，所有接口 404。规范：router 文件里不设 prefix，统一在 main.py 的 include_router 里设置。部署后必须用 `/openapi.json` 或 curl 验证实际路径。
- ⚠️【删帖按钮不显示 / openid 比较失败】原因：`onLoad` 先读 Storage 存 openid，再异步 loadPost；loadPost 完成时 setData 只更新 post，不更新 openid，导致 `post.author_openid === openid` 比较时机错位。修法：在 loadPost 完成的 setData 里同时刷新 openid，确保两者在同一帧对齐。调试方法：Console 输入 `getCurrentPages().pop().data.openid` 和 `getCurrentPages().pop().data.post.author_openid` 对比。

#### Phase F：产品升级（2026-05-09）

##### F1 首页 TabBar 修复
- [x] tabBar 被赛历长列表挤到底部 → container 改 flex+100vh，赛历列表包在 scroll-view 内 ✅

##### 论坛分区热帖推荐
- [x] forum-section 顶部展示分区 Top 3 热帖卡片 ✅
  - 红色竖条 + 排名序号 + 标题/作者/评论数/浏览数
  - `wx:if="{{hotPosts.length >= 3}}"` 控制显示
  - 热帖独立于下方排序列表，onLoad 时加载一次

##### 中文资讯源
- [x] 资讯模块新增中文内容源 ✅
  - 爬虫改为网页爬取方式（RSS 源普遍失效）
  - 新浪体育 F1 可用（服务器在 HK，百度/腾讯不通）
  - news 表新增 language 字段，前端新增"全部/中文/English"筛选 Tab

##### AI 赛后分析质量升级
- [x] rule_engine.py 新增 `identify_key_laps` + `analyze_stint_degradation` 指标 ✅
- [x] llm_client.py Prompt 重写为叙事风格 ✅
  - 新格式：一句话结论 → 关键时刻 → 速度对比 → 轮胎与策略 → 总评
  - temperature 0.4→0.5，max_tokens 1500→2000

##### 内容投稿与精选系统
- [x] 数据库 `curated_content` 表 + CRUD 函数 ✅
- [x] 链接解析服务 `link_parser.py` ✅
  - 自动识别平台（微博/公众号/抖音/B站/网页）
  - OG 标签提取 + 平台适配（公众号正文快照+评论区抓取）
  - 封面图下载到服务器本地永久保存
- [x] 后端 API `routers/curated.py` ✅
  - POST /curated/submit（解析+入库）
  - GET /curated/list（分页+标签/关键词/平台过滤）
  - GET /curated/{id}（详情含快照）
  - GET /curated/tags
- [x] 前端资讯页“精选”Tab ✅
  - 主 Tab 切换（资讯/精选），左图右文卡片，平台色标
- [x] 投稿页 curated-submit ✅
  - 粘贴链接 + 标签选择 + 推荐语 + 昵称（缓存）
- [x] 详情页 curated-detail ✅
  - 封面大图 + rich-text 快照正文 + 复制原文链接
- [x] 静态文件服务挂载 /static ✅
- [x] 公众号链接测试通过（3条全部成功解析入库）✅

##### 快照与双模展示优化（2026-05-09）
- [x] Playwright 全页截图替代 HTML 快照 ✅
  - 3x 高清分辨率（device_scale_factor=3）
  - domcontentloaded + 滚动触发懒加载 + 5s 等待图片加载
  - 截图文件 2-3MB 高清效果
- [x] 详情页双视图切换开关 ✅
  - 🖼 截图（保真图片，人看）/ 📝 图文（HTML文本，机器可搜索/AI索引）
  - 两种数据永久保存，长远支撑知识库建设
- [x] 公众号 HTML 隐藏样式修复 ✅
  - 后端解析时 visibility:hidden→visible / opacity:0→1
  - 前端 stripScript 同样做替换处理
- [x] 精选内容在中文模式下以完整卡片展示 ✅
  - 无中文新闻时精选内容以 news-card 形式展示（不只是横滑小卡）

##### 投稿体验优化（2026-05-09）
- [x] 投稿后返回刷新精选列表 ✅
  - onShow 重新加载 curatedItems，提交后立即可见
- [x] 标签选择视觉反馈增强 ✅
  - 加大点击区域（padding 14rpx 28rpx）
  - 选中后红色高亮 + 边框 + 加粗 + scale(1.05)

##### 资讯页 Bug 修复（2026-05-09）
- [x] 中文页面进出后混入英文新闻 ✅
  - 根因：_syncAnalyzed() 调用 api.getNews(1) 未传 language 参数
  - 修复：加上 activeLanguage 和 teamFilter 参数

##### 论坛种子帖恢复（2026-05-09）
- [x] 数据库覆盖后重新生成 26 条 AI 种子帖 ✅
  - 覆盖多个分区（车队/赛事/综合讨论）
  - 每条含完整三段式 AI 分析

##### 精选内容 AI 解读（2026-05-09）
- [x] curated-detail 新增 AI 专业解读区 ✅
  - 三段卡片：📋事实摘要 / 🔍深度解读 / 💡我们的判断
  - 轮询等待 + 骨架屏动画
  - "生成 AI 解读"按钮 + "重新分析"按钮
  - 解读生成后所有人可见

##### AI 分析专业化升级（2026-05-09）
- [x] Agent Skills 体系建立 ✅
  - 5个专业技能 md：遥测对标/轮胎策略/扇区诊断/赛事叙事/新闻影响
  - 路径：`.qoder/skills/f1-*.md`，既指导开发也被生产 LLM 动态调用
- [x] 领域知识库 `backend/knowledge/` ✅
  - tracks/：24条赛道特性（扇区类型/DRS/退化等级/进站损失）
  - reference_data/：轮胎参数 + 燃油修正 + DRS效果
  - decision_rules/：策略判定规则
  - analysis_templates/：遥测/退化/策略分析模板
  - gotchas/：常见分析错误安全网
- [x] 知识库动态加载 `backend/services/knowledge_loader.py` ✅
  - 按赛道名匹配赛道特性
  - 按 session 类型 + 赛道类型选择方法论章节
  - 从 Skills md 提取对应章节注入 Prompt（≤2000字）
- [x] LLM Prompt 重构 `backend/services/llm_client.py` ✅
  - SYSTEM_PROMPT：三层递进框架 + 势能因素归因 + 置信度规范 + 2个few-shot范例
  - 知识块动态注入到 system 消息末尾
  - max_tokens 2000→3000
- [x] 规则引擎大幅增强 `backend/services/rule_engine.py` ✅
  - 7种关键时刻分类（pit_undercut/overcut/tire_cliff/safety_car/drs_boost/pace/rain）
  - 动态弯角选择（阈值=max(2, 中位数*0.3)，返回8-10个）
  - 轮胎悬崖检测（连续3圈退化加速）
  - 理想圈计算（各扇区最佳组合）
  - 燃油修正配速
- [x] 新闻分析递进式三段重构 ✅
  - 「核心要点/通俗解释/赛况影响」→「📋事实摘要/🔍深度解读/💡我们的判断」
  - 第二段改为机制分析（所有新闻都有内容）
  - 第三段要求明确立场 + 量化预测 + 置信度 + 验证条件
- [x] 数据来源标注规范 ✅
  - [原文]：新闻明确提到的数据
  - [推算]：基于原文的推导（附逻辑）
  - 无数据时用定性描述，禁止编造精确数字
- [x] 专业性展示重构：徽章标签→方法论面板 ✅
  - analysis 和 news-detail 页面均改为"查看分析方法论"按钮
  - 点击展开详细面板：方法论体系/知识库/数据管线
  - 展示5套方法论 + 激活状态 + 9个知识库 + 4步处理管线

#### Phase 5 词典界面专业化优化 ✅ 2026-05-09

**后端数据层扩展**
- [x] terms 表新增字段：scene_tags / why_important / data_ref ✅
- [x] 分类重组：flag 合并到 rules，新增 driving（驾驶技术）分类 ✅
- [x] 新增 GET /terms/hot 接口（近7天术语在新闻中匹配次数统计，缓存1小时）✅
- [x] 新增 GET /terms/popular 接口（热度TOP5术语列表）✅
- [x] 列表接口支持 scene 查询参数过滤 ✅
- [x] ALTER TABLE 自动兼容旧数据库（try/except 模式）✅

**种子数据大幅扩充**
- [x] 从 26 条扩充到 105 条高质量术语（联网调研+结构化整理）✅
- [x] 新增驾驶技术类 10 条（trail_braking/divebomb/switchback/slipstream 等）✅
- [x] 新增策略类 9 条、空气动力 4 条、轮胎 7 条、规则 4 条、动力单元 4 条 ✅
- [x] 所有术语补充 scene_tags / why_important / data_ref 字段 ✅
- [x] related_slugs 完整性验证：修复 3 处无效引用（power_unit/concorde_agreement）✅

**词典列表页 UI 增强**
- [x] 双视图切换：技术分类 ⇄ 场景分类（比赛常用/解说热词/2026必知）✅
- [x] 卡片增强：难度星级（★★★）+ 2026 NEW 红色角标 + 热度进度条 ✅
- [x] 本周热词横向滚动卡片区（TOP3，热度为空时隐藏）✅
- [x] 搜索聚焦面板：热门术语 TOP5 + 最近查看 ✅
- [x] 搜索联想：实时匹配 aliases，格式「关键词→术语名」✅

**术语详情页增强**
- [x] 新增「为什么重要」+「数据参考」内容区 ✅
- [x] 术语关系辐射图（CSS 圆形分布，替代旧列表，可点击跳转）✅
- [x] 浏览面包屑导航（from_slug 参数传递，最多3层回溯）✅
- [x] 最近查看记录持久化（storage，FIFO 10 条）✅

**全局悬浮查词按钮**
- [x] 遥测/分析/赛事详情 3 个页面添加可拖拽悬浮「?」按钮 ✅
- [x] 底部 Sheet 快速搜索：实时匹配 + 热门术语 + 跳转详情 ✅

**部署与修复**
- [x] 后端代码 rsync 同步 + 服务重启 + 种子数据重灌（清空→105条）✅
- [x] 修复 curated_id 索引在旧数据库创建失败的问题 ✅
- [x] 修复 related_slugs 中 power_unit/concorde_agreement 无效引用（本地+线上）✅
- [x] API 验证全部通过：/terms(105条) /terms/hot(16条) /terms/popular /terms?scene=2026_new(14条) ✅

#### 后端容错与部署安全 ✅ 2026-05-09

**数据缺失友好提示**
- [x] fastf1_service.py：session.load() 加 try-except，新增 check_laps_available() 工具函数 ✅
- [x] laptimes.py / telemetry.py：laps 数据不可用时返回中文友好提示而非崩溃 ✅
- [x] 前端 event.js：loadLaptimes() / loadQualifying() 的 catch 块改为展示后端返回的具体错误消息 ✅

**部署安全防护（防止数据库丢失）**
- [x] init_db() 改为逐条执行 DDL + 容错，schema 不兼容时不再导致整库重建 ✅
- [x] 新建 deploy.sh 部署脚本：部署前自动备份服务器 f1.db，再 rsync + restart ✅

---

## 2026-05-28

- 首页赛历第五轮回调完成：进一步增大赛历卡片标题、副信息与回合角标字号，并扩大右侧赛道图尺寸。
- 首页赛道 SVG 继续提亮并加粗线条，当前改为更亮的红色和更高的线宽，提升滚动时的可识别性。
- 首页赛道缩略图渲染继续校正：所有赛道 path 统一映射到固定 SVG 画布中，按比例缩放并自动居中，避免不同分站预览图出现忽粗忽细或靠边漂移。
- 首页赛道线稿继续微调：固定描边宽度从 3.8 下调到 2.8，并维持较亮红色，优先保留 Monaco、Barcelona 这类紧凑赛道的轮廓细节。

## 启动命令（本地）
```bash
lsof -ti:8000 | xargs kill -9 2>/dev/null
cd /Users/aijian/Downloads/Fast-F1/backend
/Users/aijian/anaconda3/envs/llm_eval_new/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 部署命令（推送到云服务器）
```bash
cd /Users/aijian/Downloads/Fast-F1/backend
./deploy.sh
# 自动执行：备份数据库 → rsync同步代码 → 重启f1api服务
```

## 启动命令（云服务器）
```bash
ssh ubuntu@43.129.185.165
sudo systemctl restart f1api   # 重启服务
sudo systemctl status f1api    # 查看状态
```
