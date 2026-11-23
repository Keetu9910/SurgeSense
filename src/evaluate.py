"""
evaluate.py - Compare SurgeSense route flags against what actually happened in Ian.

Reports results for two flagging rules side by side:
  - elevation-aware : impassable = flood depth lower bound >= road_height_ft
  - depth-only      : original rule, impassable = class >= 2 (>1 ft above ground)

Uses data/processed/route_flood.csv and config/outcomes.csv.
Writes data/processed/evaluation.csv and prints a summary.
"""
import pandas as pd

flood = pd.read_csv("data/processed/route_flood.csv", encoding="utf-8-sig")
flood["impassable"]            = flood["impassable"].astype(str).str.lower() == "true"
flood["impassable_depth_only"] = flood["impassable_depth_only"].astype(str).str.lower() == "true"

outcomes = pd.read_csv("config/outcomes.csv", encoding="utf-8-sig")

# Aggregate per route for each rule
flags = (
    flood.groupby("route")
    .agg(
        flagged=("impassable",            "any"),
        flagged_depth_only=("impassable_depth_only", "any"),
        max_class=("flood_class", "max"),
    )
    .reset_index()
)

df = outcomes.merge(flags, on="route", how="left")
df["flagged"]            = df["flagged"].fillna(False).astype(bool)
df["flagged_depth_only"] = df["flagged_depth_only"].fillna(False).astype(bool)
df["closed"]             = df["closed_after_ian"].astype(bool)


def label(flagged: bool, closed: bool) -> str:
    if flagged and closed:
        return "caught"
    if flagged and not closed:
        return "false alarm"
    if not flagged and closed:
        return "missed"
    return "correct clear"


df["result_elev"]  = df.apply(lambda r: label(r.flagged,            r.closed), axis=1)
df["result_depth"] = df.apply(lambda r: label(r.flagged_depth_only, r.closed), axis=1)

df.to_csv("data/processed/evaluation.csv", index=False)

# --- Print side-by-side comparison ---
print(
    df[[
        "route", "bridge_type", "max_class", "closed",
        "result_elev", "result_depth",
    ]].to_string(index=False)
)
print()


def summary(result_col: str, label_str: str) -> None:
    caught       = (df[result_col] == "caught").sum()
    closed       = df["closed"].sum()
    false_alarms = (df[result_col] == "false alarm").sum()
    missed       = (df[result_col] == "missed").sum()
    open_routes  = (~df["closed"]).sum()
    print(f"[{label_str}]")
    print(f"  Closures caught : {caught} of {closed}")
    print(f"  Missed          : {missed} of {closed}")
    print(f"  False alarms    : {false_alarms} of {open_routes} routes that stayed open")
    fa_types = df[df[result_col] == "false alarm"]["bridge_type"].value_counts()
    if not fa_types.empty:
        print("  False alarms by bridge type:")
        for bt, cnt in fa_types.items():
            print(f"    {bt}: {cnt}")
    print()


summary("result_elev",  "elevation-aware rule")
summary("result_depth", "depth-only rule     ")
