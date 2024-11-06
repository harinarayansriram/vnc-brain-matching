import random
import csv
from typing import List, Tuple

def generate_test_data(n_nodes: int = 50, edge_density: float = 0.1, 
                      zero_degree_fraction: float = 0.02) -> None:
    """
    Generate test connectome data with known optimal matching.
    
    Args:
        n_nodes: Number of nodes in each graph
        edge_density: Fraction of possible edges that exist
        zero_degree_fraction: Fraction of nodes that should have no edges
    """
    # Create true matching (identity permutation for simplicity)
    true_matching = list(range(n_nodes))
    
    # Decide which nodes will have zero degree
    n_zero_degree = int(n_nodes * zero_degree_fraction)
    zero_degree_nodes = set(random.sample(range(n_nodes), n_zero_degree))
    
    # Generate edges for both graphs using same pattern (for known optimal solution)
    edges: List[Tuple[int, int, int]] = []
    possible_edges = [(i, j) for i in range(n_nodes) for j in range(n_nodes)
                     if i != j and i not in zero_degree_nodes and j not in zero_degree_nodes]
    n_edges = int(len(possible_edges) * edge_density)
    
    for src, dst in random.sample(possible_edges, n_edges):
        weight = random.randint(1, 10)
        edges.append((src, dst, weight))
    
    # Write male connectome
    with open('test_male_connectome_graph.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['From Node ID', 'To Node Id', 'Weight'])
        for src, dst, weight in edges:
            writer.writerow([str(src), str(dst), str(weight)])
        # Add zero-degree nodes with self-loops of weight 0 to ensure they appear in the file
        for node in zero_degree_nodes:
            writer.writerow([str(node), str(node), '0'])
    
    # Write female connectome (using same pattern)
    with open('test_female_connectome_graph.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['From Node ID', 'To Node Id', 'Weight'])
        for src, dst, weight in edges:
            writer.writerow([str(src), str(dst), str(weight)])
        # Add zero-degree nodes with self-loops of weight 0 to ensure they appear in the file
        for node in zero_degree_nodes:
            writer.writerow([str(node), str(node), '0'])
    
    # Write known optimal matching
    with open('test_warm_start.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Male Node ID', 'Female Node ID'])
        for male_idx in range(n_nodes):  # Start from 0 to include all nodes
            writer.writerow([f'm{male_idx}', f'f{male_idx}'])
    
    # Calculate and return optimal score
    optimal_score = sum(weight for _, _, weight in edges)
    return optimal_score

def test_matching_solver():
    """Test the matching solver with small synthetic data."""
    # Generate test data
    n_nodes = 50
    optimal_score = generate_test_data(n_nodes=n_nodes)
    print(f"Generated test data with {n_nodes} nodes")
    print(f"Optimal score: {optimal_score}")
    
    # Run the matching solver
    import z3_test  # Import your solver module
    z3_test.main()  # It should read test_*_connectome_graph.csv files
    
    # Verify the result
    result_matching = {}
    with open('vnc_matching_submission.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            male_node = row['Male Node ID'].strip('m')  # Remove 'm' prefix
            female_node = row['Female Node ID'].strip('f')  # Remove 'f' prefix
            result_matching[int(male_node)] = int(female_node)
    
    # Check properties and print diagnostic information
    print(f"\nMatching size: {len(result_matching)}")
    print(f"Expected size: {n_nodes}")
    print("\nNodes missing from matching:", set(range(n_nodes)) - set(result_matching.keys()))
    print("Duplicate assignments:", set(val for val in result_matching.values() if list(result_matching.values()).count(val) > 1))
    
    assert len(result_matching) == n_nodes, "Matching should contain all nodes"
    female_nodes = set(result_matching.values())
    assert len(female_nodes) == n_nodes, "Matching should be one-to-one"
    
    print("Basic matching properties verified!")
    print("Result matching:", result_matching)


if __name__ == '__main__':
    test_matching_solver()