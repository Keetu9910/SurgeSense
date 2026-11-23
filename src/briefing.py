"""briefing.py - Turn SurgeSense results into a plain-language briefing for the Orchestrate agent."""
import pandas as pd

EDT = "America/New_York"
d = pd.read_csv("data/processed/deadlines.csv",
                parse_dates=["surge_flag_utc", "wind_deadline_utc", "wind_arrival_utc"])
f = pd.read_csv("data/processed/route_flood.csv")
e = pd.read_csv("data/processed/evaluation.csv")
labels = {0: "none", 1: "0-1 ft", 2: ">1 ft", 3: ">3 ft", 4: ">6 ft", 5: ">9 ft"}
fmt = lambda t: t.tz_convert(EDT).strftime("%a %b %d, %I:%M %p EDT")

lines = ["# SurgeSense route risk briefing: Hurricane Ian (2022), Lee County, FL", "",
         "SurgeSense checks NHC Potential Storm Surge Flooding forecasts (10% exceedance, "
         "a reasonable worst case) at each evacuation route, and compares them with the "
         "HURREVAC-style wind-only deadline: tropical-storm wind arrival minus clearance time "
         "(41 h, Lee County worst-case in-county clearance).", "",
         "## Key timeline", ""]
r = d.iloc[0]
lines += [f"- SurgeSense first flagged routes: {fmt(r.surge_flag_utc)} (NHC advisory 12)",
          f"- Wind-only evacuation deadline: {fmt(r.wind_deadline_utc)}",
          "- Lee County mandatory evacuation order: Tuesday Sept 27, 2022, morning (approximate)",
          f"- Tropical-storm-force winds reached the routes: {fmt(r.wind_arrival_utc)}",
          "- Ian landfall: Wednesday Sept 28, 2022, afternoon (approximate)", "",
          "## Route by route", ""]
for _, row in d.iterrows():
    rf = f[f.route == row.route].sort_values("advisory")
    first, last = rf.iloc[0], rf.iloc[-1]
    ev = e[e.route == row.route].iloc[0]
    lines += [f"### {row.route}",
              f"- Forecast flooding: {labels[first.flood_class]} at advisory {first.advisory}, "
              f"{labels[last.flood_class]} by advisory {last.advisory}",
              f"- Flagged impassable by SurgeSense: {fmt(row.surge_flag_utc)}, "
              f"{row.lead_hours:.0f} hours before the wind-only deadline",
              f"- Structure: {ev.bridge_type}",
              f"- What actually happened: {'CLOSED after Ian' if ev.closed else 'stayed open'} "
              f"({ev.source})",
              f"- Evaluation: {ev.result}", ""]
lines += ["## Limitations", "",
          "- Flood maps show forecast peak flooding, not the time flooding starts.",
          "- Wind arrival uses the 6-hourly best track; clearance time is a county-wide worst case.",
          "- Flood depth alone over-flags high bridges: all 4 false alarms were high-span bridges. "
          "Next step: account for road elevation and train on more storms.",
          "- Lee County's order time is approximate (reported as Tuesday morning)."]
open("docs/surgesense_briefing.md", "w", encoding="utf-8").write("\n".join(lines))
print("Wrote docs/surgesense_briefing.md")