import csv
from typing import List, Dict, Tuple, Set, Optional
import random
from collections import defaultdict
from z3 import *
import math
from dataclasses import dataclass
from itertools import combinations

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

@dataclass
class GraphMetrics:
    """Store preprocessed graph metrics for optimization."""
    node_degrees: Dict[int, int]
    node_strengths: Dict[int, int]  # Sum of edge weights
    clustering_coeffs: Dict[int, float]
    neighbor_sets: Dict[int, Set[int]]
    community_assignments: Dict[int, int]

def preprocess_graph(edges: Dict[Tuple[int, int], int], n_nodes: int) -> GraphMetrics:
    """Preprocess graph to compute useful metrics for matching."""
    # Calculate node degrees and strengths
    degrees = defaultdict(int)
    strengths = defaultdict(int)
    neighbors = defaultdict(set)
    
    for (src, dst), weight in edges.items():
        degrees[src] += 1
        degrees[dst] += 1
        strengths[src] += weight
        strengths[dst] += weight
        neighbors[src].add(dst)
        neighbors[dst].add(src)
    
    # Calculate clustering coefficients
    clustering = {}
    for node in range(n_nodes):
        if len(neighbors[node]) <= 1:
            clustering[node] = 0.0
            continue
            
        neighbor_list = list(neighbors[node])
        possible_triangles = len(neighbor_list) * (len(neighbor_list) - 1) / 2
        if possible_triangles == 0:
            clustering[node] = 0.0
            continue
            
        actual_triangles = 0
        for n1, n2 in combinations(neighbor_list, 2):
            if (n1, n2) in edges or (n2, n1) in edges:
                actual_triangles += 1
        
        clustering[node] = actual_triangles / possible_triangles
    
    # Detect communities using simple modularity optimization
    communities = detect_communities(edges, neighbors, n_nodes)
    
    return GraphMetrics(
        node_degrees=degrees,
        node_strengths=strengths,
        clustering_coeffs=clustering,
        neighbor_sets=neighbors,
        community_assignments=communities
    )

def detect_communities(edges: Dict[Tuple[int, int], int], 
                      neighbors: Dict[int, Set[int]], 
                      n_nodes: int, 
                      n_communities: int = 4) -> Dict[int, int]:
    """Simple community detection using node connectivity patterns."""
    # Initialize random communities
    communities = {node: random.randrange(n_communities) for node in range(n_nodes)}
    
    # Iteratively refine communities based on neighbor majority
    for _ in range(5):  # Limited iterations for speed
        for node in range(n_nodes):
            if not neighbors[node]:
                continue
                
            # Count neighbor communities
            comm_counts = defaultdict(int)
            for neighbor in neighbors[node]:
                comm_counts[communities[neighbor]] += 1
            
            # Assign to majority community
            if comm_counts:
                communities[node] = max(comm_counts.items(), key=lambda x: x[1])[0]
    
    return communities

def optimize_local_region(male_edges: Dict[Tuple[int, int], int],
                         female_edges: Dict[Tuple[int, int], int],
                         current_perm: List[int],
                         center_idx: int,
                         male_zero_degree: Set[int],
                         female_zero_degree: Set[int],
                         male_metrics: GraphMetrics,
                         female_metrics: GraphMetrics,
                         neighborhood_size: int = 5) -> List[int]:
    """Optimize a local region of the graph using Z3 with advanced heuristics."""
    if center_idx in male_zero_degree:
        return current_perm
    
    # Find connected neighborhood more intelligently
    neighborhood = {center_idx}
    edge_queue = [(src, dst) for (src, dst), _ in male_edges.items() 
                  if src == center_idx or dst == center_idx]
    
    # Prioritize nodes in same community and with similar properties
    while len(neighborhood) < neighborhood_size and edge_queue:
        candidates = []
        for src, dst in edge_queue:
            new_node = dst if src in neighborhood else src
            if new_node not in neighborhood and new_node not in male_zero_degree:
                # Calculate similarity score
                score = calculate_node_similarity(
                    new_node, center_idx,
                    male_metrics, male_edges
                )
                candidates.append((new_node, score))
        
        if not candidates:
            break
            
        # Add most similar node
        best_node = max(candidates, key=lambda x: x[1])[0]
        neighborhood.add(best_node)
        
        # Update edge queue
        edge_queue = [(s, d) for (s, d), _ in male_edges.items()
                     if (s == best_node or d == best_node) 
                     and s not in neighborhood and d not in neighborhood]
    
    neighborhood = list(neighborhood)[:neighborhood_size]
    
    # Find relevant female nodes more intelligently
    current_female_indices = set(current_perm[i] for i in neighborhood)
    candidates = set()
    
    # Add nodes with similar properties to current assignments
    for m_idx in neighborhood:
        similar_females = find_similar_nodes(
            m_idx, male_metrics,
            female_metrics, female_edges,
            exclude=female_zero_degree
        )
        candidates.update(similar_females)
    
    valid_female_indices = list(current_female_indices | candidates)
    
    if len(valid_female_indices) <= 1:
        return current_perm
    
    # Create Z3 solver with optimization
    s = Optimize()
    
    # Create variables
    perm = {(m, f): Bool(f'p_{m}_{f}') 
            for m in neighborhood 
            for f in valid_female_indices}
    
    # Basic matching constraints
    for m in neighborhood:
        s.add(Sum([If(perm[(m, f)], 1, 0) for f in valid_female_indices]) == 1)
    
    used_females = [Sum([If(perm[(m, f)], 1, 0) for m in neighborhood]) <= 1 
                   for f in valid_female_indices]
    s.add(used_females)
    
    # Add soft constraints based on node properties
    for m in neighborhood:
        for f in valid_female_indices:
            similarity_score = calculate_node_similarity_cross(
                m, f, male_metrics, female_metrics
            )
            if similarity_score > 0.7:  # High similarity threshold
                s.add_soft(perm[(m, f)], weight=int(similarity_score * 100))
    
    # Build objective function more efficiently
    alignment_score = optimize_alignment_score(
        male_edges, female_edges,
        neighborhood, valid_female_indices,
        perm, male_metrics, female_metrics
    )
    
    s.maximize(alignment_score)
    
    # Add timeout and parameters
    s.set("timeout", 10_000)
    s.set("priority", "pareto")  # Prefer balanced solutions
    
    if s.check() == sat:
        m = s.model()
        new_perm = current_perm.copy()
        for m_idx in neighborhood:
            for f_idx in valid_female_indices:
                if m.evaluate(perm[(m_idx, f_idx)]):
                    new_perm[m_idx] = f_idx
        return new_perm
    
    return current_perm

def calculate_node_similarity(node1: int, node2: int, 
                            metrics: GraphMetrics,
                            edges: Dict[Tuple[int, int], int]) -> float:
    """Calculate similarity between two nodes in the same graph."""
    # Weighted combination of multiple similarity measures
    degree_sim = 1.0 - abs(metrics.node_degrees[node1] - metrics.node_degrees[node2]) / \
                 max(metrics.node_degrees[node1], metrics.node_degrees[node2], 1)
    
    strength_sim = 1.0 - abs(metrics.node_strengths[node1] - metrics.node_strengths[node2]) / \
                  max(metrics.node_strengths[node1], metrics.node_strengths[node2], 1)
    
    clustering_sim = 1.0 - abs(metrics.clustering_coeffs[node1] - metrics.clustering_coeffs[node2])
    
    community_sim = float(metrics.community_assignments[node1] == 
                        metrics.community_assignments[node2])
    
    # Weight the different components
    return (0.3 * degree_sim + 0.3 * strength_sim + 
            0.2 * clustering_sim + 0.2 * community_sim)

def calculate_node_similarity_cross(node1: int, node2: int,
                                  metrics1: GraphMetrics,
                                  metrics2: GraphMetrics) -> float:
    """Calculate similarity between nodes across different graphs."""
    degree_sim = 1.0 - abs(metrics1.node_degrees[node1] - metrics2.node_degrees[node2]) / \
                 max(metrics1.node_degrees[node1], metrics2.node_degrees[node2], 1)
    
    strength_sim = 1.0 - abs(metrics1.node_strengths[node1] - metrics2.node_strengths[node2]) / \
                  max(metrics1.node_strengths[node1], metrics2.node_strengths[node2], 1)
    
    clustering_sim = 1.0 - abs(metrics1.clustering_coeffs[node1] - metrics2.clustering_coeffs[node2])
    
    return (0.4 * degree_sim + 0.4 * strength_sim + 0.2 * clustering_sim)

def find_similar_nodes(node: int, 
                      source_metrics: GraphMetrics,
                      target_metrics: GraphMetrics,
                      target_edges: Dict[Tuple[int, int], int],
                      exclude: Set[int],
                      n_similar: int = 5) -> Set[int]:
    """Find nodes in target graph similar to given node in source graph."""
    similarities = []
    for target_node in range(max(target_metrics.node_degrees.keys()) + 1):
        if target_node in exclude:
            continue
        
        sim = calculate_node_similarity_cross(
            node, target_node,
            source_metrics, target_metrics
        )
        similarities.append((target_node, sim))
    
    return {node for node, sim in sorted(similarities, key=lambda x: x[1], reverse=True)[:n_similar]}

def optimize_alignment_score(male_edges: Dict[Tuple[int, int], int],
                           female_edges: Dict[Tuple[int, int], int],
                           neighborhood: List[int],
                           valid_females: List[int],
                           perm: Dict[Tuple[int, int], Bool],
                           male_metrics: GraphMetrics,
                           female_metrics: GraphMetrics) -> ArithRef:
    """Build optimized alignment score expression."""
    score = IntVal(0)
    
    # Precompute edge weights
    male_weights = {(src, dst): weight 
                   for (src, dst), weight in male_edges.items()
                   if src in neighborhood and dst in neighborhood}
    female_weights = {(src, dst): weight 
                     for (src, dst), weight in female_edges.items()
                     if src in valid_females and dst in valid_females}
    
    # Build score expression with additional rewards
    for (m_src, m_dst), m_weight in male_weights.items():
        for f_src in valid_females:
            for f_dst in valid_females:
                if (f_src, f_dst) in female_weights:
                    f_weight = female_weights[(f_src, f_dst)]
                    base_weight = If(m_weight <= f_weight,
                                   IntVal(m_weight),
                                   IntVal(f_weight))
                    
                    # Add bonus for matching similar nodes
                    similarity_bonus = If(And(
                        calculate_node_similarity_cross(
                            m_src, f_src, male_metrics, female_metrics) > 0.7,
                        calculate_node_similarity_cross(
                            m_dst, f_dst, male_metrics, female_metrics) > 0.7
                    ), IntVal(5), IntVal(0))
                    
                    contribution = If(
                        And(perm[(m_src, f_src)], perm[(m_dst, f_dst)]),
                        base_weight + similarity_bonus,
                        IntVal(0)
                    )
                    score = score + contribution
    
    return score

def optimize_matching(male_edges: Dict[Tuple[int, int], int],
                     female_edges: Dict[Tuple[int, int], int],
                     male_zero_degree: Set[int],
                     female_zero_degree: Set[int],
                     initial_perm: Optional[List[int]] = None,
                     target_score: int = 4800,
                     max_iterations: int = 200,
                     patience: int = 50) -> List[int]:
    """Optimize the matching using iterative local improvement with advanced heuristics."""
    n = max(max(src, dst) for (src, dst) in male_edges.keys()) + 1
    
    # Preprocess graphs
    print("Preprocessing graphs...")
    male_metrics = preprocess_graph(male_edges, n)
    female_metrics = preprocess_graph(female_edges, n)
    
    # Initialize permutation intelligently
    if initial_perm is None:
        print("Generating initial matching...")
        current_perm = initialize_matching(
            n, male_edges, female_edges,
            male_metrics, female_metrics,
            male_zero_degree, female_zero_degree
        )
    else:
        current_perm = initial_perm
    
    current_score = calculate_score(male_edges, female_edges, current_perm)
    best_score = current_score
    best_perm = current_perm.copy()
    iterations_without_improvement = 0
    
    print(f"Initial score: {current_score}")

    # return current_perm

    # save_permutation(current_perm, 'initial_perm.csv', male_metrics.node_idx_to_node, female_metrics.node_idx_to_node)
    
    # Prioritize nodes for optimization
    priority_nodes = prioritize_nodes(
        male_edges, male_metrics,
        male_zero_degree, n
    )
    
    # Dynamic neighborhood size based on improvement rate
    base_neighborhood_size = 5
    neighborhood_size = base_neighborhood_size
    
    iterations = 0
    while (current_score < target_score and 
           iterations < max_iterations and 
           iterations_without_improvement < patience):
        
        # Adjust neighborhood size based on progress
        if iterations_without_improvement > patience // 2:
            neighborhood_size = min(10, neighborhood_size + 1)
        else:
            neighborhood_size = base_neighborhood_size
        
        # Select center node based on priority and iteration
        center_idx = priority_nodes[iterations % len(priority_nodes)]
        
        # Optimize local region
        new_perm = optimize_local_region(
            male_edges, female_edges, 
            current_perm, center_idx,
            male_zero_degree, female_zero_degree,
            male_metrics, female_metrics,
            neighborhood_size
        )
        
        # Calculate the new score
        new_score = calculate_score(male_edges, female_edges, new_perm)
        
        # Update if improvement
        if new_score > current_score:
            print(f"Iteration {iterations}: Improved score from {current_score} to {new_score}")
            current_score = new_score
            current_perm = new_perm
            iterations_without_improvement = 0
            
            # Update best score if applicable
            if new_score > best_score:
                best_score = new_score
                best_perm = new_perm.copy()
        else:
            iterations_without_improvement += 1
            print(f"Iteration {iterations}: No improvement. Current best score: {best_score}")
        
        iterations += 1

    print(f"Optimization complete. Best score: {best_score} after {iterations} iterations.")
    return best_perm

def calculate_score(male_edges: Dict[Tuple[int, int], int],
                    female_edges: Dict[Tuple[int, int], int],
                    perm: List[int]) -> int:
    """Calculate the alignment score for the given permutation."""
    score = 0
    
    # Accumulate scores based on edge matches
    for (m_src, m_dst), m_weight in male_edges.items():
        f_src, f_dst = perm[m_src], perm[m_dst]
        if (f_src, f_dst) in female_edges:
            f_weight = female_edges[(f_src, f_dst)]
            score += min(m_weight, f_weight)
    
    return score

def initialize_matching(n: int, 
                       male_edges: Dict[Tuple[int, int], int], 
                       female_edges: Dict[Tuple[int, int], int], 
                       male_metrics: GraphMetrics, 
                       female_metrics: GraphMetrics, 
                       male_zero_degree: Set[int], 
                       female_zero_degree: Set[int]) -> List[int]:
    """Generate an initial matching between nodes based on heuristic similarity."""
    perm = [-1] * n
    used_females = set()
    
    for m in range(n):
        if m in male_zero_degree:
            continue
        
        # Find similar female nodes not yet matched
        similar_females = find_similar_nodes(
            m, male_metrics, female_metrics, 
            female_edges, female_zero_degree - used_females
        )
        
        # Assign the best available match
        for f in similar_females:
            if f not in used_females:
                perm[m] = f
                used_females.add(f)
                break
    
    # Fill remaining unmatched nodes with unused indices
    unmatched_females = iter(f for f in range(n) if f not in used_females and f not in female_zero_degree)
    for m in range(n):
        if perm[m] == -1:
            perm[m] = next(unmatched_females, -1)
    
    return perm

def prioritize_nodes(male_edges: Dict[Tuple[int, int], int],
                     male_metrics: GraphMetrics,
                     male_zero_degree: Set[int],
                     n_nodes: int) -> List[int]:
    """Prioritize nodes for optimization based on their degree and connectivity."""
    priority = [
        (node, male_metrics.node_degrees[node])
        for node in range(n_nodes) if node not in male_zero_degree
    ]
    # Sort by degree in descending order, as high-degree nodes are more influential
    priority.sort(key=lambda x: x[1], reverse=True)
    
    # Return only node indices
    return [node for node, _ in priority]

def save_permutation(perm: List[int], filename: str, male_idx_to_node: Dict[int, str], female_idx_to_node: Dict[int, str]):
    """Save the given permutation to a file."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Male Node ID', 'Female Node ID'])
        for male_idx, female_idx in enumerate(perm):
            if male_idx in male_idx_to_node and female_idx in female_idx_to_node:
                writer.writerow([male_idx_to_node[male_idx], female_idx_to_node[female_idx]])
            else:
                print(f"Warning: Missing mapping for male_idx={male_idx} or female_idx={female_idx}")

def main():
    # Load edge data for both male and female connectomes
    male_edges, male_node_to_idx, n_male, male_zero_degree = read_edges("test_male_connectome_graph.csv")
    female_edges, female_node_to_idx, n_female, female_zero_degree = read_edges("test_female_connectome_graph.csv")
    
    # Ensure the graphs are compatible in size
    assert n_male == n_female, "Graphs must have the same number of nodes"
    
    # Mapping indices back to node labels for final output
    male_idx_to_node = {idx: node for node, idx in male_node_to_idx.items()}
    female_idx_to_node = {idx: node for node, idx in female_node_to_idx.items()}
    
    # Attempt to load a warm start permutation if available
    initial_perm = None
    try:
        # initial_perm = read_warm_start("test_warm_start.csv", male_node_to_idx, female_node_to_idx)
        initial_perm = read_warm_start("error.csv", male_node_to_idx, female_node_to_idx)
        print("Using warm start solution")
    except FileNotFoundError:
        print("No warm start file found; using default initialization")

    # Run the optimization to find the best permutation
    perm = optimize_matching(male_edges, female_edges, 
                             male_zero_degree, female_zero_degree,
                             initial_perm)
    
    # Output the result to a CSV file
    with open("vnc_matching_submission.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Male Node ID', 'Female Node ID'])
        for male_idx, female_idx in enumerate(perm):
            if male_idx in male_idx_to_node and female_idx in female_idx_to_node:
                writer.writerow([male_idx_to_node[male_idx], female_idx_to_node[female_idx]])
            else:
                print(f"Warning: Missing mapping for male_idx={male_idx} or female_idx={female_idx}")

if __name__ == "__main__":
    main()
