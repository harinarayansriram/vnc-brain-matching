import csv
from typing import List, Dict, Tuple, Set
import random
from collections import defaultdict
from z3 import *

def read_edges(filename: str) -> Tuple[Dict[Tuple[int, int], int], Dict[str, int], int, Set[int]]:
    """
    Read edge data from CSV file and convert to indexed representation.
    Returns:
    - edges: dictionary mapping (src_idx, dst_idx) to weight
    - node_to_idx: mapping from node ID to index
    - next_idx: number of nodes
    - zero_degree_nodes: set of indices of nodes with no edges
    """
    edges = {}
    node_to_idx = {}  # Map from node ID to index
    next_idx = 0
    degree = defaultdict(int)  # Track node degrees
    
    # First pass: collect all nodes and count degrees
    with open(filename, encoding='utf-8') as f:
        reader = csv.reader(f)
        assert next(reader) == ['From Node ID', 'To Node Id', 'Weight']  # Verify header
        for row in csv.reader(f):
            # Add 'm' or 'f' prefix based on filename
            # prefix = 'm' if 'male' in filename or 'gm' in filename else 'f'
            prefix = 'f' if 'female' in filename or 'gf' in filename else 'm'

            src, dst = f"{prefix}{row[0]}", f"{prefix}{row[1]}"
            weight = int(row[2])
            
            # Record degrees
            degree[src] += weight
            degree[dst] += weight
            
            # Assign indices
            for node in (src, dst):
                if node not in node_to_idx:
                    node_to_idx[node] = next_idx
                    next_idx += 1
    
    # Second pass: create edge dictionary with indices
    with open(filename, encoding='utf-8') as f:
        next(csv.reader(f))  # Skip header
        for row in csv.reader(f):
            # prefix = 'm' if 'male' in filename or 'gm' in filename else 'f'
            prefix = 'f' if 'female' in filename or 'gf' in filename else 'm'
            src = f"{prefix}{row[0]}"
            dst = f"{prefix}{row[1]}"
            src_idx = node_to_idx[src]
            dst_idx = node_to_idx[dst]
            edges[(src_idx, dst_idx)] = int(row[2])
    
    # Identify zero-degree nodes
    zero_degree_nodes = {node_to_idx[node] for node, deg in degree.items() if deg == 0}
    
    return edges, node_to_idx, next_idx, zero_degree_nodes

def read_warm_start(filename: str, male_node_to_idx: Dict[str, int], 
                   female_node_to_idx: Dict[str, int]) -> List[int]:
    """Read existing matching from CSV file and convert to permutation."""
    n = len(male_node_to_idx)
    perm = list(range(n))  # Default to identity permutation
    
    with open(filename, encoding='utf-8') as f:
        reader = csv.reader(f)
        assert next(reader) == ['Male Node ID', 'Female Node ID']  # Verify header
        print(male_node_to_idx)
        print(female_node_to_idx)
        for row in reader:
            male_node, female_node = row
            # Convert to indices
            male_idx = male_node_to_idx[male_node]
            female_idx = female_node_to_idx[female_node]
            perm[male_idx] = female_idx
    
    return perm
def optimize_local_region(male_edges: Dict[Tuple[int, int], int],
                         female_edges: Dict[Tuple[int, int], int],
                         current_perm: List[int],
                         center_idx: int,
                         male_zero_degree: Set[int],
                         female_zero_degree: Set[int],
                         neighborhood_size: int = 5) -> List[int]:
    """Optimize a local region of the graph using Z3."""
    if center_idx in male_zero_degree:
        return current_perm
    
    # Find connected neighborhood more efficiently
    neighborhood = {center_idx}
    edge_queue = [(src, dst) for (src, dst), _ in male_edges.items() 
                  if src == center_idx or dst == center_idx]
    while len(neighborhood) < neighborhood_size and edge_queue:
        src, dst = edge_queue.pop(0)
        new_node = dst if src in neighborhood else src
        if new_node not in neighborhood and new_node not in male_zero_degree:
            neighborhood.add(new_node)
            # Add new edges connected to this node
            edge_queue.extend([(s, d) for (s, d), _ in male_edges.items()
                             if (s == new_node or d == new_node) 
                             and s not in neighborhood and d not in neighborhood])
    
    neighborhood = list(neighborhood)[:neighborhood_size]
    
    # Find relevant female nodes (current assignments plus their neighbors)
    current_female_indices = set(current_perm[i] for i in neighborhood)
    female_neighbors = set()
    for f_idx in current_female_indices:
        if f_idx not in female_zero_degree:
            female_neighbors.update(dst for (src, dst), _ in female_edges.items() 
                                  if src == f_idx and dst not in female_zero_degree)
            female_neighbors.update(src for (src, dst), _ in female_edges.items() 
                                  if dst == f_idx and src not in female_zero_degree)
    
    valid_female_indices = list(current_female_indices | female_neighbors)
    
    if len(valid_female_indices) <= 1:
        return current_perm
    
    # Create Z3 solver with optimization
    s = Optimize()
    
    # Create variables more efficiently
    perm = {(m, f): Bool(f'p_{m}_{f}') 
            for m in neighborhood 
            for f in valid_female_indices}
    
    # Simplified constraints
    for m in neighborhood:
        s.add(Sum([If(perm[(m, f)], 1, 0) for f in valid_female_indices]) == 1)
    
    used_females = [Sum([If(perm[(m, f)], 1, 0) for m in neighborhood]) <= 1 
                   for f in valid_female_indices]
    s.add(used_females)
    
    # Precompute edge weights for faster lookup
    male_weights = {(src, dst): weight 
                   for (src, dst), weight in male_edges.items()
                   if src in neighborhood and dst in neighborhood}
    female_weights = {(src, dst): weight 
                     for (src, dst), weight in female_edges.items()
                     if src in valid_female_indices and dst in valid_female_indices}
    
    # Build objective function more efficiently
    alignment_score = IntVal(0)
    for (m_src, m_dst), m_weight in male_weights.items():
        for f_src in valid_female_indices:
            for f_dst in valid_female_indices:
                if (f_src, f_dst) in female_weights:
                    f_weight = female_weights[(f_src, f_dst)]
                    weight_expr = If(m_weight <= f_weight,
                                   IntVal(m_weight),
                                   IntVal(f_weight))
                    contribution = If(And(perm[(m_src, f_src)],
                                       perm[(m_dst, f_dst)]),
                                   weight_expr,
                                   IntVal(0))
                    alignment_score = alignment_score + contribution

    s.maximize(alignment_score)
    
    # Add timeout for Z3 solver
    s.set("timeout", 5000)  # 1 second timeout
    
    if s.check() == sat:
        m = s.model()
        new_perm = current_perm.copy()
        for m_idx in neighborhood:
            for f_idx in valid_female_indices:
                if m.evaluate(perm[(m_idx, f_idx)]):
                    new_perm[m_idx] = f_idx
        return new_perm
    
    return current_perm

def optimize_matching(male_edges: Dict[Tuple[int, int], int],
                     female_edges: Dict[Tuple[int, int], int],
                     male_zero_degree: Set[int],
                     female_zero_degree: Set[int],
                     initial_perm: List[int] = None,
                     target_score: int = 4500,
                     max_iterations: int = 100,
                     patience: int = 50) -> List[int]:
    """Optimize the matching using iterative local improvement with early stopping."""
    n = max(max(src, dst) for (src, dst) in male_edges.keys()) + 1
    
    # Initialize permutation more intelligently
    if initial_perm is None:
        current_perm = list(range(n))
        
        # Match zero-degree nodes to zero-degree nodes
        zero_degree_perm = list(female_zero_degree)
        random.shuffle(zero_degree_perm)
        for i, male_idx in enumerate(male_zero_degree):
            current_perm[male_idx] = zero_degree_perm[i % len(zero_degree_perm)]
        
        # For nodes with edges, try to match based on degree similarity
        male_degrees = defaultdict(int)
        female_degrees = defaultdict(int)
        for (src, dst), weight in male_edges.items():
            male_degrees[src] += weight
            male_degrees[dst] += weight
        for (src, dst), weight in female_edges.items():
            female_degrees[src] += weight
            female_degrees[dst] += weight
        
        non_zero_male = list(set(range(n)) - male_zero_degree)
        non_zero_female = list(set(range(n)) - female_zero_degree)
        
        # Sort by degree
        non_zero_male.sort(key=lambda x: male_degrees[x])
        non_zero_female.sort(key=lambda x: female_degrees[x])
        
        for i, male_idx in enumerate(non_zero_male):
            current_perm[male_idx] = non_zero_female[i % len(non_zero_female)]
    else:
        current_perm = initial_perm
    
    # Calculate initial score
    current_score = calculate_score(male_edges, female_edges, current_perm)
    best_score = current_score
    best_perm = current_perm.copy()
    iterations_without_improvement = 0
    
    print(f"Initial score: {current_score}")
    
    # Precompute node priorities based on edge weights
    node_importance = defaultdict(int)
    for (src, dst), weight in male_edges.items():
        node_importance[src] += weight
        node_importance[dst] += weight
    
    # Sort nodes by importance for prioritized optimization
    priority_nodes = sorted(
        [i for i in range(n) if i not in male_zero_degree],
        key=lambda x: node_importance[x],
        reverse=True
    )
    
    iterations = 0
    while (current_score < target_score and 
           iterations < max_iterations and 
           iterations_without_improvement < patience):
        
        # Select center node based on priority and iteration
        center_idx = priority_nodes[iterations % len(priority_nodes)]
        
        # Optimize local region
        new_perm = optimize_local_region(
            male_edges, female_edges, 
            current_perm, center_idx,
            male_zero_degree, female_zero_degree
        )
        
        # Calculate new score
        new_score = calculate_score(male_edges, female_edges, new_perm)
        
        # Update if improved
        if new_score > current_score:
            current_perm = new_perm
            current_score = new_score
            iterations_without_improvement = 0
            
            # Update best solution
            if current_score > best_score:
                best_score = current_score
                best_perm = current_perm.copy()
                print(f"Iteration {iterations}: Score improved to {current_score}")
        else:
            iterations_without_improvement += 1
        
        iterations += 1
    
    print(f"Final score: {best_score} after {iterations} iterations")
    return best_perm

def calculate_score(male_edges: Dict[Tuple[int, int], int],
                   female_edges: Dict[Tuple[int, int], int],
                   perm: List[int]) -> int:
    """Calculate alignment score for a given permutation."""
    score = 0
    for (src, dst), weight in male_edges.items():
        fsrc, fdst = perm[src], perm[dst]
        if (fsrc, fdst) in female_edges:
            score += min(weight, female_edges[(fsrc, fdst)])
    return score

def main():
    # Read input data
    male_edges, male_node_to_idx, n_male, male_zero_degree = read_edges("test_male_connectome_graph.csv")
    female_edges, female_node_to_idx, n_female, female_zero_degree = read_edges("test_female_connectome_graph.csv")
    
    assert n_male == n_female, "Graphs must have same number of nodes"
    
    # Create reverse mapping for output
    male_idx_to_node = {idx: node for node, idx in male_node_to_idx.items()}
    female_idx_to_node = {idx: node for node, idx in female_node_to_idx.items()}
    
    print(f"Number of nodes: {n_male}")
    print(f"Zero-degree male nodes: {male_zero_degree}")
    print(f"Zero-degree female nodes: {female_zero_degree}")
    
    # Try to read warm start if available
    initial_perm = None
    try:
        # initial_perm = read_warm_start("test_warm_start.csv", male_node_to_idx, female_node_to_idx)
        initial_perm = read_warm_start("error.csv", male_node_to_idx, female_node_to_idx)

        print("Using warm start solution")
        print(f"Initial permutation length: {len(initial_perm)}")
    except FileNotFoundError:
        print("No warm start file found, starting from random permutation")
    
    # Optimize matching
    perm = optimize_matching(male_edges, female_edges, 
                           male_zero_degree, female_zero_degree,
                           initial_perm)
    
    print(f"Final permutation length: {len(perm)}")
    
    # Verify all indices are present in mappings
    missing_male = set(range(n_male)) - set(male_idx_to_node.keys())
    missing_female = set(range(n_female)) - set(female_idx_to_node.keys())
    if missing_male or missing_female:
        print("Warning: Missing indices in mappings:")
        print(f"Male: {missing_male}")
        print(f"Female: {missing_female}")
    
    # Save result
    with open("vnc_matching_submission.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Male Node ID', 'Female Node ID'])
        for male_idx, female_idx in enumerate(perm):
            if male_idx in male_idx_to_node and female_idx in female_idx_to_node:
                writer.writerow([male_idx_to_node[male_idx], 
                               female_idx_to_node[female_idx]])
            else:
                print(f"Warning: Missing mapping for male_idx={male_idx} or female_idx={female_idx}")

if __name__ == "__main__":
    main()