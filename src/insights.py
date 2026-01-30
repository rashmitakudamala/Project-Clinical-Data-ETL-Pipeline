# src/insights.py

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Data for the bar chart
# ----------------------------------
# For the selected patient:
# - OpenEMR: 1 Condition, 0 Observations, 0 Procedures
# - Primary FHIR (after ETL): 2 Conditions, 1 Observation, 1 Procedure
labels = ["Condition", "Observation", "Procedure"]
openemr_counts = [1, 0, 0]
primary_counts = [2, 1, 1]

x = np.arange(len(labels))   # label locations
width = 0.35                 # width of the bars

fig, ax = plt.subplots(figsize=(6, 4))

ax.bar(x - width/2, openemr_counts, width, label="OpenEMR (source)")
ax.bar(x + width/2, primary_counts, width, label="Primary FHIR (after ETL)")

ax.set_ylabel("Number of resources")
ax.set_title("Resources for one patient: source vs after ETL")
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
ax.grid(axis="y", linestyle="--", alpha=0.3)

fig.tight_layout()

# Save into assets/resource_etl_bar.png
# ----------------------------------
project_root = Path(__file__).resolve().parent.parent
assets_dir = project_root / "assets"
assets_dir.mkdir(exist_ok=True)

out_path = assets_dir / "resource_etl_bar.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")

print(f"Saved bar chart to: {out_path}")
