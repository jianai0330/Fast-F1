"""
2026 Japanese GP (Suzuka) - ALB (Williams) vs ALO (Aston Martin)
Qualifying fastest lap telemetry comparison
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

import fastf1
import fastf1.plotting

fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')

os.makedirs('/Users/aijian/Downloads/Fast-F1/cache', exist_ok=True)
fastf1.Cache.enable_cache('/Users/aijian/Downloads/Fast-F1/cache')

session = fastf1.get_session(2026, 'Japanese Grand Prix', 'Q')
session.load()

alb_lap = session.laps.pick_drivers('ALB').pick_fastest()
alo_lap = session.laps.pick_drivers('ALO').pick_fastest()

alb_tel = alb_lap.get_car_data().add_distance()
alo_tel = alo_lap.get_car_data().add_distance()

circuit_info = session.get_circuit_info()

alb_color = fastf1.plotting.get_driver_color('ALB', session=session)
alo_color = fastf1.plotting.get_driver_color('ALO', session=session)

def fmt_time(td):
    total = int(td.total_seconds())
    ms = int(td.total_seconds() * 1000) % 1000
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}.{ms:03d}"

alb_time = fmt_time(alb_lap['LapTime'])
alo_time = fmt_time(alo_lap['LapTime'])
delta_s = (alb_lap['LapTime'] - alo_lap['LapTime']).total_seconds()
faster = 'ALB' if delta_s < 0 else 'ALO'
delta_str = f"{abs(delta_s):.3f}s  ({faster} faster)"

# 弯角距离：如果 circuit_info 有数据就用，否则按遥测总距离等分
total_dist = alb_tel['Distance'].max()
n_corners = len(circuit_info.corners)

corner_distances = circuit_info.corners['Distance'].values
if np.isnan(corner_distances).all():
    # fallback: 等间距分布
    corner_distances = np.linspace(0, total_dist, n_corners + 1)[1:]

corner_labels = [
    f"T{int(r['Number'])}{r['Letter']}"
    for _, r in circuit_info.corners.iterrows()
]

# ── Layout ────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(4, 1, figsize=(16, 14), sharex=True,
                         gridspec_kw={'height_ratios': [3, 2, 1, 2], 'hspace': 0.08})

fig.suptitle(
    f"2026 Japanese GP — Suzuka  |  Qualifying Fastest Lap\n"
    f"ALB (Williams)  {alb_time}   vs   ALO (Aston Martin)  {alo_time}   |  Gap: {delta_str}",
    fontsize=13, y=0.99
)

channels = [
    ('Speed',    'Speed (km/h)', False),
    ('Throttle', 'Throttle (%)', False),
    ('Brake',    'Brake',        False),
    ('nGear',    'Gear',         True),
]

for ax, (channel, ylabel, is_step) in zip(axes, channels):
    if is_step:
        ax.step(alb_tel['Distance'], alb_tel[channel],
                color=alb_color, label=f"ALB  {alb_time}", where='post', linewidth=1.5)
        ax.step(alo_tel['Distance'], alo_tel[channel],
                color=alo_color, label=f"ALO  {alo_time}", where='post', linewidth=1.5)
    else:
        ax.plot(alb_tel['Distance'], alb_tel[channel],
                color=alb_color, label=f"ALB  {alb_time}", linewidth=1.5)
        ax.plot(alo_tel['Distance'], alo_tel[channel],
                color=alo_color, label=f"ALO  {alo_time}", linewidth=1.5)

    ax.set_ylabel(ylabel, fontsize=11)
    ax.legend(loc='upper right', fontsize=9)
    ax.tick_params(axis='y', labelsize=10)

    # 弯角虚线
    for d in corner_distances:
        ax.axvline(d, color='grey', linestyle=':', linewidth=0.8, alpha=0.7)

# Gear: integer ticks only
axes[3].yaxis.set_major_locator(ticker.MultipleLocator(1))
axes[3].set_ylim([0.5, 8.5])

# ── X-axis: corner labels ─────────────────────────────────────────────────────
ax_bottom = axes[-1]
ax_bottom.set_xticks(corner_distances)
ax_bottom.set_xticklabels(corner_labels, fontsize=10, rotation=0, ha='center')
ax_bottom.set_xlabel('Corner', fontsize=11)
ax_bottom.tick_params(axis='x', which='both', length=6, labelsize=10)

plt.savefig('/Users/aijian/Downloads/Fast-F1/suzuka_2026_alb_vs_alo.png',
            dpi=150, bbox_inches='tight')
plt.close()
print("Saved: suzuka_2026_alb_vs_alo.png")
