"""
2026 日本大奖赛（铃鹿）- 阿尔本 vs 阿隆索 遥测数据对比
Williams ALB vs Aston Martin ALO - Suzuka 2026
"""

import matplotlib.pyplot as plt
import numpy as np

import fastf1
import fastf1.plotting

fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')
fastf1.Cache.enable_cache('cache')

# 加载 2026 日本大奖赛排位赛
session = fastf1.get_session(2026, 'Japanese Grand Prix', 'Q')
session.load()

# 获取最快圈
alb_lap = session.laps.pick_drivers('ALB').pick_fastest()
alo_lap = session.laps.pick_drivers('ALO').pick_fastest()

# 获取遥测数据并添加距离列
alb_tel = alb_lap.get_car_data().add_distance()
alo_tel = alo_lap.get_car_data().add_distance()

# 获取赛道角落信息
circuit_info = session.get_circuit_info()

# 获取车队颜色
alb_color = fastf1.plotting.get_driver_color('ALB', session=session)
alo_color = fastf1.plotting.get_driver_color('ALO', session=session)

# 创建多子图布局：速度、油门、刹车、档位
fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
fig.suptitle(
    f"2026 日本大奖赛（铃鹿）排位赛 - 最快圈对比\n"
    f"ALB (Williams) vs ALO (Aston Martin)",
    fontsize=14, y=0.98
)

# 各子图数据
channels = [
    ('Speed',    'Speed (km/h)',    False),
    ('Throttle', 'Throttle (%)',    False),
    ('Brake',    'Brake',           False),
    ('nGear',    'Gear',            True),
]

for ax, (channel, ylabel, is_step) in zip(axes, channels):
    if is_step:
        ax.step(alb_tel['Distance'], alb_tel[channel], color=alb_color, label='ALB', where='post')
        ax.step(alo_tel['Distance'], alo_tel[channel], color=alo_color, label='ALO', where='post')
    else:
        ax.plot(alb_tel['Distance'], alb_tel[channel], color=alb_color, label='ALB')
        ax.plot(alo_tel['Distance'], alo_tel[channel], color=alo_color, label='ALO')

    ax.set_ylabel(ylabel)
    ax.legend(loc='upper right')

    # 添加角落标注
    v_min = ax.get_ylim()[0]
    v_max = ax.get_ylim()[1]
    ax.vlines(
        x=circuit_info.corners['Distance'],
        ymin=v_min, ymax=v_max,
        linestyles='dotted', colors='grey', alpha=0.5, linewidth=0.8
    )

# 在最下方子图添加角落编号
ax_bottom = axes[-1]
v_min, v_max = ax_bottom.get_ylim()
for _, corner in circuit_info.corners.iterrows():
    txt = f"{corner['Number']}{corner['Letter']}"
    ax_bottom.text(
        corner['Distance'], v_min - 0.5, txt,
        va='top', ha='center', size='x-small', color='grey'
    )

axes[-1].set_xlabel('Distance (m)')

plt.tight_layout()
plt.savefig('suzuka_2026_alb_vs_alo.png', dpi=150, bbox_inches='tight')
plt.show()
print("图表已保存为 suzuka_2026_alb_vs_alo.png")
