import csv
import jax.numpy as jnp
from jax import jit

# Function to read the mapping file.
def read_mapping(filename):
    mapping = {}
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Remove the "m" and "f" prefixes and convert to int.
            male_id = int(row["Male Node ID"].lstrip("mM"))
            female_id = int(row["Female Node ID"].lstrip("fF"))
            mapping[male_id] = female_id
    return mapping

# Function to read connectome edge files.
def read_edges(filename):
    edges = {}
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            u = int(row["From Node ID"])
            v = int(row["To Node Id"])
            weight = float(row["Weight"])
            edges[(u, v)] = weight
    return edges

# Smooth minimum using log-sum-exp.
def smooth_min(a, b, rho=50.0):
    return -1.0 / rho * jnp.log(jnp.exp(-rho * a) + jnp.exp(-rho * b))

# Compute the alignment score given a mapping and the edge dictionaries.
def compute_alignment_score(mapping, male_edges, female_edges, rho=50.0):
    total_score = 0.0
    for (u, v), w_m in male_edges.items():
        # Find corresponding female nodes via the mapping.
        f_u = mapping.get(u)
        f_v = mapping.get(v)
        if f_u is None or f_v is None:
            # If one of the nodes isn’t mapped, treat the female weight as 0.
            w_f = 0.0
        else:
            w_f = female_edges.get((f_u, f_v), 0.0)
        total_score += smooth_min(w_m, w_f, rho)
    return total_score

# Optionally compile the alignment score function with JAX.
compute_alignment_score_jit = jit(compute_alignment_score)

if __name__ == '__main__':
    # File paths for the mapping and the connectomes.
    mapping_file = '../score_lookup/5853925.csv'
    gm_file = '../gm.csv'
    gf_file = '../gf.csv'
    
    # Read in the data.
    mapping = read_mapping(mapping_file)
    male_edges = read_edges(gm_file)
    female_edges = read_edges(gf_file)
    
    # Set the smoothing parameter (adjust as needed)
    rho = 50.0
    
    # Compute the alignment score (using the JIT-compiled version if desired).
    score = compute_alignment_score_jit(mapping, male_edges, female_edges, rho)
    print("Alignment score:", score)
