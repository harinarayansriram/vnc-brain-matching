import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Parameters (you can change these)
max_time = 100  # maximum time in minutes to display in the plot

# File paths for the CSV files
optimized_csv = '../faster_metrics/from_benchmark.csv_iterations.csv'
best_swap_csv = '../score_lookup/benchmark_best_swap_mapping.csv_iterations.csv'

# -------------------------------
# Process Optimized Faster Metrics
# -------------------------------
# Load the CSV (assumes columns: Iteration, Score)
df_optimized = pd.read_csv(optimized_csv)

# Total iterations and total time (in minutes) for the optimized method
total_iterations_opt = 55601  # from iteration 0 to 55601
total_time_opt = 604          # minutes

# Compute time per iteration
time_per_iter_opt = total_time_opt / total_iterations_opt

# Compute effective time (in minutes) for each iteration
df_optimized['Time'] = df_optimized['Iteration'] * time_per_iter_opt

# Filter to only include data up to max_time minutes
df_optimized = df_optimized[df_optimized['Time'] <= max_time]

# -------------------------------
# Process best_swap
# -------------------------------
# Load the CSV (assumes columns: Iteration, Score, Best Score)
df_best_swap = pd.read_csv(best_swap_csv)

# For best_swap, account for the Hungarian algorithm iterations:
# For every 2500 iterations in the CSV, add 2000 extra iterations.
# Define a function to compute effective iteration count:
def compute_effective_iteration(iteration):
    extra_iters = (iteration // 2500) * 2000  # integer division for floor
    return iteration + extra_iters

# Apply the function to compute effective iterations for each row
df_best_swap['EffectiveIteration'] = df_best_swap['Iteration'].apply(compute_effective_iteration)

# Total effective iterations and total time for best_swap
# Final CSV iteration is 5935 so total effective iterations are:
total_effective_iterations_bs = compute_effective_iteration(52500)  # should be 9935
total_time_bs = 508  # minutes

# Compute time per effective iteration
time_per_iter_bs = total_time_bs / total_effective_iterations_bs

# time_per_iter_bs /= 2

# Compute effective time (in minutes) for each row
df_best_swap['Time'] = df_best_swap['EffectiveIteration'] * time_per_iter_bs

# Filter to only include data up to max_time minutes
df_best_swap = df_best_swap[df_best_swap['Time'] <= max_time]

# -------------------------------
# Plotting the results
# -------------------------------
plt.figure(figsize=(10, 6))

# Plot for Optimized Faster Metrics
plt.plot(df_optimized['Time'], df_optimized['Score'], label='Brute force with heuristic', marker='o', markersize=3, linestyle='-')

# Plot for best_swap
plt.plot(df_best_swap['Time'], df_best_swap['Score'], label='Optimal Swap with ISG', marker='s', markersize=3, linestyle='-')

# Formatting the plot
plt.xlabel('Time (minutes)')
plt.ylabel('Score')
plt.title(f'Brute Force vs Optimal Swap for the First {max_time} Minutes')
plt.legend()
plt.grid(True)
plt.xlim(0, max_time)
plt.tight_layout()

plt.show()
