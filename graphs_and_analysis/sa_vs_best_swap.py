import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# File paths for SA method and Best Swap method data
sa_file_path = "../score_lookup/from_benchmark_SA_iterations.csv"
best_swap_file_path = "../score_lookup/benchmark_best_swap_mapping_3.csv_iterations.csv"

# -----------------------------
# Load the data
# -----------------------------
sa_df = pd.read_csv(sa_file_path)
best_swap_df = pd.read_csv(best_swap_file_path)

# -----------------------------
# Process SA Method Data
# -----------------------------
# The SA CSV has columns: "10M Iteration", "Time", "Score", "Best Score".
# Compute elapsed time (in minutes) from the 'Time' column (assumed to be a Unix timestamp in seconds).
sa_df['elapsed_min'] = (sa_df['Time'] - sa_df['Time'].iloc[0]) / 60

# -----------------------------
# Process Best Swap Data
# -----------------------------
# The Best Swap CSV now has columns: "Iteration", "Time", "Score", "Best Score".
# Use the row order (or the provided timestamp) to compute elapsed time.
best_swap_df['elapsed_min'] = (best_swap_df['Time'] - best_swap_df['Time'].iloc[0]) / 60

# -----------------------------
# Limit Best Swap Data to the SA Time Interval
# -----------------------------
sa_time_max = sa_df['elapsed_min'].max()
best_swap_df = best_swap_df[best_swap_df['elapsed_min'] <= sa_time_max]

# best_swap_time_max = best_swap_df['elapsed_min'].max()
# sa_df = sa_df[sa_df['elapsed_min'] <= best_swap_time_max]

# -----------------------------
# Plot Both Methods on the Same Graph
# -----------------------------
plt.figure(figsize=(10, 6))
plt.plot(sa_df['elapsed_min'], sa_df['Score'], label='Simulated Annealing', color='blue',
         marker='o', markersize=3, linewidth=1)
plt.plot(best_swap_df['elapsed_min'], best_swap_df['Score'], label='Optimal Swap with ISG Method', color='green',
         marker='x', markersize=3, linewidth=1)
plt.xlabel('Time (minutes)')
plt.ylabel('Score')
plt.title('Score Progress Over ~1 hour: Simulated Annealing vs Optimal Swapping with ISG')
plt.legend()
plt.grid(True)
plt.xlim(0, sa_time_max)
plt.tight_layout()
plt.show()
