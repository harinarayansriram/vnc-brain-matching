import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from numpy.polynomial.polynomial import Polynomial
from sklearn.metrics import r2_score
from scipy.optimize import curve_fit

# File paths
input_file_path = "Times for Hungarian.csv"
output_file_path = "bench_map_filtered.csv"
mosek_file_path = "Times for QAP Methods.csv"
sa_file_path = "../score_lookup/from_benchmark_SA_iterations.csv"

# Load data
df = pd.read_csv(input_file_path)
mosek_df = pd.read_csv(mosek_file_path)
sa_df = pd.read_csv(sa_file_path)

# Drop missing values from MOSEK data
mosek_df = mosek_df.dropna()

# Filter for k <= 800
filtered_df = df[df['k'] <= 800]
mosek_df = mosek_df[mosek_df['Subset size'] <= 800]

# Fit a cubic regression model
coeffs = np.polyfit(filtered_df['k'], filtered_df['time_seconds'], 3)
cubic_poly = np.poly1d(coeffs)

# Predict values using cubic regression
predicted_times = cubic_poly(filtered_df['k'])

# Compute residuals and filter out outliers using standard deviation threshold
residuals = filtered_df['time_seconds'] - predicted_times
std_dev = np.std(residuals)
filtered_df = filtered_df[np.abs(residuals) <= 2 * std_dev]

# Save filtered data to a new file
filtered_df.to_csv(output_file_path, index=False)

# Refit cubic regression on filtered data
coeffs_filtered = np.polyfit(filtered_df['k'], filtered_df['time_seconds'], 3)
cubic_poly_filtered = np.poly1d(coeffs_filtered)

# Compute R^2 score
r2 = r2_score(filtered_df['time_seconds'], cubic_poly_filtered(filtered_df['k']))

# Generate regression equation string with significant terms only
terms = [f"{coeff:.6f}x^{i}" for i, coeff in enumerate(coeffs_filtered) if abs(coeff) > 1e-6]
equation = "y = " + " + ".join(terms)
legend_label = f"{equation}\nR^2 = {r2:.6f}"

# Generate smooth values for plotting
k_smooth = np.linspace(filtered_df['k'].min(), filtered_df['k'].max(), 800)
time_smooth_filtered = cubic_poly_filtered(k_smooth)

# Exponential regression function
def exp_func(x, a, b, c):
    return a * np.exp(b * x) + c

# Fit exponential regression to MOSEK data with better constraints
popt, _ = curve_fit(exp_func, mosek_df['Subset size'], mosek_df['Time MOSEK (s)'], 
                     p0=(1, 0.01, 1), bounds=([0, 0, 0], [np.inf, np.inf, np.inf]), maxfev=10000)

# Generate smooth values for exponential regression
mosek_smooth = np.linspace(mosek_df['Subset size'].min(), mosek_df['Subset size'].max(), 800)
mosek_exp_fit = exp_func(mosek_smooth, *popt)

# Generate equation string for exponential fit
equation_mosek = f"y = {popt[0]:.6f} * exp({popt[1]:.6f} * x) + {popt[2]:.6f}"
legend_label_mosek = f"{equation_mosek}"

# Plot comparison of ISG vs MOSEK
plt.figure(figsize=(8, 5))
plt.scatter(filtered_df['k'], filtered_df['time_seconds'], color='b', label='Indep. Subset Greedy')
plt.plot(k_smooth, time_smooth_filtered, color='r', label=legend_label)
plt.scatter(mosek_df['Subset size'], mosek_df['Time MOSEK (s)'], color='g', label='MOSEK Solver')
plt.plot(mosek_smooth, mosek_exp_fit, color='orange', linestyle='dashed', label=legend_label_mosek)
plt.xlabel('k')
plt.ylabel('Time (seconds)')
plt.title('Runtime Comparison of ISG vs MOSEK (k <= 800)')
plt.legend()
plt.grid()
plt.show()