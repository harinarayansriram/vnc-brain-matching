import csv
import numpy as np
from collections import defaultdict
import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import random
import sys

def compare_mappings(optimized_file, reference_file):
    """Compare two mapping files and report discrepancies."""
    # Load mappings
    optimized = parse_mapping(optimized_file)
    reference = parse_mapping(reference_file)

    differences = []
    stats = {
        'total_nodes': 0,
        'matching': 0,
        'conflicting': 0,
        'missing_in_optimized': 0,
        'missing_in_reference': 0
    }

    # Check all reference entries
    for male_node, ref_female in reference.items():
        stats['total_nodes'] += 1
        opt_female = optimized.get(male_node)

        if opt_female is None:
            differences.append(('MISSING_IN_OPTIMIZED', male_node, None, ref_female))
            stats['missing_in_optimized'] += 1
        elif opt_female != ref_female:
            differences.append(('CONFLICT', male_node, opt_female, ref_female))
            stats['conflicting'] += 1
        else:
            stats['matching'] += 1

    # Find nodes missing in reference
    for male_node in optimized:
        if male_node not in reference:
            differences.append(('MISSING_IN_REFERENCE', male_node, optimized[male_node], None))
            stats['missing_in_reference'] += 1

    # Write differences to CSV
    # with open(output_diff_file, 'w') as f:
    #     writer = csv.writer(f)
    #     writer.writerow(['Issue Type', 'Male Node', 'Optimized Female', 'Reference Female'])
    #     writer.writerows(differences)

    # Print summary
    print(f"""
    Mapping Comparison Report:
    - Total nodes in reference: {stats['total_nodes']}
    - Matching assignments: {stats['matching']} ({stats['matching']/stats['total_nodes']:.1%})
    - Conflicting assignments: {stats['conflicting']}
    - Nodes missing in optimized: {stats['missing_in_optimized']}
    - Nodes missing in reference: {stats['missing_in_reference']}
    """)

    # return differences
    return stats['conflicting'] != 0


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

def sort_nodes_by_degree(graph):
    """Sort nodes by degree in descending order."""
    degrees = {n: sum(graph['outgoing'][n].values()) for n in graph['outgoing']}
    return sorted(degrees, key=degrees.get, reverse=True)

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

def create_scip_qap_model(male_graph, female_graph, current_mapping, subset_S):
    """Create Pyomo model optimized for SCIP with non-convex handling."""
    subset_T = [current_mapping[n] for n in subset_S]
    k = len(subset_S)

    # Create index mappings
    male_idx = {n: i for i, n in enumerate(subset_S)}
    female_idx = {n: i for i, n in enumerate(subset_T)}

    # Precompute coefficients using sparse storage
    linear_terms = []
    quadratic_terms = []

    # Calculate linear coefficients (external edges)
    for i_male, male_node in enumerate(subset_S):
        # Outgoing external edges
        for dst_male, weight in male_graph['outgoing'][male_node].items():
            if dst_male not in male_idx:
                dst_female = current_mapping.get(dst_male, -1)
                if dst_female == -1: continue

                for j_female, female_node in enumerate(subset_T):
                    edge_weight = female_graph['outgoing'][female_node].get(dst_female, 0)
                    if edge_weight > 0:
                        linear_terms.append((i_male, j_female, min(weight, edge_weight)))

        # Incoming external edges
        for src_male, weight in male_graph['incoming'][male_node].items():
            if src_male not in male_idx:
                src_female = current_mapping.get(src_male, -1)
                if src_female == -1: continue

                for j_female, female_node in enumerate(subset_T):
                    edge_weight = female_graph['incoming'][female_node].get(src_female, 0)
                    if edge_weight > 0:
                        linear_terms.append((i_male, j_female, min(weight, edge_weight)))

    # Build subgraph adjacency matrices using sparse representation
    quad_dict = defaultdict(float)
    for i, m in enumerate(subset_S):
        for dst, w_m in male_graph['outgoing'][m].items():
            if dst not in male_idx: continue
            m_idx = male_idx[dst]
            for j, f in enumerate(subset_T):
                for f_dst, w_f in female_graph['outgoing'][f].items():
                    if f_dst not in female_idx: continue
                    n_idx = female_idx[f_dst]
                    weight = min(w_m, w_f)
                    if weight > 0:
                        quad_dict[(i, j, m_idx, n_idx)] += weight

    # Create Pyomo model
    model = pyo.ConcreteModel()

    # Sets for indices
    model.I = pyo.Set(initialize=range(k))
    model.J = pyo.Set(initialize=range(k))

    # Binary decision variables with warm start
    model.X = pyo.Var(model.I, model.J, domain=pyo.Binary,
                     initialize=lambda m, i, j: 1 if (i == j) else 0)

    # Assignment constraints
    def row_constraint_rule(model, i):
        return sum(model.X[i,j] for j in model.J) == 1
    model.row_constraints = pyo.Constraint(model.I, rule=row_constraint_rule)

    def col_constraint_rule(model, j):
        return sum(model.X[i,j] for i in model.I) == 1
    model.col_constraints = pyo.Constraint(model.J, rule=col_constraint_rule)

    # Force at least one assignment to change from the initial (warm-start) solution.
    def nontrivial_solution_rule(model):
        return sum(model.X[i, i] for i in model.I) <= len(model.I) - 1
    
    model.nontrivial_constraint = pyo.Constraint(rule=nontrivial_solution_rule)

    # Objective function using sparse term storage
    def objective_rule(model):
        linear_sum = sum(coeff * model.X[i,j] for i, j, coeff in linear_terms)
        quad_sum = sum(coeff * model.X[i,j] * model.X[m,n]
                    for (i,j,m,n), coeff in quad_dict.items())
        return linear_sum + quad_sum

    model.objective = pyo.Objective(rule=objective_rule, sense=pyo.maximize)

    return model, subset_S, subset_T

def solve_with_scip(model, time_limit=600):
    """Solve model with SCIP using optimized settings."""
    solver = SolverFactory('scip', solver_io='nl')

    # SCIP parameters for non-convex QAP
    options = {
        'limits/time': time_limit,
        'limits/gap': 0.00003
        ,  # 5% optimality gap
        'presolving/maxrestarts': 1,
        'separating/maxrounds': 0,
        'heuristics/emphasis': 'aggressive',
        'numerics/emphasis': 'fast',
        'constraints/quadratic/enable': True,
        'nonconvex': 2,  # Enable non-convex handling
        'display/verblevel': 4
    }

    results = solver.solve(model, options=options, tee=True)
    return results

def solve_subset_qap(male_graph, female_graph, current_mapping, subset_S, time_limit=600):
    """Solve QAP for a subset using SCIP with optimized settings."""
    if not subset_S:
        print("Error: Empty subset provided")
        return {}

    print(f"Solving QAP for subset of size {len(subset_S)}")

    try:
        # Create SCIP-optimized model
        model, subset_S, subset_T = create_scip_qap_model(
            male_graph, female_graph, current_mapping, subset_S
        )

        # Solve with SCIP
        results = solve_with_scip(model, time_limit)

        # Process solution
        if results.solver.status == pyo.SolverStatus.ok:
            new_mapping = {}
            for i in model.I:
                for j in model.J:
                    if pyo.value(model.X[i,j]) > 0.5:
                        new_mapping[subset_S[i]] = subset_T[j]
            return new_mapping
        else:
            print(f"Solver failed with status: {results.solver.status}")
            return {}

    except Exception as e:
        print(f"Error solving QAP: {str(e)}")
        return {}

def sample_numbers(n):
    # Define the range and count per distribution range
    ranges = [
        (0.0, 0.1, 0),
        (0.1, 0.2, 2),
        (0.2, 0.3, 1),
        (0.3, 0.4, 4),
        (0.4, 0.5, 3),
        (0.5, 0.6, 12),
        (0.6, 0.7, 13),
        (0.7, 0.8, 17),
        (0.8, 0.9, 45),
        (0.9, 1.0, 26),
    ]

    # Normalize counts to match the required n
    total_counts = sum(count for _, _, count in ranges)
    scale_factor = n / total_counts

    # Adjust counts based on n
    adjusted_counts = [max(1, round(count * scale_factor)) for _, _, count in ranges]

    selected_numbers = set()

    for (low, high, _), count in zip(ranges, adjusted_counts):
        low_idx = int(low * 18524) + 1
        high_idx = int(high * 18524)

        # Ensure unique selections
        selected_numbers.update(np.random.choice(range(low_idx, high_idx + 1), count, replace=False))

    return sorted(selected_numbers)


if __name__ == "__main__":
    # Load data with memoization
    male_path = '../gm.csv'
    female_path = '../gf.csv'
    # current_mapping_path = '../independent_hungarian/5853925-qap-hungarian.csv'
    current_mapping_path = 'improved_mapping_5853925.csv'
    subset_size = 150

    male_graph = parse_graph(male_path)
    female_graph = parse_graph(female_path)
    current_mapping = parse_mapping(current_mapping_path)

    print(sort_nodes_by_degree(male_graph)[:200])

    # Select subset with high-degree nodes for better initial progress
    # node_degrees = {n: len(data['outgoing']) for n, data in male_graph.items()}
    # subset_S = sorted(node_degrees, key=lambda x: -node_degrees[x])[:250]

    # subset_S = random.sample([n for n in current_mapping.keys()], 100)

    # subset_S = [2371,6995,7037,7263,7618,8356,9035,9404,9561,9883,10092,10141,10575,11003,11080,11086,11146,11522,11544,11677,11839,11863,11936,11974,12290,12352,12461,12613,12700,12824,12858,12914,13009,13117,13216,13446,13657,13683,13760,13761,13841,13863,13966,13973,14168,14260,14349,14354,14377,14412,14582,14769,14790,14848,14946,14990,14999,15016,15037,15062,15069,15073,15079,15133,15158,15218,15231,15263,15280,15324,15338,15363,15400,15557,15598,15674,15699,15717,15833,15837,15838,15860,15897,15926,15940,15961,15968,15971,15979,15997,16002,16021,16029,16039,16101,16126,16132,16138,16348,16433,16610,16683,16698,16770,16777,16785,16786,16802,16805,17164,17211,17431,17458,17475,17565,17668,18002,18157,18200,18276,18339,18428,18492,18499,18507,18510,18513,18520,]
    # subset_s = [2371, 15940, 6995, 9883, 7037, 15280, 7263, 7618, 7618, 7263, 8356, 11863, 9035, 11544, 9404, 15837, 9561, 11146, 9883, 6995, 10092, 12461, 10141, 12700, 10575, 15833, 11003, 17668, 11080, 13863, 11086, 13446, 11146, 9561, 11522, 1716411544, 903511677, 11936, 11839, 16805, 11863, 8356, 11936, 11677, 11974, 18507, 12290, 18002, 12352, 13760, 12461, 11839, 12613, 10575, 12700, 10141, 12824, 15400, 12858, 11974, 12914, 14790, 13009, 15158, 13117, 15979, 13216, 17475, 13446, 9404, 13657, 14377, 13683, 13966, 13760, 12352, 13761, 16777, 13841, 14168, 13863, 11080, 13966, 13683, 13973, 15069, 14168, 13841, 14260, 14354, 14349, 15717, 14354, 14260, 14377, 13657, 14412, 14582, 14582, 14412, 14769, 15016, 14790, 12914, 14848, 15079, 14946, 15037, 14990, 15961, 14999, 15073, 15016, 14769, 15037, 14946, 15062, 16802, 15069, 13973, 15073, 14999, 15079, 15324, 15133, 15231, 15158, 16002, 15218, 16785, 15231, 15133, 15263, 18510, 15280, 16101, 15324, 14848, 15338, 18276, 15363, 2371, 15400, 12824, 15557, 16029, 15598, 15860, 15674, 18428, 15699, 17565, 15717, 14349, 15833, 15363, 15837, 16126, 15838, 18339, 15860, 15598, 15897, 16021, 15926, 13117, 15940, 15968, 15961, 16039, 15968, 18520, 15971, 18157, 15979, 15926, 15997, 12858, 16002, 15997, 16021, 15897, 16029, 15557, 16039, 14990, 16101, 15062, 16126, 16698, 16132, 17431, 16138, 18200, 16348, 15971, 16433, 17211, 16610, 10092, 16683, 17458, 16698, 13761, 16770, 18492, 16777, 16786, 16785, 7037, 16786, 16610, 16802, 15263, 16805, 18513, 17164, 11522, 17211, 16433, 17431, 16132, 17458, 16348, 17475, 13216, 17565, 15699, 17668, 11003, 18002, 12290, 18157, 18499, 18200, 16138, 18276, 15338, 18339, 15838, 18428, 15674, 18492, 12613, 18499, 15218, 18507, 16770, 18510, 11086, 18513, 13009, 18520, 16683,]

    # subset_S = [593, 3605, 1342, 15062, 3451, 9237, 3605, 593, 4039, 18257, 4394, 6275, 5587, 9643, 6275, 4394, 6284, 16213, 6995, 9883, 7037, 14970, 7149, 7248, 7248, 7149, 7263, 7618, 7614, 7856, 7618, 7263, 7856, 7614, 8400, 10166, 9035, 11544, 9237, 3451, 9404, 15837, 9561, 11146, 9643, 5587, 9883, 6995, 9934, 10244, 10092, 15263, 10141, 12700, 10166, 8400, 10244, 9934, 10347, 12587, 10452, 11084, 10575, 18507, 10833, 13563, 11080, 13863, 11084, 10452, 11086, 15158, 11146, 9561, 11287, 16805, 11522, 17164, 11544, 9035, 11677, 11936, 11839, 18492, 11936, 11677, 11974, 15968, 12290, 18002, 12352, 13760, 12461, 16777, 12587, 10347, 12602, 12897, 12613, 15218, 12700, 10141, 12858, 11974, 12897, 12602, 12935, 15138, 13009, 11086, 13117, 11839, 13446, 9404, 13563, 10833, 13668, 13117, 13683, 13966, 13748, 15748, 13760, 12352, 13761, 16610, 13863, 11080, 13966, 13683, 13973, 15069, 14290, 14469, 14349, 15717, 14469, 15282, 14502, 14916, 14769, 15016, 14829, 15046, 14848, 15079, 14916, 14502, 14946, 15037, 14970, 15985, 15012, 15187, 15016, 14769, 15037, 14946, 15046, 14829, 15062, 16802, 15069, 13973, 15079, 15324, 15138, 15679, 15158, 16002, 15187, 15012, 15218, 15979, 15263, 18510, 15280, 13446, 15282, 14290, 15324, 14848, 15338, 18276, 15395, 15628, 15528, 15926, 15557, 16029, 15598, 15860, 15620, 15822, 15628, 15839, 15631, 15951, 15674, 18428, 15679, 15699, 15699, 15916, 15701, 16022, 15717, 14349, 15748, 13748, 15752, 16705, 15822, 15620, 15837, 16126, 15838, 18339, 15839, 15395, 15860, 15598, 15916, 16197, 15926, 15528, 15940, 16786, 15951, 15631, 15968, 18520, 15971, 11287, 15979, 7037, 15985, 18523, 15997, 12858, 16002, 15997, 16022, 18506, 16029, 15557, 16101, 1342, 16126, 16698, 16135, 18284, 16138, 12461, 16197, 13668, 16213, 6284, 16348, 15701, 16610, 10575, 16683, 17458, 16698, 13761, 16705, 15752, 16770, 18473, 16777, 10092, 16785, 13009, 16786, 16785, 16802, 18200, 16805, 15280, 17164, 11522, 17458, 16348, 18002, 12290, 18157, 15940, 18200, 16138, 18257, 4039, 18276, 15338, 18284, 16135, 18339, 15838, 18419, 12935, 18428, 15674, 18473, 18499, 18492, 18157, 18499, 15971, 18506, 16101, 18507, 16770, 18510, 12613, 18520, 16683, 18523, 18419, ]
    # subset_S = [593, 1342, 2371, 3451, 3605, 4039, 4394, 5587, 6275, 6284, 6995, 7037, 7149, 7248, 7263, 7614, 7618, 7856, 8400, 9035, 9237, 9404, 9561, 9643, 9883, 9934, 10092, 10141, 10166, 10244, 10347, 10452, 10575, 10833, 11080, 11084, 11086, 11146, 11287, 11522, 11544, 11677, 11839, 11936, 11974, 12290, 12352, 12461, 12587, 12602, 12613, 12700, 12858, 12897, 12935, 13009, 13117, 13446, 13563, 13668, 13683, 13748, 13760, 13761, 13863, 13966, 13973, 14290, 14349, 14469, 14502, 14769, 14829, 14848, 14916, 14946, 14970, 15012, 15016, 15037, 15046, 15062, 15069, 15079, 15138, 15158, 15187, 15218, 15263, 15280, 15282, 15324, 15338, 15395, 15528, 15557, 15598, 15620, 15628, 15631, 15674, 15679, 15699, 15701, 15717, 15748, 15752, 15822, 15837, 15838, 15839, 15860, 15916, 15926, 15940, 15951, 15968, 15971, 15979, 15985, 15997, 16002, 16022, 16029, 16101, 16126, 16135, 16138, 16197, 16213, 16348, 16610, 16683, 16698, 16705, 16770, 16777, 16785, 16786, 16802, 16805, 17164, 17458, 18002, 18157, 18200, 18257, 18276, 18284, 18339, 18419, 18428, 18473, 18492, 18499, 18506, 18507, 18510, 18520, 18523, ]

    while True:
        # subset_S = sample_numbers(subset_size)
        subset_S = [38, 32, 256, 86, 56, 126, 1680, 259, 65, 60, 400, 1085, 395, 289, 95, 267, 416, 157, 557, 6570, 152, 3361, 122, 59, 349, 321, 206, 90, 448, 23, 857, 814, 168, 372, 190, 825, 192, 198, 574, 2031, 465, 234, 344, 980, 158, 456, 888, 427, 730, 293, 12892, 12161, 457, 136, 284, 517, 226, 391, 68, 1038, 383, 69, 382, 407, 164, 544, 620, 402, 1061, 432, 129, 99, 269, 1592, 463, 520, 14911, 16252, 326, 177, 2334, 108, 7670, 1112, 1717, 1067, 196, 611, 116, 501, 115, 16244, 696, 788]
        # Solve with SCIP
        new_mapping = solve_subset_qap(
            male_graph=male_graph,
            female_graph=female_graph,
            current_mapping=current_mapping,
            subset_S=subset_S,
            time_limit=6500  # 100 minutes
        )


        # Update and save mapping
        if new_mapping:
            print({i: current_mapping[i] for i in new_mapping})
            print(new_mapping)

            current_mapping.update(new_mapping)
            print(f"Obtained {len(new_mapping)} new assignments")
            compare_mappings('improved_mapping.csv', current_mapping_path)
            # if compare_mappings('improved_mapping.csv', current_mapping_path):
            with open('improved_mapping_5853925.csv', 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['Male Node ID', 'Female Node ID'])
                for m, f in current_mapping.items():
                    writer.writerow([f"m{m}", f"f{f}"])

            break
        
        break

