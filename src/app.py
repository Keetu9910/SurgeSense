"""
app.py – SurgeSense Streamlit dashboard.

Flags Lee County evacuation routes whose forecast storm-surge inundation
makes them impassable, and shows how early that warning arrives compared
with the conventional wind-only evacuation deadline.

Run with:  python -m streamlit run src/app.py
"""

import pathlib

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# ---------------------------------------------------------------------------
# Paths (all relative to repo root; Streamlit's cwd is the repo root when
# launched as `streamlit run src/app.py` from that directory)
# ---------------------------------------------------------------------------
ROUTES_CSV    = pathlib.Path("config/routes.csv")
ADVISORIES_CSV = pathlib.Path("config/advisories.csv")
OUTCOMES_CSV  = pathlib.Path("config/outcomes.csv")
FLOOD_CSV     = pathlib.Path("data/processed/route_flood.csv")
DEADLINES_CSV = pathlib.Path("data/processed/deadlines.csv")
EVAL_CSV      = pathlib.Path("data/processed/evaluation.csv")
HEATMAP_PNG   = pathlib.Path("docs/flood_heatmap.png")

EDT = "US/Eastern"

# Flood-class display metadata
CLASS_LABEL = {0: "Dry / no data", 1: "0–1 ft", 2: ">1 ft", 3: ">3 ft", 4: ">6 ft", 5: ">9 ft"}
CLASS_COLOR = {0: "#aaaaaa", 1: "#cccccc", 2: "#a8d8ea", 3: "#f9e04b", 4: "#f4a324", 5: "#d9534f"}


# ---------------------------------------------------------------------------
# Data loading (cached so Streamlit only reads once)
# ---------------------------------------------------------------------------

@st.cache_data
def load_data():
    routes     = pd.read_csv(ROUTES_CSV, encoding="utf-8-sig")
    routes["name"] = routes["name"].str.strip()

    advisories = pd.read_csv(ADVISORIES_CSV)
    advisories["issued_utc"] = pd.to_datetime(advisories["issued_utc"], utc=True)
    advisories["issued_edt"] = advisories["issued_utc"].dt.tz_convert(EDT)

    outcomes   = pd.read_csv(OUTCOMES_CSV, encoding="utf-8-sig")
    outcomes["route"] = outcomes["route"].str.strip()

    flood      = pd.read_csv(FLOOD_CSV)
    flood["impassable"]            = flood["impassable"].astype(str).str.lower() == "true"
    flood["impassable_depth_only"] = flood["impassable_depth_only"].astype(str).str.lower() == "true"

    deadlines  = pd.read_csv(DEADLINES_CSV)
    for col in ["surge_flag_utc", "wind_arrival_utc", "wind_deadline_utc"]:
        deadlines[col] = pd.to_datetime(deadlines[col], utc=True, errors="coerce")
    for col in ["surge_flag_utc", "wind_arrival_utc", "wind_deadline_utc"]:
        deadlines[col + "_edt"] = deadlines[col].dt.tz_convert(EDT)

    evaluation = pd.read_csv(EVAL_CSV)

    return routes, advisories, outcomes, flood, deadlines, evaluation


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.set_page_config(page_title="SurgeSense", layout="wide")

routes, advisories, outcomes, flood, deadlines, evaluation = load_data()

# --- Title ---
st.title("🌊 SurgeSense")
st.caption(
    "Flags evacuation routes that forecast storm surge will cut off, "
    "compared with the conventional wind-only evacuation deadline — "
    "demonstrated on Hurricane Ian (2022), Lee County, FL."
)

# --- Sidebar ---
st.sidebar.header("Controls")

adv_list = sorted(advisories["advisory"].tolist())
adv_sel = st.sidebar.select_slider(
    "NHC Advisory",
    options=adv_list,
    value=adv_list[0],
    format_func=lambda x: f"Adv {x}",
)

adv_row  = advisories[advisories["advisory"] == adv_sel].iloc[0]
adv_time = adv_row["issued_edt"]
st.sidebar.markdown(f"**Issued:** {adv_time.strftime('%b %d, %Y %H:%M EDT')}")

elev_aware = st.sidebar.toggle("Elevation-aware rule", value=True)
impassable_col = "impassable" if elev_aware else "impassable_depth_only"
rule_label     = "elevation-aware" if elev_aware else "depth-only (class ≥ 2)"

st.sidebar.markdown(
    f"**Active rule:** {rule_label}  \n"
    "Elevation-aware = impassable only if flood depth lower bound ≥ road height.  \n"
    "Depth-only = impassable at any class ≥ 2 (>1 ft above ground)."
)

st.sidebar.markdown(
    "**Key times (EDT)**  \n"
    "SurgeSense flag: Sun 9/25, 11 PM  \n"
    "Wind-only deadline: Mon 9/26, 9 AM  \n"
    "Lee County order: Tue 9/27, morning (approx.)"
)

# ---------------------------------------------------------------------------
# Filter flood to selected advisory
# ---------------------------------------------------------------------------
adv_flood = flood[flood["advisory"] == adv_sel].copy()
adv_flood = adv_flood.merge(routes[["name", "lat", "lon", "road_height_ft"]], left_on="route", right_on="name", how="left")
adv_flood = adv_flood.merge(outcomes[["route", "bridge_type", "closed_after_ian"]], on="route", how="left")

# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------
st.subheader(f"Route Status — Advisory {adv_sel}")

m = folium.Map(location=[26.55, -81.95], zoom_start=10, tiles="OpenStreetMap")

for _, row in adv_flood.iterrows():
    cls    = int(row["flood_class"]) if pd.notna(row["flood_class"]) else 0
    color  = CLASS_COLOR.get(cls, "#aaaaaa")
    imp    = bool(row[impassable_col])
    closed = int(row["closed_after_ian"]) if pd.notna(row["closed_after_ian"]) else 0

    popup_html = (
        f"<b>{row['route']}</b><br>"
        f"Flood class: {cls} ({CLASS_LABEL.get(cls, '?')})<br>"
        f"Road height: {row['road_height_ft']:.0f} ft<br>"
        f"Impassable ({rule_label}): {'⚠️ Yes' if imp else '✅ No'}<br>"
        f"Actual closure after Ian: {'🔴 Closed' if closed else '🟢 Open'}"
    )

    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=12,
        color="#111111" if imp else color,
        weight=3 if imp else 1,
        fill=True,
        fill_color=color,
        fill_opacity=0.85,
        popup=folium.Popup(popup_html, max_width=260),
        tooltip=row["route"],
    ).add_to(m)

# Legend as a fixed HTML element
legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:9999;background:white;
     padding:10px 14px;border:1px solid #ccc;border-radius:6px;font-size:12px;line-height:1.8">
<b>Flood class</b><br>
<span style="color:#aaaaaa">■</span> 0–1 Dry / 0–1 ft &nbsp;
<span style="color:#a8d8ea">■</span> 2 &gt;1 ft<br>
<span style="color:#f9e04b">■</span> 3 &gt;3 ft &nbsp;
<span style="color:#f4a324">■</span> 4 &gt;6 ft &nbsp;
<span style="color:#d9534f">■</span> 5 &gt;9 ft<br>
<b>Black outline</b> = impassable under chosen rule
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

st_folium(m, width="100%", height=480)

# ---------------------------------------------------------------------------
# Metric cards
# ---------------------------------------------------------------------------
n_impassable = int(adv_flood[impassable_col].sum())

result_col  = "result_elev" if elev_aware else "result_depth"
caught_n    = int((evaluation[result_col] == "caught").sum())
fa_n        = int((evaluation[result_col] == "false alarm").sum())
closed_n    = int(evaluation["closed"].sum())

# Lead hours: average of non-NaN flagged routes under elevation-aware rule
# (lead_hours in deadlines.csv was computed from impassable, so use as-is)
lead_vals = deadlines["lead_hours"].dropna()
avg_lead  = lead_vals.mean() if len(lead_vals) > 0 else float("nan")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Routes impassable", f"{n_impassable} / {len(adv_flood)}", help=f"At advisory {adv_sel} under {rule_label} rule")
col2.metric("Avg lead vs wind deadline", f"{avg_lead:.1f} h" if not pd.isna(avg_lead) else "N/A", help="Hours SurgeSense flagged route before wind-only deadline (flagged routes only)")
col3.metric("Closures caught", f"{caught_n} / {closed_n}", help=f"Routes Ian actually closed, correctly flagged ({rule_label})")
col4.metric("False alarms", str(fa_n), help=f"Routes flagged but not closed by Ian ({rule_label})")

# ---------------------------------------------------------------------------
# Deadlines table
# ---------------------------------------------------------------------------
st.subheader("Evacuation Deadlines (EDT)")

dl_display = deadlines[[
    "route", "surge_flag_utc_edt", "wind_deadline_utc_edt", "wind_arrival_utc_edt", "lead_hours"
]].copy()
dl_display.columns = ["Route", "Surge flag (EDT)", "Wind deadline (EDT)", "34-kt arrival (EDT)", "Lead (h)"]

for col in ["Surge flag (EDT)", "Wind deadline (EDT)", "34-kt arrival (EDT)"]:
    dl_display[col] = dl_display[col].apply(
        lambda x: x.strftime("%b %d %H:%M") if pd.notna(x) else "—"
    )
dl_display["Lead (h)"] = dl_display["Lead (h)"].apply(
    lambda x: f"{x:.1f}" if pd.notna(x) else "—"
)

st.dataframe(dl_display, width="stretch", hide_index=True)

# ---------------------------------------------------------------------------
# Evaluation table
# ---------------------------------------------------------------------------
st.subheader("Evaluation: Both Rules Side by Side")

ev_display = evaluation[[
    "route", "bridge_type", "max_class", "closed", result_col
]].copy()
ev_display.columns = ["Route", "Bridge type", "Max class", "Closed by Ian", "Result"]
ev_display["Closed by Ian"] = ev_display["Closed by Ian"].map({True: "Yes", False: "No"})

def result_badge(val):
    colors = {
        "caught":        "background-color:#d4edda;color:#155724",
        "missed":        "background-color:#f8d7da;color:#721c24",
        "false alarm":   "background-color:#fff3cd;color:#856404",
        "correct clear": "background-color:#e2e3e5;color:#383d41",
    }
    return colors.get(val, "")

st.dataframe(
    ev_display.style.map(result_badge, subset=["Result"]),
    width="stretch",
    hide_index=True,
)

# ---------------------------------------------------------------------------
# Heatmap image
# ---------------------------------------------------------------------------
st.subheader("Inundation Heatmap (all advisories)")
if HEATMAP_PNG.exists():
    st.image(str(HEATMAP_PNG), width="stretch")
else:
    st.info("docs/flood_heatmap.png not found.")

# ---------------------------------------------------------------------------
# Limitations
# ---------------------------------------------------------------------------
st.subheader("Limitations")
st.markdown("""
- **Road height estimates for low causeways (~3 ft) are assumptions**, not surveyed values.
  Actual roadway elevation varies along each causeway.
- **High-bridge approach flooding is not modeled.** Even with high deck clearance, the
  low-lying approach roads at the foot of a bridge can flood from surge, potentially
  cutting off access before the deck itself is threatened.
- NHC inundation maps show **forecast peak flooding** at each advisory (a 1-in-10 worst case),
  not the time flooding starts.
- 34-kt wind arrival resolution is 6-hourly (NHC best-track synoptic times).
- This dashboard covers only Hurricane Ian (2022) and Lee County, FL routes.
""")