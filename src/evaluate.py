"""
evaluate.py - Compare SurgeSense route flags against what actually happened in Ian.

Uses data/processed/route_flood.csv (flagged = impassable in any advisory)
and config/outcomes.csv (closed_after_ian from Lee County's Oct 1, 2022 list).
Writes data/processed/evaluation.csv and prints a summary.
"""
import pandas as pd

flood = pd.read_csv("data/processed/route_flood.csv")
flood["impassable"] = flood["impassable"].astype(str).str.lower() == "true"
outcomes = pd.read_csv("config/outcomes.csv", encoding="utf-8-sig")

flags = (flood.groupby("route")
         .agg(flagged=("impassable", "any"), max_class=("flood_class", "max"))
         .reset_index())
df = outcomes.merge(flags, on="route", how="left")
df["flagged"] = df["flagged"].fillna(False).astype(bool)
df["closed"] = df["closed_after_ian"].astype(bool)

def label(r):
    if r.flagged and r.closed:
        return "caught"
    if r.flagged and not r.closed:
        return "false alarm"
    if not r.flagged and r.closed:
        return "missed"
    return "correct clear"

df["result"] = df.apply(label, axis=1)
df.to_csv("data/processed/evaluation.csv", index=False)

print(df[["route", "bridge_type", "max_class", "flagged", "closed", "result"]].to_string(index=False))
print()
caught = (df.result == "caught").sum()
closed = df.closed.sum()
false_alarms = (df.result == "false alarm").sum()
print(f"Closures caught: {caught} of {closed}")
print(f"False alarms:    {false_alarms} of {(~df.closed).sum()} routes that stayed open")
print()
print("False alarms by bridge type:")
print(df[df.result == "false alarm"]["bridge_type"].value_counts().to_string())