# F1 轮胎与策略分析技能 (Tire & Strategy Analysis)

## 元信息

- **技能ID**: f1-tire-strategy
- **版本**: 1.0.0
- **适用场景**: 正赛轮胎退化分析、进站策略评估、安全车策略决策、比赛策略复盘
- **前置依赖**: 圈时数据、轮胎配方记录、进站数据、赛道位置数据
- **核心方法论**: 退化模型建立 → Undercut/Overcut判定 → 进站窗口计算 → 策略格局影响

---

## 1. 轮胎性能三阶段模型

### 1.1 热身期 (Warm-up Phase)

**定义**：新胎安装后至达到最佳工作温度的时间段。

| 参数 | 硬胎 | 中性胎 | 软胎 |
|------|------|--------|------|
| 热身圈数 | 3-5圈 | 2-3圈 | 1-2圈 |
| 目标温度 | 95-105°C | 100-110°C | 105-115°C |
| 热身期圈时损失 | 0.3-0.8s | 0.2-0.5s | 0.1-0.3s |

**关键特征**：
- 温度上升曲线为指数型：`T(t) = T_target × (1 - e^(-t/τ))`
- 轮胎表面温度先达标，胎体温度滞后2-3圈
- 热身期间操控性不稳定——车手反馈"前/后端没有信心"
- 2026新规：更宽的轮胎工作温度窗口使得热身期影响可能降低

**分析注意事项**：
- 出站圈前2圈不做退化分析
- 热身期的圈时改善不应与"赛道进化"混淆
- 轮胎保温毯温度影响热身长度：2026赛季保温毯可能进一步限制

### 1.2 稳定期 (Optimal Phase)

**定义**：轮胎在最佳工作温度窗口内的性能阶段。

| 参数 | 硬胎 | 中性胎 | 软胎 |
|------|------|--------|------|
| 典型持续圈数 | 15-25圈 | 10-18圈 | 5-10圈 |
| 圈时波动范围 | ±0.15s | ±0.20s | ±0.25s |
| 退化率 | 0.01-0.03s/圈 | 0.02-0.04s/圈 | 0.03-0.06s/圈 |

**关键特征**：
- 圈时在该阶段呈缓慢线性退化
- 横向抓地力缓慢下降，纵向抓地力基本稳定
- 胎面磨损均匀——如果某侧磨损过快说明悬挂几何需调整
- 稳定期长度高度依赖赛道：高能量赛道（Suzuka）退化快，低能量赛道（Monaco）退化慢

**稳定性评估**：
```
圈时标准差（σ）解读：
- σ < 0.15s：极度稳定，轮胎完全在窗口内
- 0.15s ≤ σ < 0.25s：正常，轻微波动来自胎流和燃油校正
- 0.25s ≤ σ < 0.35s：不稳定，轮胎接近窗口边缘或空力设置不匹配
- σ ≥ 0.35s：极不稳定，轮胎过热或底盘平衡问题
```

### 1.3 退化期 (Degradation Phase)

**定义**：轮胎性能越过"悬崖点"后的加速衰退阶段。

| 参数 | 硬胎 | 中性胎 | 软胎 |
|------|------|--------|------|
| 悬崖点位置 | 25-35圈 | 18-25圈 | 10-15圈 |
| 悬崖后退化率 | 0.05-0.10s/圈 | 0.08-0.15s/圈 | 0.12-0.25s/圈 |
| 悬崖前兆 | 圈时标准差增大 | 末段弯心速度骤降 | 油门全开区缩短 |

**关键特征**：
- 退化曲线从线性变为指数型：`Deg(lap) ∝ lap²` 而非 `lap`
- 横向和纵向抓地力同时下降——不只是慢，而是"不可控"
- 驾驶风格差异放大：温和风格的车手悬崖点延后3-5圈
- 温度管理退化为恶性循环：过热→退化→更大滑动→更过热

**"轮胎悬崖"的识别**：
```python
def detect_tyre_cliff(lap_times, window=3):
    """检测圈时退化率是否突然加速（轮胎悬崖）"""
    if len(lap_times) < window + 1:
        return None
    
    # 计算滑动窗口退化率
    rates = []
    for i in range(len(lap_times) - window):
        rate = (lap_times[i + window] - lap_times[i]) / window
        rates.append(rate)
    
    # 检测退化率是否突然增大
    for i in range(1, len(rates)):
        if rates[i] > rates[i-1] * 2:  # 退化率翻倍
            return i + window  # 悬崖点圈数
    
    return None
```

---

## 2. 退化率计算方法

### 2.1 基础退化模型

```
LapTime(lap) = BaseTime + WarmUp(lap) + DegRate × lap²

其中：
- BaseTime：轮胎在最佳状态下的基准圈时
- WarmUp(lap)：热身期的时间损失，随圈数递减
  WarmUp(lap) = WarmLoss × e^(-lap / τ)
- DegRate：二次退化系数（s/圈²）
- lap：当前圈数（从换胎后计）
```

### 2.2 五圈窗口回归验证

**为什么需要5圈窗口**：
- 3圈窗口：噪声过大，交通/胎流影响占比高
- 5圈窗口：平衡噪声过滤与趋势捕捉
- 7圈窗口：过于迟钝，无法及时发现状态变化

```python
import numpy as np

def calculate_degradation_rate(lap_times, start_lap, window=5):
    """
    使用5圈滑动窗口计算退化率
    返回：线性退化率(s/圈)和二次退化率(s/圈²)
    """
    if len(lap_times) < window:
        return None, None
    
    laps = np.arange(start_lap, start_lap + len(lap_times))
    times = np.array(lap_times)
    
    # 线性拟合
    linear_fit = np.polyfit(laps, times, 1)
    linear_rate = linear_fit[0]  # s/圈
    
    # 二次拟合（更准确但需更多数据）
    if len(lap_times) >= 8:
        quad_fit = np.polyfit(laps, times, 2)
        quad_rate = quad_fit[0]  # s/圈²
    
    return linear_rate, quad_rate if len(lap_times) >= 8 else None
```

### 2.3 退化率校正因素

在计算退化率时，必须校正以下因素：

| 校正项 | 方法 | 量级 |
|--------|------|------|
| 燃油烧耗 | 每圈约0.03s改善 | 前10圈影响显著 |
| 赛道进化 | 对比同圈位置的其他车手 | 前5-10圈1-2s改善 |
| 交通阻挡 | 圈时突然增加0.5s+后恢复 | 标记并排除异常圈 |
| 脏气流 | 跟车时圈时增加0.3-0.8s | 检查与前车距离 |
| 轮胎保温毯残留 | 出站前2圈偏高 | 前2圈不纳入退化计算 |

**燃油校正公式**：
```
CorrectedLapTime = RawLapTime + FuelBurnRate × lap_number
FuelBurnRate ≈ -0.030s/圈（典型值，按每圈消耗约1.5kg燃油）
```

---

## 3. 策略判定规则

### 3.1 Undercut 条件判定

**Undercut定义**：通过提前进站换新胎，利用新胎优势在对手进站时实现超越。

**Undercut成功条件**：

```
新胎性能优势 > 进站时间损失 + 出站圈劣势

具体计算：
新胎优势 = (旧胎退化后圈时 - 新胎圈时) × 对手还需跑的圈数
进站损失 = 约20-25s（赛道依赖，Monaco约22s，Monza约20s）
出站圈劣势 = 约0.5-1.0s（热身期损失）

判断：
Undercut窗口 = 进站损失 / 新胎每圈优势
如果 Undercut窗口 ≤ 对手还剩的旧胎圈数，则Undercut可行
```

**Undercut风险因素**：
- 出站落入交通：被慢车阻挡2-3圈即消散Undercut优势
- 安全车：如果在Undercut执行过程中出安全车，进站方可能反亏
- 轮胎选择：Undercut后如果换的仍是旧配方，优势有限

**Undercut最佳时机**：
- 旧胎刚进入退化期（退化率开始加速时）
- 对手身后有足够gap（>进站损失+出站劣势，约2.5-3s）
- 出站后前方无慢车

### 3.2 Overcut 条件判定

**Overcut定义**：延迟进站，利用对手换胎后的出站圈劣势和清洁气流优势保持位置。

**Overcut成功条件**：

```
清洁气流 + 轻燃油优势 > 旧胎退化损失 + 对手新胎热身后优势

具体计算：
清洁气流优势 = 约0.3-0.5s/圈（在对手出站后，前方赛道清洁）
轻燃油优势 = 每晚进1圈多跑1圈燃油 ≈ 0.03s
旧胎退化损失 = DegRate × 额外圈数（需确保退化率仍在线性期）

关键判断：
- 如果旧胎已接近悬崖点，Overcut风险极高
- 如果赛道难以超车（Monaco），Overcut价值更高
- 如果赛道超车容易（Monza），Overcut价值更低
```

**Overcut适用场景**：
- 高退化赛道：对手新胎退化也快，净窗口优势有限
- 难超车赛道：保持位置比轮胎优势更重要
- 轮胎尚在线性退化期：确认不会突然"掉下悬崖"

### 3.3 安全车策略

**安全车下进站决策矩阵**：

| 当前位置 | 与前车Gap | 进站收益 | 建议 |
|----------|-----------|----------|------|
| ≤P5 | 任何 | "免费"进站（损失从25s降为~12s） | **立即进站** |
| P6-P10 | >2s | 仍可获益但需评估出站位置 | 条件性进站 |
| P6-P10 | <2s | 出站可能丢失多位置 | 保守，除非轮胎已到悬崖 |
| >P10 | 任何 | 位置损失可能大于轮胎收益 | 仅在轮胎危急时进站 |
| 任何 | 领先且Gap<3s | 对手进站你也必须跟进 | **立即进站** |

**安全车"免费进站"计算**：
```
正常进站损失 = 20-25s（全速绕一圈的代价）
安全车进站损失 = 约12-15s（安全车速度下绕一圈）

免费收益 = 正常损失 - 安全车损失 ≈ 8-13s

判断：如果当前可超越目标>5位，安全车进站几乎必赚
```

**VSC vs SC 区别**：
- VSC（虚拟安全车）：所有车减速，进站无位置损失但有Delta Time限制
- SC（安全车）：队列压缩，进站后出站可能落入队列后段
- VSC下进站窗口：必须确保进站+出站不超过Delta Time
- SC下：如果刚好在进站口，"lucky dog"效应最大

---

## 4. 进站窗口计算

### 4.1 最优进站窗口

```
理论最早进站圈 = 赛道总圈数 - 最长stint长度(硬胎)
理论最晚进站圈 = 赛道总圈数 - 最短stint长度(软胎)

最优窗口 = [理论最早圈, 理论最晚圈] 的交集

示例（50圈正赛）：
- 硬胎stint: 20-30圈
- 中性胎stint: 15-22圈
- 软胎stint: 8-15圈

一停策略窗口：
- 起→中→终: 第18-25圈进站
- 起→硬→终: 第22-30圈进站

二停策略窗口：
- 第一停: 第12-18圈
- 第二停: 第30-38圈
```

### 4.2 策略时间等效计算

**不同策略的总时间等效**：

```python
def strategy_total_time(base_lap, stint_config):
    """
    计算策略总时间
    stint_config: [(compound, lap_count), ...]
    """
    total = 0
    for compound, laps in stint_config:
        for lap in range(1, laps + 1):
            deg = get_degradation(compound, lap)
            total += base_lap + deg
    # 加入进站时间损失
    pit_stops = len(stint_config) - 1
    total += pit_stops * 22  # 假设22s进站损失
    return total
```

---

## 5. 正确 vs 错误示例

### 5.1 退化率描述

❌ **错误**："软胎衰退斜率0.05s/圈"
- 问题：仅一个数字，无上下文，无验证方法，无物理机制

✅ **正确**："软胎在第8-12圈进入退化期，A的圈时标准差0.021s vs B的0.034s，表明A的空力设置对轮胎温度窗口匹配更精准，在35圈stint中累积优势约0.4s"
- 优点：标准差对比 + 空力归因 + 累积量化

### 5.2 策略评估

❌ **错误**："A应该早点进站换新胎"
- 问题：无量化依据，"早点"是多久？

✅ **正确**："A在第18圈执行Undercut，新中性胎vs对手旧软胎（第12圈已退化）每圈优势0.35s，需8圈追回进站损失22s。如果对手在第20圈跟进进站，A可获1.2s净窗口优势，足以在T1完成超越"
- 优点：具体圈数 + 每圈优势 + 追回时间 + 超越可行性

### 5.3 安全车决策

❌ **错误**："安全车出来了，应该进站"
- 问题：未评估位置损失和出站位置

✅ **正确**："SC第24圈出现时A在P3，与前车Gap 2.1s。进站损失约12s（SC下），出站预估P7，可追回至P5（前方2车需在5圈内进站）。不进站则轮胎在第30圈到达悬崖，预计损失3-4s。建议进站——位置损失1-2位可接受，换得16圈新鲜硬胎"
- 优点：位置评估 + 出站预测 + 不进站风险 + 决策理由

### 5.4 轮胎对比

❌ **错误**："硬胎比软胎慢1.5秒"
- 问题：条件不明——哪一圈？什么温度？退化到什么程度？

✅ **正确**："硬胎vs软胎基准圈时差1.2s（取两种配方稳定期第3-8圈中位数），在35°C赛道温度下差距扩大至1.4s。但硬胎退化率仅0.015s/圈 vs 软胎0.045s/圈，在第15圈后硬胎反而更快"
- 优点：基准差 + 温度条件 + 退化率对比 + 交叉点

---

## 6. 常见陷阱与Gotchas

### 6.1 数据解读陷阱

| 陷阱 | 说明 | 应对策略 |
|------|------|----------|
| 燃油烧耗混淆退化 | 前10圈燃油改善(0.03s/圈)可能大于轮胎退化 | 校正燃油效应后再评估退化率 |
| 双停vs单停不可直接对比 | 双停策略后段轮胎更新，圈时不可与单停同龄轮胎对比 | 分stint分析，标注轮胎年龄 |
| 脏气流加热效应 | 跟车时轮胎温度升6-8°C | 长时间跟车后退化加速不代表轮胎本身差 |
| 排位赛轮胎数据误用 | 排位赛轮胎温度、燃油与正赛完全不同 | 不可直接套用排位退化率到正赛 |
| 码表圈时 vs 真实圈时 | DRS、尾流、交通导致单圈圈时不具代表性 | 用中位数或3圈滚动平均 |
| 气温变化 | 正赛期间气温可能变化5-10°C | 不同stint间的退化率差异可能来自气温而非策略 |

### 6.2 策略推理陷阱

| 陷阱 | 说明 | 应对策略 |
|------|------|----------|
| 后视偏差 | "如果他早1圈进站就能保住位置" | 当时无法预知安全车时机 |
| 忽略二阶效应 | 只看轮胎退化，忽略交通/位置保护 | 策略评估必须包含位置价值 |
| 过度优化 | 追求"最优"策略忽略容错性 | 实际策略需考虑安全车概率 |
| 一停偏好偏差 | 认为一停更优（少损失进站时间） | 需对比总时间等效而非仅进站次数 |
| 假设对手最优 | 分析自身策略时假设对手做最优选择 | 对手也会犯错，需评估双方策略 |
| 周五练习数据误用 | 周五的长距离数据可能不代表正赛条件 | 标注数据来源和条件差异 |

### 6.3 2026赛季特殊考虑

**新轮胎供应商/规格**：
- 2026赛季轮胎规格变化可能改变退化特性
- 历史退化数据仅供参考，需用2026实际数据验证
- 新规格的"悬崖点"位置可能与以往不同

**50/50功率比影响**：
- MGU-K功率增大导致出弯牵引力需求增加→后轮退化可能更严重
- 能量回收变化影响制动分布→前轮退化模式可能改变
- 需要关注：2026轮胎退化是否呈现"前后轮差异化"的新模式

**比赛长度变化**：
- 部分赛事可能有比赛时间/圈数调整
- 进站窗口计算需基于实际赛程

---

## 7. 轮胎策略分析输出规范

### 7.1 退化分析报告模板

```markdown
## [车手] [赛道] [配方] 退化分析

### Stint概览
- 配方: [C1/C2/C3/C4/C5] / [硬/中/软]
- Stint长度: [X]圈 (第[N]圈 - 第[M]圈)
- 进站损失: [X.X]s

### 退化曲线
- 热身期: 第[N]-[M]圈, 损失[X.X]s
- 稳定期: 第[N]-[M]圈, 线性退化率[X.XXX]s/圈
- 退化期: 第[N]圈起, 二次退化率[X.XXX]s/圈²
- 悬崖点: 第[N]圈 (如已到达)

### 稳定性评估
- 稳定期圈时σ: [X.XXX]s
- 横向一致性: [高/中/低]
- 与队友对比: σ差距[X.XXX]s, 原因[...]

### 策略评价
- 该stint时长评级: [优/良/中/差]
- 与最优窗口偏差: [X]圈
- 改进建议: [...]
```

### 7.2 策略复盘报告模板

```markdown
## [赛道] [赛季] 策略复盘

### 策略选择
| 车手 | 策略 | 进站圈 | 配方序列 | 总时间等效 |
|------|------|--------|----------|-----------|

### 关键策略决策
1. 第[N]圈: [决策描述] → [结果] → [评价]
2. ...

### 最优策略反事实
如果[车手]选择[替代策略]：
- 预估总时间: [X.XXX]s (对比实际±[X.X]s)
- 位置变化: 预估P[X] vs 实际P[Y]
- 风险评估: [...]

### 经验总结
- 本站策略教训: [...]
- 通用策略洞见: [...]
```

---

## 8. FastF1 API 实战指南

### 8.1 获取轮胎和策略数据

```python
import fastf1

session = fastf1.get_session(2026, 'Japanese Grand Prix', 'R')
session.load()

# 获取所有车手的轮胎信息
for driver in session.drivers:
    driver_laps = session.laps.pick_driver(driver)
    stint_info = driver_laps[['Stint', 'Compound', 'LapNumber', 'LapTime']]
    # 按stint分组计算退化
    for stint_num, stint_laps in stint_info.groupby('Stint'):
        compound = stint_laps['Compound'].iloc[0]
        # ... 退化分析
```

### 8.2 进站数据提取

```python
# 获取进站信息
pit_stops = session.laps[
    session.laps['PitInTime'].notna()
][['Driver', 'LapNumber', 'PitInTime', 'Stint', 'Compound']]

# 计算进站时间损失
for driver in session.drivers:
    driver_laps = session.laps.pick_driver(driver)
    pit_laps = driver_laps[driver_laps['PitInTime'].notna()]['LapNumber'].tolist()
    # 进站圈+出站圈的额外时间
    for pit_lap in pit_laps:
        normal_lap = driver_laps[
            ~driver_laps['LapNumber'].isin(pit_laps)
        ]['LapTime'].median()
        pit_lap_time = driver_laps[
            driver_laps['LapNumber'] == pit_lap
        ]['LapTime'].iloc[0]
        pit_loss = pit_lap_time - normal_lap
```

### 8.3 退化率可视化

```python
import matplotlib.pyplot as plt
import numpy as np

def plot_degradation(session, driver, compound_filter=None):
    """绘制轮胎退化曲线"""
    laps = session.laps.pick_driver(driver)
    
    if compound_filter:
        laps = laps[laps['Compound'] == compound_filter]
    
    for stint in laps['Stint'].unique():
        stint_laps = laps[laps['Stint'] == stint]
        compound = stint_laps['Compound'].iloc[0]
        
        # 排除进站圈和异常圈
        clean_laps = stint_laps[
            stint_laps['PitInTime'].isna() & 
            stint_laps['PitOutTime'].isna()
        ]
        
        lap_numbers = clean_laps['LapNumber'] - clean_laps['LapNumber'].iloc[0]
        lap_times = clean_laps['LapTime'].dt.total_seconds()
        
        plt.plot(lap_numbers, lap_times, 
                label=f'Stint {stint} ({compound})',
                marker='o', markersize=3)
    
    plt.xlabel('Stint Lap Number')
    plt.ylabel('Lap Time (s)')
    plt.legend()
    plt.title(f'{driver} Tire Degradation')
```

---

## 9. 质量检查清单

分析完成前，逐项确认：

- [ ] 退化率基于5圈以上窗口验证
- [ ] 已校正燃油烧耗效应（特别是前10圈数据）
- [ ] 进站圈/出站圈已从退化分析中排除
- [ ] 安全车圈已标记并排除
- [ ] 轮胎配方标注正确（硬/中/软 + C编号）
- [ ] 稳定期vs退化期已明确区分
- [ ] Undercut/Overcut判定包含具体圈数和量化数据
- [ ] 策略评估包含位置价值而不仅是圈时
- [ ] 已标注置信度等级
- [ ] 2026新规影响（MGU-K/轮胎规格）已考虑
