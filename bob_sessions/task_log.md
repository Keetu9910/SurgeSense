TASK 1:
Route flood check. Bob wrote src/flood_check.py, which reads NHC's Potential Storm Surge Flooding rasters for advisories 12 through 25 and records the highest flood class near each evacuation route. Bob worked out the window math so the script reads only a small patch around each route instead of loading the full 49,000 by 45,000 pixel coastal raster.
![alt text](image.png)
![alt text](image-1.png)

TASK 2:
Deadline comparison. Before writing any code, Bob inspected Ian's best-track archive, found the wind radii layer, and confirmed its time format. It then wrote src/deadlines.py, which finds when 34-knot winds reached each route, sets the wind-only deadline 41 hours earlier, measures how far ahead SurgeSense's warning came, and draws docs/timeline.png
![alt text](image.png)
![alt text](image-1.png)
![alt text](image-2.png)

TASK 3:
Elevation-aware rule. Our evaluation showed four false alarms, all on high-span bridges, so Bob changed the rule so that a route counts as impassable only when forecast water reaches the roadway. It kept the old depth-only rule for comparison and updated src/evaluate.py to report both. In the Ian replay, the new rule caught all three real closures with no false alarms.
![alt text](image-3.png)
![alt text](image-4.png)
![alt text](image-5.png)

TASK 4:
Interactive dashboard. Bob built src/app.py, a Streamlit and Folium dashboard with an advisory slider, a toggle between the two rules, a map of the routes, metric cards, and the deadline and evaluation tables.
![alt text](image-6.png)
![alt text](image-7.png)
![alt text](image-8.png)

TASK 5:
Replay agent with IBM Granite. Bob built the first version of src/replay_agent.py, which replays Ian advisory by advisory, detects changes on each route, and asks IBM Granite (run locally through Ollama) to write an alert, falling back to a template if Granite is unavailable.
![alt text](image-9.png)
![alt text](image-10.png)
![alt text](image-11.png)

TASK 6: 
Alert validation. Bob added a validator and a retry for Granite's drafts, then debugged three real problems: route names with parentheses not matching Granite's wording, numbers inside road names like "US-41" being flagged as invented, and emoji crashing the Windows console.
![alt text](image-12.png)
![alt text](image-13.png)
![alt text](image-14.png)
![alt text](image-15.png)
![alt text](image-16.png)

Review and later changes. We reviewed every Bob change before running it and denied any command that tried to read the large raw data files. A few issues were fixed by hand after review: a pandas method removed in newer versions, map tiles that now require an API key, and an inaccurate note about flood timing. The final version of replay_agent.py, where code writes the facts, Granite writes the guidance, and a clause-level checker reviews it, was revised outside Bob after these sessions.

