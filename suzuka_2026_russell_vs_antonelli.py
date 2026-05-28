"""
2026 Japanese GP (Suzuka) - RUS (Mercedes) vs ANT (Mercedes)
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

rus_lap = session.laps.pick_drivers('RUS').pick_fastest()
ant_lap = session.laps.pick_drivers('ANT').pick_fastest()

rus_tel = rus_lap.get_car_data().add_distance()
ant_tel = ant_lap.get_car_data().add_distance()

circuit_info = session.get_circuit_info()

rus_color = fastf1.plotting.get_driver_color('RUS', session=session)
ant_color = fastf1.plotting.get_driver_color('ANT', session=session)

def fmt_time(td):
    total = int(td.total_seconds())
    ms = int(td.total_seconds() * 1000) % 1000
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}.{ms:03d}"

rus_time = fmt_time(rus_lap['LapTime'])
ant_time = fmt_time(ant_lap['LapTime'])
delta_s = (rus_lap['LapTime'] - ant_lap['LapTime']).total_seconds()
faster = 'RUS' if delta_s < 0 else 'ANT'
delta_str = f"{abs(delta_s):.3f}s  ({faster} faster)"

total_dist = rus_tel['Distance'].max()
n_corners = len(circuit_info.corners)

corner_distances = circuit_info.corners['Distance'].values
if np.isnan(corner_distances).all():
    corner_distances = np.linspace(0, total_dist, n_corners + 1)[1:]

corner_labels = [
    f"T{int(r['Number'])}{r['Letter']}"
    for _, r in circuit_info.corners.iterrows()
]

fig, axes = plt.subplots(4, 1, figsize=(16, 14), sharex=True,
                         gridspec_kw={'height_ratios': [3, 2, 1, 2], 'hspace': 0.08})

fig.suptitle(
    f"2026 Japanese GP — Suzuka  |  Qualifying Fastest Lap\n"
    f"RUS (Mercedes)  {rus_time}   vs   ANT (Mercedes)  {ant_time}   |  Gap: {delta_str}",
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
        ax.step(rus_tel['Distance'], rus_tel[channel],
                color=rus_color, label=f"RUS  {rus_time}", where='post', linewidth=1.5)
        ax.step(ant_tel['Distance'], ant_tel[channel],
                color=ant_color, label=f"ANT  {ant_time}", where='post', linewidth=1.5)
    else:
        ax.plot(rus_tel['Distance'], rus_tel[channel],
                color=rus_color, label=f"RUS  {rus_time}", linewidth=1.5)
        ax.plot(ant_tel['Distance'], ant_tel[channel],
                color=ant_color, label=f"ANT  {ant_time}", linewidth=1.5)

    ax.set_ylabel(ylabel, fontsize=11)
    ax.legend(loc='upper right', fontsize=9)
    ax.tick_params(axis='y', labelsize=10)

    for d in corner_distances:
        ax.axvline(d, color='grey', linestyle=':', linewidth=0.8, alpha=0.7)

axes[3].yaxis.set_major_locator(ticker.MultipleLocator(1))
axes[3].set_ylim([0.5, 8.5])

ax_bottom = axes[-1]
ax_bottom.set_xticks(corner_distances)
ax_bottom.set_xticklabels(corner_labels, fontsize=10, rotation=0, ha='center')
ax_bottom.set_xlabel('Corner', fontsize=11)
ax_bottom.tick_params(axis='x', which='both', length=6, labelsize=10)

plt.savefig('/Users/aijian/Downloads/Fast-F1/suzuka_2026_rus_vs_ant.png',
            dpi=150, bbox_inches='tight')
plt.close()
print("Saved: suzuka_2026_rus_vs_ant.png")
