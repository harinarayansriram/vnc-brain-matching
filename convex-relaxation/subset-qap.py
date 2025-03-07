import csv
import numpy as np
import gurobipy as gp
from collections import defaultdict
from gurobipy import GRB


def parse_graph(filename):
    """Parse graph CSV into outgoing/incoming adjacency dicts."""
    outgoing = defaultdict(dict)
    incoming = defaultdict(dict)
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = int(row['From Node ID'])
            dst = int(row['To Node Id'])
            weight = int(row['Weight'])
            outgoing[src][dst] = weight
            incoming[dst][src] = weight
    return {'outgoing': outgoing, 'incoming': incoming}

def parse_mapping(filename):
    """Parse solution CSV into male->female node mapping."""
    mapping = {}
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            male_id = int(row['Male Node ID'].lstrip('m'))
            female_id = int(row['Female Node ID'].lstrip('f'))
            mapping[male_id] = female_id
    return mapping

def solve_subset_qap(male_graph, female_graph, current_mapping, subset_S, time_limit=300):
    """Solve QAP for a subset of male nodes using Gurobi."""
    # Extract female subset from current mapping
    subset_T = [current_mapping[n] for n in subset_S]
    k = len(subset_S)
    
    # Create index mappings for subset nodes
    male_idx = {n: i for i, n in enumerate(subset_S)}
    female_idx = {n: i for i, n in enumerate(subset_T)}

    # Precompute linear coefficients (external edges)
    linear_coeff = np.zeros((k, k), dtype=int)
    
    # For each male node in subset
    for i_male, male_node in enumerate(subset_S):
        # Handle outgoing external edges
        for dst_male, weight in male_graph['outgoing'][male_node].items():
            if dst_male not in male_idx:  # External edge
                dst_female = current_mapping.get(dst_male, -1)
                if dst_female == -1: continue  # Unmapped node
                
                # Add contribution for all possible female assignments
                for j_female, female_node in enumerate(subset_T):
                    edge_weight = female_graph['outgoing'][female_node].get(dst_female, 0)
                    linear_coeff[i_male, j_female] += min(weight, edge_weight)

        # Handle incoming external edges
        for src_male, weight in male_graph['incoming'][male_node].items():
            if src_male not in male_idx:  # External edge
                src_female = current_mapping.get(src_male, -1)
                if src_female == -1: continue
                
                for j_female, female_node in enumerate(subset_T):
                    edge_weight = female_graph['incoming'][female_node].get(src_female, 0)
                    linear_coeff[i_male, j_female] += min(weight, edge_weight)

    # Build subgraph adjacency matrices
    gm_subset = np.zeros((k, k), dtype=int)
    gf_subset = np.zeros((k, k), dtype=int)
    
    for i, m in enumerate(subset_S):
        for dst, w in male_graph['outgoing'][m].items():
            if dst in male_idx:
                gm_subset[i, male_idx[dst]] = w
                
    for i, f in enumerate(subset_T):
        for dst, w in female_graph['outgoing'][f].items():
            if dst in female_idx:
                gf_subset[i, female_idx[dst]] = w

    # Gurobi model setup
    model = gp.Model("QAP_Subset")
    model.Params.Threads = 14
    model.Params.TimeLimit = time_limit
    model.Params.MIPGap = 0.05

    # Decision variables
    X = model.addVars(k, k, vtype=GRB.BINARY, name="X")

    # Constraints
    for i in range(k):
        model.addConstr(gp.quicksum(X[i,j] for j in range(k)) == 1)
    for j in range(k):
        model.addConstr(gp.quicksum(X[i,j] for i in range(k)) == 1)

    # Objective: Quadratic + Linear terms
    obj = gp.QuadExpr()

    # Quadratic terms (internal edges)
    for i in range(k):
        for m in range(k):
            if gm_subset[i,m] > 0:
                for j in range(k):
                    w = min(gm_subset[i,m], gf_subset[j,female_idx[subset_T[m]]])
                    if w > 0:
                        obj += w * X[i,j] * X[m,female_idx[subset_T[m]]]

    # Linear terms (external edges)
    for i in range(k):
        for j in range(k):
            if linear_coeff[i,j] > 0:
                obj += linear_coeff[i,j] * X[i,j]

    model.setObjective(obj, GRB.MAXIMIZE)
    model.optimize()

    # Extract new mapping
    new_mapping = {}
    if model.status == GRB.OPTIMAL or model.status == GRB.TIME_LIMIT:
        for i in range(k):
            for j in range(k):
                if X[i,j].X > 0.5:
                    new_mapping[subset_S[i]] = subset_T[j]
    return new_mapping

# ========================
# Execution Example
# ========================
if __name__ == "__main__":
    # Load data
    male_graph = parse_graph('../gm.csv')
    female_graph = parse_graph('../gf.csv')
    current_mapping = parse_mapping('../score_lookup/5853909.csv')

    # Select subset (example: first 100 male nodes with mappings)
    subset_S = [n for n in current_mapping.keys() if 15000 <= n <= 15010][:10]
    
    # Solve QAP for subset
    new_mapping = solve_subset_qap(
        male_graph=male_graph,
        female_graph=female_graph,
        current_mapping=current_mapping,
        subset_S=subset_S,
        time_limit=600  # 10 minutes
    )

    # Update global mapping with new assignments
    current_mapping.update(new_mapping)
    print(f"Optimized mapping for {len(new_mapping)} nodes")

    # Write new mapping to file
    with open('new_mapping.csv', 'w', newline='\n') as f:
        writer = csv.writer(f)
        writer.writerow(['Male Node ID', 'Female Node ID'])
        for male_node, female_node in current_mapping.items():
            writer.writerow([f"m{male_node}", f"f{female_node}"])