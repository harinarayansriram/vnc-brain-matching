import networkx as nx 
import matplotlib.pyplot as plt
import pandas as pd
import os
import glob
import re

# ----- Load and Build the Male Graph -----
gm = pd.read_csv("../gm.csv")

# Convert to strings, strip prefixes, then convert to integers
gm['From Node ID'] = gm['From Node ID'].astype(str).str.lstrip('m').astype(int)
gm['To Node Id'] = gm['To Node Id'].astype(str).str.lstrip('m').astype(int)

# Select top 1000 highest-weight edges
top_1000_male = gm.nlargest(3000, 'Weight')

# Create male graph
G_male = nx.from_pandas_edgelist(top_1000_male, source='From Node ID', target='To Node Id', edge_attr='Weight')

# Compute layout
pos = nx.spring_layout(G_male, seed=42, iterations=5)

# ----- Load the Female Graph -----
gf = pd.read_csv("../gf.csv")

# Convert to strings, strip 'f' prefix, then convert to integers
gf['From Node ID'] = gf['From Node ID'].astype(str).str.lstrip('f').astype(int)
gf['To Node Id'] = gf['To Node Id'].astype(str).str.lstrip('f').astype(int)

# Select top 10000 highest-weight edges for the female graph
top_10000_female = gf.nlargest(30000, 'Weight')
G_female = nx.from_pandas_edgelist(top_10000_female, source='From Node ID', target='To Node Id', edge_attr='Weight')

# ----- Get all mapping files and sort them -----
mapping_files = glob.glob("../score_lookup/new_mapping_*.csv")

# Extract number from filenames for sorting
def extract_number(filename):
    match = re.search(r'new_mapping_(\d+)\.csv', filename)
    if match:
        return int(match.group(1))
    return 0

# Sort files by the extracted number
sorted_mapping_files = sorted(mapping_files, key=extract_number)

def visualize_mapping_file(mapping_file_path, output_filename=None, male_graph_path="../gm.csv", female_graph_path="../gf.csv"):
    """
    Generate and save a visualization for a specific mapping file.
    
    Parameters:
    -----------
    mapping_file_path : str
        Path to the mapping file to visualize
    output_filename : str, optional
        Name of the output file. If None, will be derived from the mapping filename
    male_graph_path : str, optional
        Path to the male graph CSV file
    female_graph_path : str, optional
        Path to the female graph CSV file
    
    Returns:
    --------
    str
        Path to the saved visualization file
    """
    file_number = 0
    # If output_filename is not provided, derive it from the mapping filename
    if output_filename is None:
        # Extract base filename without path and extension
        base_filename = os.path.basename(mapping_file_path)
        # Try to extract a number if it exists in the pattern
        match = re.search(r'(\d+)', base_filename)
        if match:
            file_number = match.group(1)
            output_filename = f"alignment_visualization_{file_number}.png"
        else:
            # Just use the base filename if no number is found
            name_without_ext = os.path.splitext(base_filename)[0]
            output_filename = f"alignment_visualization_{name_without_ext}.png"
    
    # ----- Load and Build the Male Graph -----
    # gm = pd.read_csv(male_graph_path)
    
    # # Convert to strings, strip prefixes, then convert to integers
    # gm['From Node ID'] = gm['From Node ID'].astype(str).str.lstrip('m').astype(int)
    # gm['To Node Id'] = gm['To Node Id'].astype(str).str.lstrip('m').astype(int)
    
    # # Select top 3000 highest-weight edges
    # top_male = gm.nlargest(3000, 'Weight')
    
    # # Create male graph
    # G_male = nx.from_pandas_edgelist(top_male, source='From Node ID', target='To Node Id', edge_attr='Weight')
    
    # # Compute layout
    # pos = nx.spring_layout(G_male, seed=42, iterations=5)
    
    # # ----- Load the Female Graph -----
    # gf = pd.read_csv(female_graph_path)
    
    # # Convert to strings, strip 'f' prefix, then convert to integers
    # gf['From Node ID'] = gf['From Node ID'].astype(str).str.lstrip('f').astype(int)
    # gf['To Node Id'] = gf['To Node Id'].astype(str).str.lstrip('f').astype(int)
    
    # # Select top 30000 highest-weight edges for the female graph
    # top_female = gf.nlargest(30000, 'Weight')
    # G_female = nx.from_pandas_edgelist(top_female, source='From Node ID', target='To Node Id', edge_attr='Weight')
    
    # ----- Load alignment data and strip prefixes -----
    print(f"Processing {mapping_file_path} -> {output_filename}")
    alignment = pd.read_csv(mapping_file_path)
    alignment['Male_Node_ID'] = alignment['Male Node ID'].astype(str).str.lstrip('m').astype(int)
    alignment['Female_Node_ID'] = alignment['Female Node ID'].astype(str).str.lstrip('f').astype(int)
    
    female_to_male = pd.Series(alignment['Male_Node_ID'].values, index=alignment['Female_Node_ID']).to_dict()
    
    # ----- Map Female Graph Edges to Male Graph Positions -----
    female_edges_on_male = [
        (female_to_male[u], female_to_male[v])
        for u, v in G_female.edges()
        if u in female_to_male and v in female_to_male and
        female_to_male[u] in pos and female_to_male[v] in pos and
        G_male.has_edge(female_to_male[u], female_to_male[v])
    ]
    
    # ----- Visualize Both Graphs on the Same Plot -----
    plt.figure(figsize=(10, 10))
    nx.draw_networkx_nodes(G_male, pos, node_color='black', node_size=7.5)
    nx.draw_networkx_edges(G_male, pos, edge_color='cornflowerblue', alpha=0.5, label="Male Graph", width=2.0)
    nx.draw_networkx_edges(
        G_male,
        pos,
        edgelist=female_edges_on_male,
        edge_color='red',
        alpha=0.5,
        width=2.0,
        style='dashed',
        label="Female Graph (Aligned)"
    )
    plt.title(f"Graph Alignment: Score of {5853925}")
    plt.legend(loc="best")
    plt.axis('off')
    
    # Save the figure
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_filename

'''
# Process every 10th file
for i in range(0, len(sorted_mapping_files), 10):
    mapping_file = sorted_mapping_files[i]
    
    # Extract the number for the output filename
    file_number = extract_number(mapping_file)
    output_filename = f"alignment_visualization_{file_number}.png"
    
    print(f"Processing {mapping_file} -> {output_filename}")
    
    # Load alignment data and strip prefixes
    alignment = pd.read_csv(mapping_file)
    alignment['Male_Node_ID'] = alignment['Male Node ID'].astype(str).str.lstrip('m').astype(int)
    alignment['Female_Node_ID'] = alignment['Female Node ID'].astype(str).str.lstrip('f').astype(int)

    female_to_male = pd.Series(alignment['Male_Node_ID'].values, index=alignment['Female_Node_ID']).to_dict()

    # ----- Map Female Graph Edges to Male Graph Positions -----
    # For each female edge, map it to its corresponding male nodes and
    # only include it if that male edge exists in the top 1000 male edges.
    female_edges_on_male = [
        (female_to_male[u], female_to_male[v])
        for u, v in G_female.edges()
        if u in female_to_male and v in female_to_male and
        female_to_male[u] in pos and female_to_male[v] in pos and
        G_male.has_edge(female_to_male[u], female_to_male[v])
    ]

    # ----- Visualize Both Graphs on the Same Plot -----
    plt.figure(figsize=(10, 10))
    nx.draw_networkx_nodes(G_male, pos, node_color='black', node_size=7.5)  # Smaller nodes
    nx.draw_networkx_edges(G_male, pos, edge_color='cornflowerblue', alpha=0.5, width=2.0, label="Male Graph")
    nx.draw_networkx_edges(
        G_male,
        pos,
        edgelist=female_edges_on_male,
        edge_color='red',
        alpha=0.5,
        width=2.0,
        style='dashed',
        label="Female Graph (Aligned)"
    )
    plt.title(f"Graph Alignment: Score of {file_number}")
    plt.legend(loc="best")
    plt.axis('off')
    
    # Save the figure instead of displaying it
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
    plt.close()  # Close the figure to free memory

'''
visualize_mapping_file("../score_lookup/5853925.csv", "alignment_visualization_5853925.png")

print("Processing complete!")