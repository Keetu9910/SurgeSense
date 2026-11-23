# SurgeSense route risk briefing: Hurricane Ian (2022), Lee County, FL

SurgeSense checks NHC Potential Storm Surge Flooding forecasts (10% exceedance, a reasonable worst case) at each evacuation route. A route counts as impassable only if the forecast water depth reaches the roadway height. SurgeSense compares that with the HURREVAC-style wind-only deadline: tropical-storm wind arrival minus clearance time (41 h, Lee County worst-case in-county clearance).

## Key timeline

- SurgeSense first flagged routes: Sun Sep 25, 11:00 PM EDT (NHC advisory 12)
- Wind-only evacuation deadline: Mon Sep 26, 09:00 AM EDT
- Lee County mandatory evacuation order: Tuesday Sept 27, 2022, morning (approximate)
- Tropical-storm-force winds reached the routes: Wed Sep 28, 02:00 AM EDT
- Ian landfall: Wednesday Sept 28, 2022, afternoon (approximate)

## Route by route

### Sanibel Causeway
- Forecast flooding near route: >6 ft at advisory 12, >9 ft by advisory 25
- Flagged impassable by SurgeSense: Sun Sep 25, 11:00 PM EDT, 10 hours before the wind-only deadline
- Structure: low causeway
- What actually happened: CLOSED after Ian (Lee County Oct 1 2022 closure list; CNN: 3+ sections washed out by surge)

### Fort Myers Beach bridge (Matanzas Pass)
- Forecast flooding near route: >9 ft at advisory 12, >9 ft by advisory 25
- Not flagged impassable: forecast water stays below the roadway (high bridge deck), though approaches could still flood
- Structure: high span (65 ft)
- What actually happened: stayed open (Not on Lee County closed list)

### Bonita Beach Causeway
- Forecast flooding near route: >9 ft at advisory 12, >9 ft by advisory 25
- Flagged impassable by SurgeSense: Sun Sep 25, 11:00 PM EDT, 10 hours before the wind-only deadline
- Structure: low causeway
- What actually happened: CLOSED after Ian (Lee County Oct 1 2022: New Pass / Big Carlos / Big Hickory closed)

### Pine Island / Matlacha bridge
- Forecast flooding near route: >6 ft at advisory 12, >9 ft by advisory 25
- Flagged impassable by SurgeSense: Sun Sep 25, 11:00 PM EDT, 10 hours before the wind-only deadline
- Structure: low approach
- What actually happened: CLOSED after Ian (Lee County Oct 1 2022: three Matlacha bridges closed)

### Cape Coral Bridge
- Forecast flooding near route: >3 ft at advisory 12, >9 ft by advisory 25
- Not flagged impassable: forecast water stays below the roadway (high bridge deck), though approaches could still flood
- Structure: high span
- What actually happened: stayed open (Not on Lee County closed list)

### Midpoint Memorial Bridge
- Forecast flooding near route: >6 ft at advisory 12, >9 ft by advisory 25
- Not flagged impassable: forecast water stays below the roadway (high bridge deck), though approaches could still flood
- Structure: high span (55 ft)
- What actually happened: stayed open (Not on Lee County closed list)

### US-41 Caloosahatchee Bridge
- Forecast flooding near route: >6 ft at advisory 12, >9 ft by advisory 25
- Not flagged impassable: forecast water stays below the roadway (high bridge deck), though approaches could still flood
- Structure: high span (55 ft)
- What actually happened: stayed open (Not on Lee County closed list)

## How accurate was SurgeSense in Ian?

- Elevation-aware rule (current): caught all 3 routes that closed, 0 false alarms.
- Depth-only rule (earlier version): caught all 3, but 4 false alarms, all high-span bridges.

## Limitations

- Flood maps show forecast peak flooding, not the time flooding starts.
- Wind arrival uses the 6-hourly best track; clearance time is a county-wide worst case.
- Low-road heights (3 ft) are assumed, and the elevation rule was chosen after seeing Ian's outcomes; it needs testing on other storms. High-bridge approaches are not yet modeled.
- Lee County's order time is approximate (reported as Tuesday morning).