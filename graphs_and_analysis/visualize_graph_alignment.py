import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import networkx as nx
import seaborn as sns
from scipy.sparse import csr_matrix
from tqdm import tqdm
import os

def load_graph_data(file_path):
    """Load graph data from CSV file."""
    df = pd.read_csv(file_path)
    return df

def load_mapping(file_path):
    """Load node mapping data from CSV file."""
    df = pd.read_csv(file_path)
    return df

def compute_jaccard_similarity(graph_m, graph_f, mapping):
    """
    Compute modified Jaccard similarity for the current mapping.
    Modified Jaccard = sum of min(weight_m, weight_f) for overlapping edges
    """
    # Create dictionaries for faster edge lookup
    m_edges = {}
    for _, row in graph_m.iterrows():
        m_edges[(row['From Node ID'], row['To Node Id'])] = row['Weight']
    
    f_edges = {}
    for _, row in graph_f.iterrows():
        f_edges[(row['From Node ID'], row['To Node Id'])] = row['Weight']
    
    # Create mapping dictionaries
    m_to_f = dict(zip(mapping['Male Node ID'], mapping['Female Node ID']))
    f_to_m = dict(zip(mapping['Female Node ID'], mapping['Male Node ID']))
    
    # Compute similarity
    similarity = 0
    
    for (m_from, m_to), m_weight in tqdm(m_edges.items(), desc="Computing similarity"):
        if m_from in m_to_f and m_to in m_to_f:
            f_from = m_to_f[m_from]
            f_to = m_to_f[m_to]
            
            if (f_from, f_to) in f_edges:
                f_weight = f_edges[(f_from, f_to)]
                similarity += min(m_weight, f_weight)
    
    return similarity

def create_adjacency_matrices(graph_m, graph_f, all_nodes_m, all_nodes_f):
    """Create adjacency matrices for both graphs."""
    # Create node ID to index mapping
    node_to_idx_m = {node: i for i, node in enumerate(all_nodes_m)}
    node_to_idx_f = {node: i for i, node in enumerate(all_nodes_f)}
    
    # Create sparse adjacency matrices
    rows_m, cols_m, data_m = [], [], []
    for _, row in graph_m.iterrows():
        if row['From Node ID'] in node_to_idx_m and row['To Node Id'] in node_to_idx_m:
            i = node_to_idx_m[row['From Node ID']]
            j = node_to_idx_m[row['To Node Id']]
            rows_m.append(i)
            cols_m.append(j)
            data_m.append(row['Weight'])
    
    rows_f, cols_f, data_f = [], [], []
    for _, row in graph_f.iterrows():
        if row['From Node ID'] in node_to_idx_f and row['To Node Id'] in node_to_idx_f:
            i = node_to_idx_f[row['From Node ID']]
            j = node_to_idx_f[row['To Node Id']]
            rows_f.append(i)
            cols_f.append(j)
            data_f.append(row['Weight'])
    
    n_m = len(all_nodes_m)
    n_f = len(all_nodes_f)
    
    adj_m = csr_matrix((data_m, (rows_m, cols_m)), shape=(n_m, n_m))
    adj_f = csr_matrix((data_f, (rows_f, cols_f)), shape=(n_f, n_f))
    
    return adj_m, adj_f, node_to_idx_m, node_to_idx_f

def visualize_graph_statistics(graph_m, graph_f, output_path="graph_statistics.png"):
    """Visualize basic statistics of both graphs for comparison."""
    # Calculate degree distributions
    degree_m = graph_m.groupby('From Node ID').size()
    degree_f = graph_f.groupby('From Node ID').size()
    
    # Calculate weight distributions
    weights_m = graph_m['Weight']
    weights_f = graph_f['Weight']
    
    # Create a figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # Degree distributions
    sns.histplot(degree_m, kde=True, ax=axes[0, 0], log_scale=(True, True), color='blue')
    axes[0, 0].set_title('Degree Distribution - Graph M')
    axes[0, 0].set_xlabel('Degree')
    axes[0, 0].set_ylabel('Count')
    
    sns.histplot(degree_f, kde=True, ax=axes[0, 1], log_scale=(True, True), color='red')
    axes[0, 1].set_title('Degree Distribution - Graph F')
    axes[0, 1].set_xlabel('Degree')
    axes[0, 1].set_ylabel('Count')
    
    # Weight distributions
    sns.histplot(weights_m, kde=True, ax=axes[1, 0], log_scale=(False, True), color='blue')
    axes[1, 0].set_title('Weight Distribution - Graph M')
    axes[1, 0].set_xlabel('Weight')
    axes[1, 0].set_ylabel('Count')
    
    sns.histplot(weights_f, kde=True, ax=axes[1, 1], log_scale=(False, True), color='red')
    axes[1, 1].set_title('Weight Distribution - Graph F')
    axes[1, 1].set_xlabel('Weight')
    axes[1, 1].set_ylabel('Count')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_path

def create_alignment_matrix(mapping, all_nodes_m, all_nodes_f):
    """Create a binary alignment matrix based on the mapping."""
    n_m = len(all_nodes_m)
    n_f = len(all_nodes_f)
    
    node_to_idx_m = {node: i for i, node in enumerate(all_nodes_m)}
    node_to_idx_f = {node: i for i, node in enumerate(all_nodes_f)}
    
    alignment_matrix = np.zeros((n_m, n_f))
    
    for _, row in mapping.iterrows():
        if row['Male Node ID'] in node_to_idx_m and row['Female Node ID'] in node_to_idx_f:
            i = node_to_idx_m[row['Male Node ID']]
            j = node_to_idx_f[row['Female Node ID']]
            alignment_matrix[i, j] = 1
    
    return alignment_matrix

def visualize_alignment_matrix(alignment_matrix, output_path="alignment_matrix.png"):
    """Visualize the alignment matrix as a heatmap."""
    plt.figure(figsize=(12, 10))
    
    # Sample down if the matrix is too large
    sample_size = 500
    if alignment_matrix.shape[0] > sample_size or alignment_matrix.shape[1] > sample_size:
        rows = np.linspace(0, alignment_matrix.shape[0]-1, sample_size, dtype=int)
        cols = np.linspace(0, alignment_matrix.shape[1]-1, sample_size, dtype=int)
        alignment_matrix_sample = alignment_matrix[rows, :][:, cols]
        plt.imshow(alignment_matrix_sample, cmap='Blues', interpolation='nearest')
        plt.title(f"Alignment Matrix (Sampled to {sample_size}x{sample_size})")
    else:
        plt.imshow(alignment_matrix, cmap='Blues', interpolation='nearest')
        plt.title("Alignment Matrix")
    
    plt.colorbar(label="Alignment")
    plt.xlabel("Female Nodes")
    plt.ylabel("Male Nodes")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_path

def visualize_edge_matching(graph_m, graph_f, mapping, output_path="edge_matching.png"):
    """Visualize edge matching between the two graphs."""
    # Create dictionaries for faster edge lookup
    m_edges = {}
    for _, row in graph_m.iterrows():
        m_edges[(row['From Node ID'], row['To Node Id'])] = row['Weight']
    
    f_edges = {}
    for _, row in graph_f.iterrows():
        f_edges[(row['From Node ID'], row['To Node Id'])] = row['Weight']
    
    # Create mapping dictionaries
    m_to_f = dict(zip(mapping['Male Node ID'], mapping['Female Node ID']))
    
    # Count matched edges
    matched_edges = 0
    total_edges = len(m_edges)
    
    for (m_from, m_to) in m_edges.keys():
        if m_from in m_to_f and m_to in m_to_f:
            f_from = m_to_f[m_from]
            f_to = m_to_f[m_to]
            
            if (f_from, f_to) in f_edges:
                matched_edges += 1
    
    # Create a pie chart
    plt.figure(figsize=(10, 8))
    plt.pie([matched_edges, total_edges - matched_edges], 
            labels=['Matched Edges', 'Unmatched Edges'],
            autopct='%1.1f%%', 
            colors=['green', 'red'],
            explode=(0.1, 0),
            startangle=90)
    plt.title('Edge Matching Performance')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_path

def create_community_structure(graph_df, n_communities=20):
    """Extract community structure using graph partitioning."""
    G = nx.Graph()
    
    # Add edges from the DataFrame
    for _, row in graph_df.iterrows():
        G.add_edge(row['From Node ID'], row['To Node Id'], weight=row['Weight'])
    
    # Use Louvain community detection
    try:
        from community import community_louvain
        partition = community_louvain.best_partition(G)
    except ImportError:
        # Fallback to simpler approach if python-louvain is not installed
        # This will be slower and less accurate
        partition = {}
        for node in G.nodes():
            partition[node] = hash(node) % n_communities
    
    return partition

def visualize_community_alignment(graph_m, graph_f, mapping, output_path="community_alignment.png"):
    """Visualize how well communities align between the two graphs."""
    # Extract community structures
    print("Extracting communities for graph M...")
    communities_m = create_community_structure(graph_m)
    print("Extracting communities for graph F...")
    communities_f = create_community_structure(graph_f)
    
    # Create mapping dictionaries
    m_to_f = dict(zip(mapping['Male Node ID'], mapping['Female Node ID']))
    
    # Create community alignment matrix
    max_community_m = max(communities_m.values()) + 1
    max_community_f = max(communities_f.values()) + 1
    
    alignment_matrix = np.zeros((max_community_m, max_community_f))
    
    for m_node, m_comm in communities_m.items():
        if m_node in m_to_f:
            f_node = m_to_f[m_node]
            if f_node in communities_f:
                f_comm = communities_f[f_node]
                alignment_matrix[m_comm, f_comm] += 1
    
    # Normalize by row
    row_sums = alignment_matrix.sum(axis=1, keepdims=True)
    normalized_matrix = np.divide(alignment_matrix, row_sums, where=row_sums != 0)
    
    # Visualize
    plt.figure(figsize=(12, 10))
    plt.imshow(normalized_matrix, cmap='viridis', interpolation='nearest')
    plt.colorbar(label="Proportion of Nodes")
    plt.xlabel("Female Communities")
    plt.ylabel("Male Communities")
    plt.title("Community Alignment Matrix")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_path

def visualize_alignment_comparison(random_similarity, optimized_similarity, output_path="alignment_comparison.png"):
    """Visualize the comparison between random and optimized alignments."""
    plt.figure(figsize=(10, 8))
    
    plt.bar(['Random Alignment', 'Optimized Alignment'], 
            [random_similarity, optimized_similarity],
            color=['#FF9999', '#99FF99'])
    
    improvement = ((optimized_similarity - random_similarity) / random_similarity) * 100
    
    plt.title(f"Alignment Similarity Comparison\n({improvement:.2f}% Improvement)")
    plt.ylabel("Modified Jaccard Similarity")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add text annotations
    plt.text(0, random_similarity/2, f"{random_similarity:.2f}", 
             ha='center', va='center', fontweight='bold')
    plt.text(1, optimized_similarity/2, f"{optimized_similarity:.2f}", 
             ha='center', va='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_path

def node_importance_analysis(graph_m, graph_f, mapping, output_path="node_importance.png"):
    """Analyze and visualize node importance in both graphs."""
    # Create NetworkX graphs
    G_m = nx.Graph()
    for _, row in graph_m.iterrows():
        G_m.add_edge(row['From Node ID'], row['To Node Id'], weight=row['Weight'])
    
    G_f = nx.Graph()
    for _, row in graph_f.iterrows():
        G_f.add_edge(row['From Node ID'], row['To Node Id'], weight=row['Weight'])
    
    # Calculate node importance metrics
    degree_m = dict(G_m.degree())
    degree_f = dict(G_f.degree())
    
    # Calculate betweenness centrality (this can be slow for large graphs)
    print("Calculating approximate betweenness centrality for graph M...")
    betweenness_m = nx.betweenness_centrality(G_m, k=100, normalized=True)  # Approximate with sampling
    
    print("Calculating approximate betweenness centrality for graph F...")
    betweenness_f = nx.betweenness_centrality(G_f, k=100, normalized=True)  # Approximate with sampling
    
    # Create mapping dictionaries
    m_to_f = dict(zip(mapping['Male Node ID'], mapping['Female Node ID']))
    
    # Extract metrics for mapped nodes
    mapped_nodes = []
    degree_m_values = []
    degree_f_values = []
    betweenness_m_values = []
    betweenness_f_values = []
    
    for m_node, f_node in m_to_f.items():
        if m_node in degree_m and f_node in degree_f:
            mapped_nodes.append((m_node, f_node))
            degree_m_values.append(degree_m[m_node])
            degree_f_values.append(degree_f[f_node])
            betweenness_m_values.append(betweenness_m.get(m_node, 0))
            betweenness_f_values.append(betweenness_f.get(f_node, 0))
    
    # Visualize
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    
    # Degree correlation
    axes[0].scatter(degree_m_values, degree_f_values, alpha=0.5)
    axes[0].set_xlabel("Male Node Degree")
    axes[0].set_ylabel("Female Node Degree")
    axes[0].set_title("Degree Correlation in Mapped Nodes")
    
    # Add correlation coefficient
    corr_coef = np.corrcoef(degree_m_values, degree_f_values)[0, 1]
    axes[0].annotate(f"Correlation: {corr_coef:.2f}", 
                     xy=(0.05, 0.95), 
                     xycoords='axes fraction',
                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
    
    # Betweenness correlation
    axes[1].scatter(betweenness_m_values, betweenness_f_values, alpha=0.5)
    axes[1].set_xlabel("Male Node Betweenness")
    axes[1].set_ylabel("Female Node Betweenness")
    axes[1].set_title("Betweenness Correlation in Mapped Nodes")
    
    # Add correlation coefficient
    corr_coef = np.corrcoef(betweenness_m_values, betweenness_f_values)[0, 1]
    axes[1].annotate(f"Correlation: {corr_coef:.2f}", 
                     xy=(0.05, 0.95), 
                     xycoords='axes fraction',
                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_path

def visualize_alignment_heatmap(graph_m, graph_f, random_mapping, optimized_mapping, output_path="alignment_heatmap.png"):
    """Create a heatmap visualization showing the improvement in alignment."""
    # Create mapping dictionaries
    random_m_to_f = dict(zip(random_mapping['Male Node ID'], random_mapping['Female Node ID']))
    optimized_m_to_f = dict(zip(optimized_mapping['Male Node ID'], optimized_mapping['Female Node ID']))
    
    # Create dictionaries for faster edge lookup
    m_edges = {}
    for _, row in graph_m.iterrows():
        m_edges[(row['From Node ID'], row['To Node Id'])] = row['Weight']
    
    f_edges = {}
    for _, row in graph_f.iterrows():
        f_edges[(row['From Node ID'], row['To Node Id'])] = row['Weight']
    
    # Calculate edge matching for both mappings
    random_matched = {}
    optimized_matched = {}
    
    for (m_from, m_to), m_weight in tqdm(m_edges.items(), desc="Calculating edge matching"):
        # Random mapping
        if m_from in random_m_to_f and m_to in random_m_to_f:
            f_from = random_m_to_f[m_from]
            f_to = random_m_to_f[m_to]
            
            if (f_from, f_to) in f_edges:
                f_weight = f_edges[(f_from, f_to)]
                random_matched[(m_from, m_to)] = min(m_weight, f_weight)
        
        # Optimized mapping
        if m_from in optimized_m_to_f and m_to in optimized_m_to_f:
            f_from = optimized_m_to_f[m_from]
            f_to = optimized_m_to_f[m_to]
            
            if (f_from, f_to) in f_edges:
                f_weight = f_edges[(f_from, f_to)]
                optimized_matched[(m_from, m_to)] = min(m_weight, f_weight)
    
    # Create visualization
    # For visualization, we'll create a comparison of the top 100 edges by weight
    top_edges = sorted(m_edges.items(), key=lambda x: x[1], reverse=True)[:100]
    
    edge_indices = [f"{m_from}-{m_to}" for (m_from, m_to), _ in top_edges]
    random_values = [random_matched.get((m_from, m_to), 0) for (m_from, m_to), _ in top_edges]
    optimized_values = [optimized_matched.get((m_from, m_to), 0) for (m_from, m_to), _ in top_edges]
    
    # Create a DataFrame for easier plotting
    df = pd.DataFrame({
        'Edge': edge_indices,
        'Random': random_values,
        'Optimized': optimized_values
    })
    
    # Melt the DataFrame for seaborn
    df_melted = pd.melt(df, id_vars=['Edge'], var_name='Mapping', value_name='Weight')
    
    # Plot
    plt.figure(figsize=(15, 10))
    sns.heatmap(df.set_index('Edge')[['Random', 'Optimized']], cmap='YlGnBu')
    plt.title("Edge Matching Comparison: Random vs. Optimized Alignment")
    plt.ylabel("Top 100 Edges by Weight")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_path

def create_alignment_visualization(graph_m_path, graph_f_path, random_mapping_path, optimized_mapping_path, output_dir="alignment_visualization"):
    """Create a comprehensive visualization of the graph alignment."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    print("Loading graph data...")
    graph_m = load_graph_data(graph_m_path)
    graph_f = load_graph_data(graph_f_path)
    random_mapping = load_mapping(random_mapping_path)
    optimized_mapping = load_mapping(optimized_mapping_path)
    
    print(f"Graph M: {len(graph_m)} edges")
    print(f"Graph F: {len(graph_f)} edges")
    
    # Get all unique nodes
    all_nodes_m = set(graph_m['From Node ID'].unique()) | set(graph_m['To Node Id'].unique())
    all_nodes_f = set(graph_f['From Node ID'].unique()) | set(graph_f['To Node Id'].unique())
    
    print(f"Graph M: {len(all_nodes_m)} nodes")
    print(f"Graph F: {len(all_nodes_f)} nodes")
    
    # Create visualizations
    print("Creating visualizations...")
    
    # Basic graph statistics
    stats_path = os.path.join(output_dir, "graph_statistics.png")
    visualize_graph_statistics(graph_m, graph_f, stats_path)
    
    # Compute alignment similarities
    print("Computing random alignment similarity...")
    random_similarity = compute_jaccard_similarity(graph_m, graph_f, random_mapping)
    
    print("Computing optimized alignment similarity...")
    optimized_similarity = compute_jaccard_similarity(graph_m, graph_f, optimized_mapping)
    
    print(f"Random Alignment Similarity: {random_similarity}")
    print(f"Optimized Alignment Similarity: {optimized_similarity}")
    print(f"Improvement: {((optimized_similarity - random_similarity) / random_similarity) * 100:.2f}%")
    
    # Visualize alignment comparison
    comparison_path = os.path.join(output_dir, "alignment_comparison.png")
    visualize_alignment_comparison(random_similarity, optimized_similarity, comparison_path)
    
    # Visualize alignment matrices
    print("Creating alignment matrices...")
    random_matrix_path = os.path.join(output_dir, "random_alignment_matrix.png")
    random_matrix = create_alignment_matrix(random_mapping, list(all_nodes_m), list(all_nodes_f))
    visualize_alignment_matrix(random_matrix, random_matrix_path)
    
    optimized_matrix_path = os.path.join(output_dir, "optimized_alignment_matrix.png")
    optimized_matrix = create_alignment_matrix(optimized_mapping, list(all_nodes_m), list(all_nodes_f))
    visualize_alignment_matrix(optimized_matrix, optimized_matrix_path)
    
    # Visualize edge matching
    print("Visualizing edge matching...")
    random_edge_path = os.path.join(output_dir, "random_edge_matching.png")
    visualize_edge_matching(graph_m, graph_f, random_mapping, random_edge_path)
    
    optimized_edge_path = os.path.join(output_dir, "optimized_edge_matching.png")
    visualize_edge_matching(graph_m, graph_f, optimized_mapping, optimized_edge_path)
    
    # Visualize community alignment
    print("Visualizing community alignment...")
    random_community_path = os.path.join(output_dir, "random_community_alignment.png")
    visualize_community_alignment(graph_m, graph_f, random_mapping, random_community_path)
    
    optimized_community_path = os.path.join(output_dir, "optimized_community_alignment.png")
    visualize_community_alignment(graph_m, graph_f, optimized_mapping, optimized_community_path)
    
    # Visualize node importance
    print("Analyzing node importance...")
    node_importance_path = os.path.join(output_dir, "node_importance.png")
    node_importance_analysis(graph_m, graph_f, optimized_mapping, node_importance_path)
    
    # Create alignment heatmap
    print("Creating alignment heatmap...")
    heatmap_path = os.path.join(output_dir, "alignment_heatmap.png")
    visualize_alignment_heatmap(graph_m, graph_f, random_mapping, optimized_mapping, heatmap_path)
    
    # Create a summary visualization
    print("Creating summary visualization...")
    create_summary_visualization(
        os.path.join(output_dir, "alignment_comparison.png"),
        os.path.join(output_dir, "random_edge_matching.png"),
        os.path.join(output_dir, "optimized_edge_matching.png"),
        os.path.join(output_dir, "alignment_heatmap.png"),
        os.path.join(output_dir, "summary.png")
    )
    
    print(f"All visualizations created in {output_dir}")

def create_summary_visualization(comparison_path, random_edge_path, optimized_edge_path, heatmap_path, output_path):
    """Create a summary visualization combining multiple plots."""
    from matplotlib.gridspec import GridSpec
    
    fig = plt.figure(figsize=(20, 15))
    gs = GridSpec(2, 2, figure=fig)
    
    # Load and place comparison plot
    ax1 = fig.add_subplot(gs[0, 0])
    img1 = plt.imread(comparison_path)
    ax1.imshow(img1)
    ax1.axis('off')
    ax1.set_title("Alignment Similarity Comparison", fontsize=16)
    
    # Load and place edge matching plots
    ax2 = fig.add_subplot(gs[0, 1])
    img2 = plt.imread(random_edge_path)
    ax2.imshow(img2)
    ax2.axis('off')
    ax2.set_title("Random Alignment Edge Matching", fontsize=16)
    
    ax3 = fig.add_subplot(gs[1, 0])
    img3 = plt.imread(optimized_edge_path)
    ax3.imshow(img3)
    ax3.axis('off')
    ax3.set_title("Optimized Alignment Edge Matching", fontsize=16)
    
    # Load and place heatmap
    ax4 = fig.add_subplot(gs[1, 1])
    img4 = plt.imread(heatmap_path)
    ax4.imshow(img4)
    ax4.axis('off')
    ax4.set_title("Edge Matching Comparison Heatmap", fontsize=16)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_path

# Example usage
if __name__ == "__main__":
    # Path to input files
    graph_m_path = "../gm.csv"
    graph_f_path = "../gf.csv"
    random_mapping_path = "../benchmark.csv"
    optimized_mapping_path = "../score_lookup/5853925.csv"
    
    # Create visualizations
    create_alignment_visualization(graph_m_path, graph_f_path, random_mapping_path, optimized_mapping_path)