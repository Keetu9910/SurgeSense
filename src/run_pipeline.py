"""run_pipeline.py - Run the full SurgeSense pipeline in order.

Usage (from the repo root):
    python src/download_ian.py      # once, downloads NHC data (~large)
    python src/run_pipeline.py      # runs every analysis step
    python -m streamlit run src/app.py
"""
import subprocess
import sys

STEPS = [
    "src/flood_check.py",   # flood class per route per advisory
    "src/deadlines.py",     # wind-only deadline vs SurgeSense flag
    "src/evaluate.py",      # compare flags with real Ian closures
    "src/demo_charts.py",   # timeline + heatmap charts
    "src/briefing.py",      # plain-language briefing for the Orchestrate agent
    "src/replay_agent.py",  # advisory-by-advisory alerts (IBM Granite via Ollama, template fallback)
]

for step in STEPS:
    print(f"\n=== {step} ===")
    result = subprocess.run([sys.executable, step])
    if result.returncode != 0:
        sys.exit(f"Step failed: {step}")
print("\nPipeline complete. Launch the dashboard with: python -m streamlit run src/app.py")