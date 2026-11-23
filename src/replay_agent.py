"""
replay_agent.py - SurgeSense advisory replay agent.

Replays NHC advisories in order, detects per-route changes (flood class up or
down, newly impassable, cleared) and issues an alert for county emergency
managers after each advisory that changed something.

Design ("code states the facts, Granite explains them, a checker guards it"):
  1. FACTS: a deterministic sentence built in code lists every changed route,
     its new flood label, impassable status, and time to the wind-only deadline.
     These numbers are always correct.
  2. GUIDANCE: IBM Granite (local, via ollama) writes 1-2 plain-language
     sentences of guidance from the same facts. Granite is told not to use
     numbers.
  3. CHECK: validate_guidance() rejects a draft that contains numbers or calls
     a passable route impassable. After one retry, a fixed template sentence is
     used instead, so no unchecked text reaches an emergency manager.

Writes docs/alerts.md.

Usage:
    python src/replay_agent.py          # Granite guidance if available
    python src/replay_agent.py --no-llm # template guidance only
"""

import argparse
import pathlib
import re

import pandas as pd

FLOOD_CSV = pathlib.Path("data/processed/route_flood.csv")
ADVISORIES_CSV = pathlib.Path("config/advisories.csv")
ROUTES_CSV = pathlib.Path("config/routes.csv")
DEADLINES_CSV = pathlib.Path("data/processed/deadlines.csv")
OUT_MD = pathlib.Path("docs/alerts.md")

EDT = "US/Eastern"
MODEL = "granite4.1:3b"

CLASS_LABEL = {0: "no flooding shown", 1: "0-1 ft", 2: ">1 ft", 3: ">3 ft", 4: ">6 ft", 5: ">9 ft"}
BLOCKING_WORDS = ("impassable", "cut off", "closed", "blocked", "unusable", "flooded out")
OPEN_RE = re.compile(r"\b(passable|open|usable|available)\b")  # \b keeps "impassable" out

SYSTEM_PROMPT = (
    "You advise county emergency managers during a hurricane. You will receive a "
    "list of evacuation routes that are IMPASSABLE and routes that are still PASSABLE "
    "according to a storm-surge forecast. Write 1 or 2 short, plain-language sentences "
    "of guidance. Rules: do not write any numbers or times; describe as impassable, "
    "cut off or closed ONLY the routes in the IMPASSABLE list; do not mention places "
    "that are not in the lists; end by noting that the official makes the final "
    "evacuation decision."
)

TEMPLATE_GUIDANCE = (
    "Residents who depend on the impassable routes should be prioritized while "
    "other routes remain usable. The official makes the final evacuation decision."
)


def short_name(route: str) -> str:
    """Route name without any parenthetical, e.g. 'Fort Myers Beach bridge'."""
    return route.split("(")[0].strip()


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_data():
    flood = pd.read_csv(FLOOD_CSV)
    flood["impassable"] = flood["impassable"].astype(str).str.lower() == "true"

    advisories = pd.read_csv(ADVISORIES_CSV)
    advisories["issued_utc"] = pd.to_datetime(advisories["issued_utc"], utc=True)
    advisories["issued_edt"] = advisories["issued_utc"].dt.tz_convert(EDT)

    routes = pd.read_csv(ROUTES_CSV, encoding="utf-8-sig")
    routes["name"] = routes["name"].str.strip()

    deadlines = pd.read_csv(DEADLINES_CSV)
    deadlines["wind_deadline_utc"] = pd.to_datetime(
        deadlines["wind_deadline_utc"], utc=True, errors="coerce")
    return flood, advisories, routes, deadlines


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------

def detect_changes(current: dict, previous: dict, is_first: bool) -> list[dict]:
    changes = []
    for route, cur in current.items():
        prev = previous.get(route, {})
        old_cls, new_cls = prev.get("flood_class", 0), cur["flood_class"]
        old_imp, new_imp = prev.get("impassable", False), cur["impassable"]
        if not (is_first or old_cls != new_cls or old_imp != new_imp):
            continue
        if is_first:
            kind = "first forecast"
        elif new_imp and not old_imp:
            kind = "newly impassable"
        elif old_imp and not new_imp:
            kind = "no longer impassable"
        elif new_cls > old_cls:
            kind = "flooding forecast worse"
        else:
            kind = "flooding forecast lower"
        changes.append({
            "route": route,
            "kind": kind,
            "old_label": CLASS_LABEL.get(old_cls, str(old_cls)),
            "new_label": CLASS_LABEL.get(new_cls, str(new_cls)),
            "impassable": new_imp,
            "road_height_ft": cur["road_height_ft"],
        })
    return changes


# ---------------------------------------------------------------------------
# Facts (deterministic, always correct)
# ---------------------------------------------------------------------------

def deadline_phrase(hours) -> str:
    if hours is None:
        return "Wind-only deadline timing is unknown."
    if hours >= 0:
        return f"The wind-only evacuation deadline is {hours:.0f} hours away."
    return f"The wind-only evacuation deadline passed {abs(hours):.0f} hours ago."


def facts_text(facts: dict) -> str:
    parts = [f"SurgeSense, NHC advisory {facts['advisory']} ({facts['issued_edt']}):"]
    for c in facts["changes"]:
        status = "IMPASSABLE" if c["impassable"] else "passable"
        if c["kind"] == "first forecast":
            what = f"forecast flooding {c['new_label']}"
        else:
            what = f"{c['kind']} ({c['old_label']} to {c['new_label']})"
        parts.append(f"{c['route']}: {what}, {status} (roadway about {c['road_height_ft']:.0f} ft).")
    if facts["impassable_now"]:
        parts.append("Currently impassable: " + ", ".join(facts["impassable_now"]) + ".")
    parts.append(deadline_phrase(facts["hours_to_deadline"]))
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Granite guidance + validation
# ---------------------------------------------------------------------------

def build_user_msg(facts: dict) -> str:
    imp = facts["impassable_now"] or ["(none)"]
    ok = facts["passable_now"] or ["(none)"]
    timing = "the wind-only deadline has passed" if (facts["hours_to_deadline"] or 0) < 0 \
        else "the wind-only deadline has not passed yet"
    changed = [f"{c['route']}: {c['kind']}" for c in facts["changes"]]
    return (f"IMPASSABLE routes: {'; '.join(imp)}\n"
            f"PASSABLE routes: {'; '.join(ok)}\n"
            f"What changed in this advisory: {'; '.join(changed)}\n"
            f"Timing: {timing}.\n"
            "Write the guidance now as plain sentences (no list, no numbering).")


def validate_guidance(text: str, facts: dict) -> list[str]:
    """Return failure reasons for a Granite guidance draft (empty list = passed)."""
    failures = []
    if not text.strip():
        return ["empty draft"]
    # Ignore list markers such as "1." or "- " at the start of a line.
    clean = re.sub(r"(?m)^\s*(\d+[.)]|[-*])\s+", "", text)
    # 1. No numbers (numbers come only from the facts sentence).
    #    Digits inside road names such as US-41 or I-75 are allowed.
    nums = re.findall(r"(?<![A-Za-z\-\d])\d+", clean)
    if nums:
        failures.append(f"contains numbers: {', '.join(nums)}")
    # 2. A passable route must not be described as blocked. Checked clause by
    #    clause, so "Sanibel is cut off while Cape Coral Bridge stays open" passes.
    clauses = re.split(r"[.;:,]|\bwhile\b|\bbut\b|\bwhereas\b|\bhowever\b", clean.lower())
    for route in facts["passable_now"]:
        name = short_name(route).lower()
        for clause in clauses:
            if name in clause and any(w in clause for w in BLOCKING_WORDS) \
                    and not OPEN_RE.search(clause):
                failures.append(f"passable route described as blocked: {route}")
                break
    # 3. Keep it short.
    if len(re.findall(r"[.!?](\s|$)", clean)) > 3:
        failures.append("too long")
    return failures


def call_granite(user_msg: str, temperature: float = 0.0) -> str:
    import ollama  # imported here so --no-llm never needs it
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": user_msg}],
        options={"num_predict": 120, "temperature": temperature},
    )
    return response.message.content.strip()


def granite_guidance(facts: dict) -> tuple[str, str, bool, list[str]]:
    """Returns (guidance, generator_label, passed, rejected_reasons)."""
    user_msg = build_user_msg(facts)
    reasons: list[str] = []
    for attempt in range(2):
        try:
            # Retry with some randomness; at temperature 0 the retry would repeat the draft.
            draft = call_granite(user_msg, temperature=0.0 if attempt == 0 else 0.7)
        except Exception as exc:  # noqa: BLE001
            return TEMPLATE_GUIDANCE, f"template (Granite unavailable: {exc})", False, reasons
        failures = validate_guidance(draft, facts)
        if not failures:
            label = "IBM Granite" + (" (passed on retry)" if attempt else "")
            return draft, label, True, reasons
        reasons.append(f'"{draft[:160]}" -> ' + "; ".join(failures))
    return TEMPLATE_GUIDANCE, "template (Granite draft failed validation)", False, reasons


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_alerts_md(sections: list[dict]) -> None:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# SurgeSense - Advisory Replay Alerts", "",
             "Each alert = facts sentence (generated by code, always correct) + guidance "
             "(IBM Granite, checked by a validator; template if the check fails).", ""]
    for s in sections:
        lines += [f"## Advisory {s['adv']} - {s['issued_edt']}", "",
                  f"**Facts:** {s['facts_text']}", "",
                  f"**Guidance** *({s['generator']})*: {s['guidance']}", ""]
        if s["rejected"]:
            lines += [f"*Rejected Granite drafts:* {'; '.join(s['rejected'])}", ""]
        lines += ["---", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="SurgeSense advisory replay agent")
    parser.add_argument("--no-llm", action="store_true", help="Template guidance only")
    args = parser.parse_args()

    flood, advisories, routes, deadlines = load_data()
    road_height = dict(zip(routes["name"], routes["road_height_ft"]))
    wind_deadline = deadlines["wind_deadline_utc"].dropna()
    wind_deadline = wind_deadline.min() if len(wind_deadline) else None

    prev_state: dict = {}
    sections: list[dict] = []
    for i, adv in enumerate(sorted(advisories["advisory"].tolist())):
        adv_row = advisories[advisories["advisory"] == adv].iloc[0]
        issued_edt = adv_row["issued_edt"].strftime("%a %b %d, %I:%M %p EDT")
        hours = None if wind_deadline is None else \
            (wind_deadline - adv_row["issued_utc"]).total_seconds() / 3600

        current = {}
        for _, row in flood[flood["advisory"] == adv].iterrows():
            current[row["route"]] = {
                "flood_class": int(row["flood_class"]),
                "impassable": bool(row["impassable"]),
                "road_height_ft": float(road_height.get(row["route"], 3.0)),
            }

        changes = detect_changes(current, prev_state, is_first=(i == 0))
        if changes:
            facts = {
                "advisory": adv,
                "issued_edt": issued_edt,
                "changes": changes,
                "impassable_now": [r for r, s in current.items() if s["impassable"]],
                "passable_now": [r for r, s in current.items() if not s["impassable"]],
                "hours_to_deadline": hours,
            }
            if args.no_llm:
                guidance, gen, passed, rejected = TEMPLATE_GUIDANCE, "template (--no-llm)", None, []
            else:
                guidance, gen, passed, rejected = granite_guidance(facts)
            sections.append({"adv": adv, "issued_edt": issued_edt,
                             "facts_text": facts_text(facts), "guidance": guidance,
                             "generator": gen, "passed": passed, "rejected": rejected})
            tag = "" if passed is None else (" [pass]" if passed else " [fallback]")
            print(f"Adv {adv:2d} ({issued_edt}) - {len(changes)} change(s) | {gen}{tag}")
        prev_state = current

    write_alerts_md(sections)
    print(f"\nWrote {len(sections)} advisory section(s) to {OUT_MD}")
    judged = [s for s in sections if s["passed"] is not None]
    if judged:
        ok = sum(s["passed"] for s in judged)
        print(f"Granite guidance passed validation: {ok}/{len(judged)}, "
              f"template fallback: {len(judged) - ok}/{len(judged)}")


if __name__ == "__main__":
    main()  