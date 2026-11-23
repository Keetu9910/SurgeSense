"""demo_charts.py - Presentation charts: timeline with Lee County's order, and flood-class heatmap."""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import ListedColormap, BoundaryNorm

EDT = "America/New_York"
d = pd.read_csv("data/processed/deadlines.csv",
                parse_dates=["surge_flag_utc", "wind_deadline_utc", "wind_arrival_utc"])
r = d.iloc[0]  # all routes share the same times
events = [
    ("SurgeSense flags all 7 routes\n(NHC advisory 12)", r.surge_flag_utc, "#e05c2a"),
    ("Wind-only deadline\n(TS winds - 41 h clearance)", r.wind_deadline_utc, "#2a6ee0"),
    ("Lee County mandatory order\n(Tue morning, approx.)", pd.Timestamp("2022-09-27T14:00Z"), "#7a3db8"),
    ("Tropical-storm winds arrive", r.wind_arrival_utc, "#2ab05c"),
    ("Ian landfall (approx.)", pd.Timestamp("2022-09-28T19:00Z"), "#555555"),
]

# 1) Simple event timeline
fig, ax = plt.subplots(figsize=(12, 3.6))
for i, (label, t, c) in enumerate(events):
    t = t.tz_convert(EDT)
    ax.axvline(t, color=c, lw=2)
    ax.text(t, 1.02 - (i % 2) * 0.32, " " + label, color=c, fontsize=9, va="top", ha="left",
            transform=ax.get_xaxis_transform())
ax.set_yticks([])
ax.set_xlim(pd.Timestamp("2022-09-25T20:00", tz=EDT), pd.Timestamp("2022-09-28T20:00", tz=EDT))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %m/%d\n%I %p", tz=EDT))
ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 12], tz=EDT))
ax.set_title("Hurricane Ian, Lee County: SurgeSense warned before the wind-only deadline (times EDT)", fontsize=11)
for s in ["left", "right", "top"]:
    ax.spines[s].set_visible(False)
plt.tight_layout()
fig.savefig("docs/demo_timeline.png", dpi=160)

# 2) Flood-class heatmap
f = pd.read_csv("data/processed/route_flood.csv")
grid = f.pivot(index="route", columns="advisory", values="flood_class")
cmap = ListedColormap(["#f2f2f2", "#cfe3f7", "#7fb3e6", "#f2c14e", "#f08a3c", "#d7301f"])
norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5], cmap.N)
fig, ax = plt.subplots(figsize=(12, 4))
im = ax.imshow(grid.values, cmap=cmap, norm=norm, aspect="auto")
ax.set_xticks(range(len(grid.columns)), [f"Adv {a}" for a in grid.columns], fontsize=8)
ax.set_yticks(range(len(grid.index)), grid.index, fontsize=8)
cb = fig.colorbar(im, ticks=range(6))
cb.ax.set_yticklabels(["none", "0-1 ft", ">1 ft", ">3 ft", ">6 ft", ">9 ft"], fontsize=8)
ax.set_title("Forecast flooding near each evacuation route, by NHC advisory (Hurricane Ian)", fontsize=11)
plt.tight_layout()
fig.savefig("docs/flood_heatmap.png", dpi=160)
print("Wrote docs/demo_timeline.png and docs/flood_heatmap.png")