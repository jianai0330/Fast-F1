# F1 扇区根因诊断技能 (Sector Root Cause Diagnosis)

## 元信息

- **技能ID**: f1-sector-diagnosis
- **版本**: 1.0.0
- **适用场景**: 排位赛差距分析、正赛节奏差异诊断、车手/车辆性能瓶颈定位
- **前置依赖**: 扇区时间数据、遥测数据、弯角信息
- **核心方法论**: 理想圈构成 → 弱势扇区定位 → 弯角级别根因分解

---

## 1. 理想圈计算

### 1.1 概念定义

**理想圈 (Ideal Lap / Theoretical Best Lap)**：将多圈中各扇区/分段的最佳表现组合而成的理论最快圈时。

**核心价值**：
- 量化车手/车辆的潜在极限
- 评估实际表现与潜力的差距
- 定位"时间留在了哪里"——哪个扇区从未同时达到最佳

### 1.2 计算方法

#### 方法一：扇区级理想圈

```
IdealLap = min(S1_times) + min(S2_times) + min(S3_times)

优点：简单直接
缺点：扇区组合可能不可达（如S1最佳和S2最佳来自不同轮胎/燃油状态）
```

#### 方法二：迷你扇区级理想圈

```
将赛道分为更细粒度的mini-sector（每10-50m一个）：
IdealLap = Σ min(mini_sector_i_times)

优点：更精确地定位时间来源
缺点：数据对齐要求高，计算复杂
```

#### 方法三：累计时间法

```python
def ideal_lap_from_laps(laps_df):
    """
    从多圈数据计算理想圈
    laps_df: 包含 Sector1Time, Sector2Time, Sector3Time 的DataFrame
    """
    # 排除异常圈（进站、安全车、明显慢圈）
    clean_laps = laps_df[
        laps_laps['PitInTime'].isna() & 
        laps_df['PitOutTime'].isna()
    ].copy()
    
    # 取每个扇区的最佳时间
    best_s1 = clean_laps['Sector1Time'].min()
    best_s2 = clean_laps['Sector2Time'].min()
    best_s3 = clean_laps['Sector3Time'].min()
    
    ideal_lap = best_s1 + best_s2 + best_s3
    actual_best = clean_laps['LapTime'].min()
    potential_gap = ideal_lap - actual_best  # 应为负值或接近零
    
    return {
        'ideal_lap': ideal_lap,
        'actual_best': actual_best,
        'potential_gap': potential_gap,
        'best_s1_lap': clean_laps.loc[clean_laps['Sector1Time'].idxmin(), 'LapNumber'],
        'best_s2_lap': clean_laps.loc[clean_laps['Sector2Time'].idxmin(), 'LapNumber'],
        'best_s3_lap': clean_laps.loc[clean_laps['Sector3Time'].idxmin(), 'LapNumber'],
    }
```

### 1.3 理想圈与实际差距解读

| 潜力差距 | 解读 | 典型场景 |
|----------|------|----------|
| < 0.1s | 已接近极限 | 排位Q3最末推圈，三扇区几乎同时达到最佳 |
| 0.1-0.3s | 正常范围 | 大多数排位圈，一两个弯角有小失误 |
| 0.3-0.5s | 有明显提升空间 | 交通影响、小失误、轮胎未达最佳温度 |
| 0.5-1.0s | 重大未实现潜力 | 大失误、交通严重、轮胎问题 |
| > 1.0s | 极端情况 | 中途放弃的飞行圈、严重交通、技术问题 |

**重要提醒**：
- 理想圈是上界估计——实际很难同时达到所有扇区最佳
- 排位赛理想圈差距通常比正赛小（排位更接近极限）
- 不同圈的最佳扇区如果来自不同轮胎状态，组合后不可达

---

## 2. 扇区特性分类

### 2.1 扇区类型学

不同赛道的扇区特性差异巨大，必须先理解"扇区在测什么"：

#### S1：高速稳定性测试

**典型特征**：
- 含高速弯（>200km/h弯心速度）
- 测试空力效率（下压力 vs 阻力权衡）
- 稳定性要求高——小失误在高速段代价大

**优势来源**：
- 高下压力设定：弯心速度高
- 底板效率：扩散器在高速下产生更多下压力
- 车手信心：高速弯需要勇气和精准

**典型赛道**：Suzuka S1、Silverstone S1、Spa S1

#### S2：技术弯角精度测试

**典型特征**：
- 含中低速弯组合、chicane、发夹弯
- 测试机械抓地力、制动稳定性、牵引力
- 节奏感要求——连续弯角链不容失误

**优势来源**：
- 悬挂几何：中低速弯的侧向支撑
- 制动效率：重制动区的稳定性和可重复性
- 差速器设定：出弯牵引力

**典型赛道**：Monaco S2、Singapore S2、Hungaroring S2

#### S3：出弯加速与直线测试

**典型特征**：
- 含末段弯角 + 主直线
- 测试出弯效率、PU功率、DRS效果
- 直线段长度决定PU贡献权重

**优势来源**：
- PU功率：直线段最高速
- MGU-K部署：出弯电能释放
- 牵引力：出弯加速效率
- DRS效率：翼展设计

**典型赛道**：Monza S3、Baku S3、Spa S3（Eau Rouge后直线）

### 2.2 赛道扇区特性速查

| 赛道 | S1特性 | S2特性 | S3特性 |
|------|--------|--------|--------|
| Suzuka | 高速S弯群 | 技术弯角组合 | 出弯+主直线 |
| Monaco | 低速技术 | 极低速+隧道 | 出弯+直线短 |
| Monza | 减速弯+直线 | 低速弯 | 长直线+减速弯 |
| Silverstone | 高速弯组 | 技术弯 | 直线+减速弯 |
| Spa | 高速下坡 | 技术弯组 | Eau Rouge+直线 |
| Bahrain | 中速技术 | 低速弯 | 直线+牵引力 |
| Singapore | 低速技术 | 低速弯组 | 直线短+弯角 |

---

## 3. 根因诊断流程

### 3.1 四步诊断法

```
步骤1：定位差异最大的扇区
    │
    ▼
步骤2：在扇区内定位具体弯角/直线段
    │
    ▼
步骤3：对比遥测参数——是制动? 弯心? 出弯? 直线?
    │
    ▼
步骤4：归因——车辆设置 vs 驾驶风格 vs 轮胎状态 vs 天气
```

### 3.2 步骤1：定位差异最大的扇区

**方法**：
1. 计算两车各扇区时间差
2. 计算每个扇区差异占总差距的百分比
3. 定位贡献最大的扇区

```python
def locate_weakest_sector(driver_a_laps, driver_b_laps):
    """定位两车差距最大的扇区"""
    # 取最佳圈
    lap_a = driver_a_laps.pick_fastest()
    lap_b = driver_b_laps.pick_fastest()
    
    sectors = ['Sector1Time', 'Sector2Time', 'Sector3Time']
    total_gap = (lap_a['LapTime'] - lap_b['LapTime']).total_seconds()
    
    sector_gaps = {}
    for s in sectors:
        gap = (lap_a[s] - lap_b[s]).total_seconds()
        sector_gaps[s] = {
            'gap': gap,
            'pct': abs(gap) / abs(total_gap) * 100 if total_gap != 0 else 0
        }
    
    # 排序找出贡献最大的扇区
    sorted_sectors = sorted(sector_gaps.items(), 
                           key=lambda x: abs(x[1]['gap']), 
                           reverse=True)
    
    return sorted_sectors, total_gap
```

**关键指标**：
- 扇区绝对差距（秒）
- 扇区差异占总量百分比
- 是否存在"一致劣势"（所有圈同扇区都慢→设置问题）

### 3.3 步骤2：弯角级别定位

**距离映射法**：
```
1. 获取扇区起止距离范围
2. 在该范围内绘制ΔSpeed曲线
3. 定位ΔSpeed最大的弯角/直线段
4. 如果circuit_info可用，直接映射弯角编号
5. 如果不可用，用距离区间描述（如"距离1200-1500m的弯角组"）
```

**分组分析**：
```
将连续弯角归为"弯角组"：
- Suzuka: S弯群(T1-T7), Spoon(T13-T14), 130R(T15), Casio(T16-T18)
- Silverstone: Copse-Maggots-Becketts(T1-T7), Stowe(T9), Club(T17-T18)

组内弯角的时间差异通常来自同一物理原因
```

### 3.4 步骤3：遥测参数对比

对定位到的具体弯角/直线段，进行四阶段分解：

| 阶段 | 遥测指标 | 计算方法 | 时间换算 |
|------|----------|----------|----------|
| 制动 | 制动点距离、制动减速度 | Brake信号从0→1的Distance | 每提前1m ≈ 0.03s（120km/h） |
| 弯心 | 弯心速度、横向G | Speed的局部最小值 | 每1km/h ≈ 0.02-0.06s（弯角依赖） |
| 出弯 | 油门应用点、加速斜率 | Throttle从<50%→100%的Distance | 出弯0-200m加速差0.5s ≈ 0.02-0.05s |
| 直线 | 最高速、DRS状态 | Speed的最大值 | 每1km/h ≈ 0.01-0.02s（直线长度依赖） |

```python
def diagnose_corner(lap_a_telemetry, lap_b_telemetry, corner_distance, window=200):
    """
    诊断特定弯角的时间差异来源
    corner_distance: 弯心的大致距离位置
    window: 分析窗口（弯心前后各window米）
    """
    # 提取弯角区域
    start = corner_distance - window
    end = corner_distance + window
    
    tel_a = lap_a_telemetry[
        (lap_a_telemetry['Distance'] >= start) & 
        (lap_a_telemetry['Distance'] <= end)
    ]
    tel_b = lap_b_telemetry[
        (lap_b_telemetry['Distance'] >= start) & 
        (lap_b_telemetry['Distance'] <= end)
    ]
    
    # 弯心速度
    apex_speed_a = tel_a['Speed'].min()
    apex_speed_b = tel_b['Speed'].min()
    
    # 制动点
    brake_a = tel_a[tel_a['Brake'] > 0]['Distance'].min()
    brake_b = tel_b[tel_b['Brake'] > 0]['Distance'].min()
    
    # 油门恢复点
    throttle_a = tel_a[tel_a['Throttle'] > 90]['Distance'].min()
    throttle_b = tel_b[tel_b['Throttle'] > 90]['Distance'].min()
    
    return {
        'apex_speed_diff': apex_speed_a - apex_speed_b,
        'brake_point_diff': brake_a - brake_b,
        'throttle_point_diff': (throttle_a or 0) - (throttle_b or 0),
    }
```

### 3.5 步骤4：归因判断

**四大归因类别**：

#### 车辆设置 (Car Setup)

**识别特征**：
- 差异在多圈中一致存在
- 队友间差异大但同一车手各圈一致
- 换胎后差异模式不变

**典型模式**：
| 观测 | 归因 |
|------|------|
| 高速弯慢+直线快 | 低阻力设定（减翼展） |
| 高速弯快+直线慢 | 高下压力设定（增翼展） |
| 出弯牵引力差 | 差速器锁定率不足/后轮温度低 |
| 弯心不稳定 | 底盘刚度偏硬/悬挂几何不当 |

#### 驾驶风格 (Driving Style)

**识别特征**：
- 差异在同一车手的多圈中不固定
- 随比赛进程变化（轮胎退化后风格调整）
- 与车手的"个人标记"一致

**典型模式**：
| 观测 | 归因 |
|------|------|
| 循迹制动深但弯心慢 | V型过弯风格 |
| 早制动早加速 | U型过弯风格，保护轮胎 |
| 弯中油门犹豫 | 对后轮缺乏信心 |
| 多次弯中修正 | 入弯速度过高或转向不足 |

#### 轮胎状态 (Tire State)

**识别特征**：
- 差异随stint进展变化
- 换胎后差异消失或反转
- 圈时标准差增大

**典型模式**：
| 观测 | 归因 |
|------|------|
| 早期快后期慢 | 轮胎过热或退化加速 |
| 弯心速度逐步降低 | 轮胎磨损导致抓地力下降 |
| 出弯打滑增多 | 后轮退化/过热 |
| 制动不稳定 | 前轮锁定点变化 |

#### 天气/赛道条件 (Conditions)

**识别特征**：
- 差异与时间点相关（天气变化）
- 多车同时表现变化
- 风向变化导致特定弯角差异

**典型模式**：
| 观测 | 归因 |
|------|------|
| 顺风弯减速 | 尾风减少空力效率 |
| 逆风弯加速 | 迎风增加下压力 |
| 雨后某些弯角慢 | 湿滑区域/驻水 |
| 赛道进化后整体快 | 橡胶铺设 |

---

## 4. 正确 vs 错误示例

### 4.1 扇区差距描述

❌ **错误**："S2是B的弱势扇区"
- 问题：仅定位，无量化，无根因

✅ **正确**："S2劣势0.18s，集中在T7-T9高速弯群组：入弯制动点提前A车3m(-0.03s)，弯心速度低3km/h(-0.08s)，出弯平衡(+0.01s)。根因判断：底盘刚度设置偏硬导致弯心不稳，迫使提前制动"
- 优点：量化 + 弯角级分解 + 三阶段 + 具体归因

### 4.2 理想圈分析

❌ **错误**："A的理想圈比B快0.5秒"
- 问题：理想圈差距不等于实力差距，可能是A的扇区组合更不协调

✅ **正确**："A理想圈0.3s快于B，但实际最佳圈仅差0.1s。A的潜力利用率78%（差距0.4s在S1和S3两个不同飞行圈的最佳扇区），B的利用率92%（三扇区几乎在同一圈达到最佳）。说明A有更多未实现潜力，如果能在Q3找到完整圈，差距可能扩大"
- 优点：潜力利用率 + 实际vs理想对比 + 预测性判断

### 4.3 归因判断

❌ **错误**："B在弯中慢是因为他的车不好"
- 问题："车不好"过于笼统，无具体机制

✅ **正确**："B在T4-T6中速弯群组弯心速度持续低2-4km/h，但在低速弯（T1-T2）和直线段无明显差异。结合：(1)队友同弯角速度差仅0.5km/h，(2)换胎后模式不变，(3)正赛10圈后差距扩大至5km/h——判断为底盘刚度偏硬导致中速弯横向载荷转移过快，轮胎无法在弯心建立足够抓地力。根因为车辆设置而非驾驶风格"
- 优点：排除替代假说 + 多数据源交叉验证 + 明确归因

### 4.4 跨Session对比

❌ **错误**："A在正赛S2比排位赛慢0.8秒，说明他在正赛有问题"
- 问题：排位和正赛条件完全不同，差距正常

✅ **正确**："A正赛S2比排位慢0.8s，其中约0.5s来自燃油负载差异（110kg vs 排位最低量），约0.2s来自轮胎退化（正赛第15圈硬胎 vs 排位软胎），约0.1s来自引擎模式差异。剩余0.0s为未解释差异，表明A正赛节奏与排位表现一致"
- 优点：因素分解 + 量化各项贡献 + 排除异常

---

## 5. 常见陷阱与Gotchas

### 5.1 诊断逻辑陷阱

| 陷阱 | 说明 | 应对策略 |
|------|------|----------|
| 单圈归因 | 仅凭一圈数据做归因 | 至少3圈一致性验证，不同圈应显示相同模式 |
| 相关性误读 | S1快和直线快同时出现，但可能是不同原因 | 逐弯角分解，区分空力和PU贡献 |
| 忽略Session差异 | 排位vs正赛vs练习的扇区表现不可直接比较 | 校正燃油、轮胎、引擎模式差异 |
| 潜力差距误读 | 理想圈差距大不等于实力差距大 | 计算潜力利用率，结合实际最佳圈分析 |
| 确认偏差 | 先有结论再找数据支持 | 先列出所有可能的归因，逐一排除 |
| 忽略交通影响 | 跟车时S3直线可能异常慢 | 检查前车距离，排除受交通影响的圈 |

### 5.2 数据质量陷阱

| 陷阱 | 说明 | 应对策略 |
|------|------|----------|
| 扇区时间缺失 | FastF1偶发Sector时间NaN | 使用完整圈时减去其他扇区推算 |
| 弯角距离NaN | 2026赛季circuit_info.corners可能全为NaN | 降级为距离区间描述法 |
| 遥测采样不对齐 | 两车Distance刻度不完全匹配 | 插值对齐后再计算ΔSpeed |
| DRS混淆 | DRS开启导致直线速度差不代表空力差异 | 标注DRS状态，分开分析 |
| 进站圈混入 | 进站圈扇区时间异常 | 严格过滤PitIn/PitOut圈 |

### 5.3 2026赛季特殊考虑

**能量部署影响扇区表现**：
- MGU-K 200kW+的电能部署策略可能导致特定扇区表现波动
- 同一车手不同圈的S3直线速度可能差5-10km/h（电量不同）
- 需要区分"电量不足"和"空力劣势"

**新空力规则影响**：
- 主动空力可能改变不同模式下的扇区特性
- 排位模式vs正赛模式的下压力差异可能更大
- 分析时需确认空力模式（如果数据可用）

---

## 6. 扇区诊断输出规范

### 6.1 诊断报告模板

```markdown
## [车手A] vs [车手B] — [赛道] 扇区诊断

### 差距总览
| 指标 | A | B | 差异 |
|------|---|---|------|
| 最佳圈 | xx:xx.xxx | xx:xx.xxx | ±0.000s |
| 理想圈 | xx:xx.xxx | xx:xx.xxx | ±0.000s |
| 潜力利用率 | XX% | XX% | |

### 扇区差距分解
| 扇区 | A最佳 | B最佳 | 差异 | 占比 | 特性 |
|------|-------|-------|------|------|------|
| S1 | xx.xxx | xx.xxx | ±0.000s | XX% | [高速/技术/直线] |
| S2 | xx.xxx | xx.xxx | ±0.000s | XX% | [高速/技术/直线] |
| S3 | xx.xxx | xx.xxx | ±0.000s | XX% | [高速/技术/直线] |

### 关键弯角级分解（S[X]）
| 弯角 | 类型 | 差异来源 | 物理机制 | 时间贡献 |
|------|------|----------|----------|----------|
| T[X] | [高速/中速/低速] | [制动/弯心/出弯] | [具体机制] | ±0.000s |

### 归因结论
1. 主因：[车辆设置/驾驶风格/轮胎/条件] — [具体描述] — [置信度]
2. 次因：[...] — [...] — [置信度]

### 改进建议
- [具体建议1]：预期收益 ±0.000s
- [具体建议2]：预期收益 ±0.000s
```

### 6.2 量化精度规则

- 扇区时间差：精确到0.001s
- 弯角时间贡献：精确到0.01s
- 弯心速度差：精确到0.5km/h
- 制动点差：精确到1m
- 归因置信度：高(>80%) / 中(60-80%) / 低(<60%)

---

## 7. FastF1 API 实战指南

### 7.1 扇区数据获取

```python
import fastf1

session = fastf1.get_session(2026, 'Japanese Grand Prix', 'Q')
session.load()

# 获取扇区时间
for driver in ['VER', 'NOR']:
    laps = session.laps.pick_driver(driver)
    fastest = laps.pick_fastest()
    print(f"{driver}: S1={fastest['Sector1Time']}, "
          f"S2={fastest['Sector2Time']}, "
          f"S3={fastest['Sector3Time']}")
```

### 7.2 理想圈计算

```python
import pandas as pd

def compute_ideal_lap(driver_laps):
    """计算理想圈"""
    clean = driver_laps[
        driver_laps['PitInTime'].isna() & 
        driver_laps['PitOutTime'].isna()
    ]
    
    best_s1 = clean['Sector1Time'].min()
    best_s2 = clean['Sector2Time'].min()
    best_s3 = clean['Sector3Time'].min()
    
    ideal = best_s1 + best_s2 + best_s3
    actual = clean['LapTime'].min()
    
    utilization = actual / ideal * 100  # 利用率
    
    return {
        'ideal': ideal,
        'actual': actual,
        'gap': actual - ideal,
        'utilization': utilization,
        'best_s1_from': clean.loc[clean['Sector1Time'].idxmin(), 'LapNumber'],
        'best_s2_from': clean.loc[clean['Sector2Time'].idxmin(), 'LapNumber'],
        'best_s3_from': clean.loc[clean['Sector3Time'].idxmin(), 'LapNumber'],
    }
```

### 7.3 扇区差异可视化

```python
import matplotlib.pyplot as plt

def plot_sector_comparison(session, drivers):
    """绘制多车手扇区时间对比"""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    sectors = ['Sector1Time', 'Sector2Time', 'Sector3Time']
    sector_names = ['S1', 'S2', 'S3']
    
    for ax, sector, name in zip(axes, sectors, sector_names):
        times = []
        labels = []
        for driver in drivers:
            lap = session.laps.pick_driver(driver).pick_fastest()
            t = lap[sector].total_seconds()
            times.append(t)
            labels.append(driver)
        
        ax.bar(labels, times)
        ax.set_title(name)
        ax.set_ylabel('Time (s)')
        # 标注与最快的差距
        min_time = min(times)
        for i, t in enumerate(times):
            gap = t - min_time
            if gap > 0:
                ax.annotate(f'+{gap:.3f}s', (i, t), 
                          ha='center', va='bottom')
    
    plt.tight_layout()
```

---

## 8. 质量检查清单

分析完成前，逐项确认：

- [ ] 理想圈计算排除进站圈/安全车圈
- [ ] 扇区差距百分比计算正确（占总差距比例）
- [ ] 弱势扇区已定位到具体弯角/直线段
- [ ] 弯角级分解包含制动/弯心/出弯/直线四阶段
- [ ] 归因判断排除了替代假说
- [ ] 归因标注了置信度等级
- [ ] 多圈一致性验证通过（至少3圈相同模式）
- [ ] 排位/正赛数据不做直接对比（已校正条件差异）
- [ ] 弯角距离NaN时使用距离区间降级方案
- [ ] 2026特殊维度（能量部署、主动空力）已考虑
