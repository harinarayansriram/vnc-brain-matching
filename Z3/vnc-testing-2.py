import random
import csv
import numpy as np
from typing import List, Tuple, Set, Dict
from collections import defaultdict

class ConnectomeGraphGenerator:
    def __init__(self, 
                 n_nodes: int = 50,
                 edge_density: float = 0.15,
                 zero_degree_fraction: float = 0.02,
                 community_count: int = 3,
                 weight_range: Tuple[int, int] = (1, 20),
                 noise_level: float = 0.2,
                 hub_fraction: float = 0.1):
        """
        Initialize the graph generator with specified parameters.
        
        Args:
            n_nodes: Number of nodes in each graph
            edge_density: Base fraction of possible edges that exist
            zero_degree_fraction: Fraction of nodes that should have no edges
            community_count: Number of neural communities/clusters
            weight_range: Range for edge weights (min, max)
            noise_level: Amount of random variation between male and female graphs
            hub_fraction: Fraction of nodes that are hubs (highly connected)
        """
        self.n_nodes = n_nodes
        self.edge_density = edge_density
        self.zero_degree_nodes = set(random.sample(range(n_nodes), 
                                   int(n_nodes * zero_degree_fraction)))
        self.communities = self._assign_communities(community_count)
        self.weight_range = weight_range
        self.noise_level = noise_level
        self.hub_nodes = set(random.sample([n for n in range(n_nodes) 
                                          if n not in self.zero_degree_nodes],
                                         int(n_nodes * hub_fraction)))
    
    def _assign_communities(self, community_count: int) -> Dict[int, int]:
        """Assign nodes to communities, excluding zero-degree nodes."""
        active_nodes = [n for n in range(self.n_nodes) 
                       if n not in self.zero_degree_nodes]
        communities = {}
        
        # Ensure at least one node per community
        for comm in range(community_count):
            if active_nodes:
                node = random.choice(active_nodes)
                communities[node] = comm
                active_nodes.remove(node)
        
        # Randomly assign remaining nodes
        for node in active_nodes:
            communities[node] = random.randrange(community_count)
            
        return communities
    
    def _generate_base_edges(self) -> List[Tuple[int, int, int]]:
        """Generate base edge pattern with community structure and hubs."""
        edges = []
        nodes = [n for n in range(self.n_nodes) 
                if n not in self.zero_degree_nodes]
        
        # Calculate different edge probabilities
        base_prob = self.edge_density
        same_community_prob = base_prob * 2
        hub_prob = base_prob * 3
        
        for src in nodes:
            for dst in nodes:
                if src != dst:
                    # Calculate edge probability based on node properties
                    if src in self.hub_nodes or dst in self.hub_nodes:
                        prob = hub_prob
                    elif (src in self.communities and dst in self.communities and 
                          self.communities[src] == self.communities[dst]):
                        prob = same_community_prob
                    else:
                        prob = base_prob
                    
                    # Add edge with calculated probability
                    if random.random() < prob:
                        # Weight distribution depends on node types
                        if src in self.hub_nodes or dst in self.hub_nodes:
                            weight = random.randint(
                                self.weight_range[0],
                                int(self.weight_range[1] * 1.5)
                            )
                        else:
                            weight = random.randint(*self.weight_range)
                        edges.append((src, dst, weight))
        
        return edges
    
    def _add_noise(self, edges: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
        """Add noise to edge weights and potentially add/remove edges."""
        noisy_edges = []
        existing_edges = {(src, dst) for src, dst, _ in edges}
        
        # Modify existing edges
        for src, dst, weight in edges:
            if random.random() > self.noise_level:  # Keep edge with original weight
                noisy_edges.append((src, dst, weight))
            else:  # Modify weight or potentially remove edge
                if random.random() < 0.8:  # Modify weight
                    noise = int(weight * random.uniform(-0.3, 0.3))
                    new_weight = max(self.weight_range[0], 
                                   min(self.weight_range[1], weight + noise))
                    noisy_edges.append((src, dst, new_weight))
                # Otherwise, edge is removed
        
        # Add some new random edges
        nodes = [n for n in range(self.n_nodes) 
                if n not in self.zero_degree_nodes]
        n_new_edges = int(len(edges) * self.noise_level * 0.3)
        
        for _ in range(n_new_edges):
            src = random.choice(nodes)
            dst = random.choice(nodes)
            if src != dst and (src, dst) not in existing_edges:
                weight = random.randint(*self.weight_range)
                noisy_edges.append((src, dst, weight))
        
        return noisy_edges
    
    def generate_test_data(self) -> int:
        """Generate test connectome data with known optimal matching."""
        # Generate base edge pattern
        base_edges = self._generate_base_edges()
        
        # Create male and female edges with controlled differences
        male_edges = self._add_noise(base_edges)
        female_edges = self._add_noise(base_edges)
        
        # Write male connectome
        self._write_graph('../test_male_connectome_graph.csv', male_edges)
        
        # Write female connectome
        self._write_graph('../test_female_connectome_graph.csv', female_edges)
        
        # Write identity matching as warm start
        self._write_matching('../test_warm_start.csv')
        
        # Calculate and return optimal score estimate
        return self._estimate_optimal_score(male_edges, female_edges)
    
    def _write_graph(self, filename: str, edges: List[Tuple[int, int, int]]) -> None:
        """Write graph edges to CSV file."""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['From Node ID', 'To Node Id', 'Weight'])
            # Write edges
            for src, dst, weight in edges:
                writer.writerow([str(src), str(dst), str(weight)])
            # Add zero-degree nodes
            for node in self.zero_degree_nodes:
                writer.writerow([str(node), str(node), '0'])
    
    def _write_matching(self, filename: str) -> None:
        """Write identity matching to CSV file."""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Male Node ID', 'Female Node ID'])
            for idx in range(self.n_nodes):
                writer.writerow([f'm{idx}', f'f{idx}'])
    
    def _estimate_optimal_score(self, male_edges: List[Tuple[int, int, int]], 
                              female_edges: List[Tuple[int, int, int]]) -> int:
        """Estimate optimal score based on edge distributions."""
        # Convert to dictionaries for easier lookup
        m_edges = {(src, dst): weight for src, dst, weight in male_edges}
        f_edges = {(src, dst): weight for src, dst, weight in female_edges}
        
        score = 0
        for (m_src, m_dst), m_weight in m_edges.items():
            if (m_src, m_dst) in f_edges:
                score += min(m_weight, f_edges[(m_src, m_dst)])
        
        # Account for noise and structural differences
        return int(score * (1 - self.noise_level))

def test_matching_solver():
    """Test the matching solver with complex synthetic data."""
    # Generate test data with more realistic properties
    generator = ConnectomeGraphGenerator(
        n_nodes=50,
        edge_density=0.15,
        zero_degree_fraction=0.02,
        community_count=4,
        weight_range=(1, 20),
        noise_level=0.2,
        hub_fraction=0.1
    )
    
    optimal_score = generator.generate_test_data()
    print("Generated test data with the following properties:")
    print(f"- Nodes: {generator.n_nodes}")
    print(f"- Communities: {len(set(generator.communities.values()))}")
    print(f"- Hub nodes: {len(generator.hub_nodes)}")
    print(f"- Zero-degree nodes: {len(generator.zero_degree_nodes)}")
    print(f"Estimated optimal score: {optimal_score}")
    
    # Run the matching solver
    import z3_test_2  # Import your solver module
    z3_test_2.main()
    
    # Verify the result
    result_matching = {}
    with open('vnc_matching_submission.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            male_node = row['Male Node ID'].strip('m')
            female_node = row['Female Node ID'].strip('f')
            result_matching[int(male_node)] = int(female_node)
    
    # Print diagnostics
    print("\nMatching properties:")
    print(f"- Size: {len(result_matching)} (expected: {generator.n_nodes})")
    print("- Missing nodes:", 
          set(range(generator.n_nodes)) - set(result_matching.keys()))
    duplicate_assignments = [
        val for val in result_matching.values() 
        if list(result_matching.values()).count(val) > 1
    ]
    print("- Duplicate assignments:", set(duplicate_assignments))

if __name__ == '__main__':
    test_matching_solver()