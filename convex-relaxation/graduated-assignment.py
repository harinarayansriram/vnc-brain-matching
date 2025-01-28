import numpy as np
from scipy.optimize import linear_sum_assignment

# Define the Graduated Assignment Algorithm
def graduated_assignment(graph1, graph2, max_iter=100, beta=1.5, beta_update=1.05, tol=1e-5, P_init=None):
    """
    Approximate matching of two weighted directed graphs using the Graduated Assignment Algorithm.

    Parameters:
    graph1 : ndarray, adjacency matrix for graph 1
    graph2 : ndarray, adjacency matrix for graph 2
    max_iter : int, maximum number of iterations
    beta : float, initial beta for assignment matrix scaling
    beta_update : float, factor to increase beta after each iteration
    tol : float, convergence tolerance
    P_init : ndarray, optional initial assignment matrix for warm start

    Returns:
    P : ndarray, final assignment matrix
    """
    n1, n2 = graph1.shape[0], graph2.shape[0]

    if n1 != n2:
        raise ValueError("Graphs must have the same number of nodes for this implementation.")

    # Initialize the assignment matrix P
    if P_init is not None:
        P = P_init
    else:
        P = np.ones((n1, n2)) / n2

    for iteration in range(max_iter):
        if iteration % 10 == 0:
            print(f"Iteration {iteration}- Score of P: {calculate_alignment_score(graph1, graph2, permutation_to_mapping(P))}")
        # Compute compatibility matrix
        C = graph1 @ P @ graph2.T + graph1.T @ P @ graph2

        # Update P using the Hungarian algorithm
        # cost_matrix = -beta * C
        # row_ind, col_ind = linear_sum_assignment(cost_matrix)
        # P_new = np.zeros_like(P)
        # P_new[row_ind, col_ind] = 1

        # Avoid overflow by subtracting the max value in C before taking exp
        C_max = np.max(C)
        if C_max > 1:
            C /= C_max

        P_new = np.exp(beta * C)
        P_new /= P_new.sum(axis=1, keepdims=True)  # Normalize rows

        # Gradually enforce hard permutations
        if iteration > max_iter // 2:
            row_ind, col_ind = linear_sum_assignment(-P_new)
            P_hard = np.zeros_like(P)
            P_hard[row_ind, col_ind] = 1
            P_new = P_hard

        # Convergence check
        diff = np.linalg.norm(P_new - P, ord='fro')
        if diff < tol:
            break

        # Update P and beta
        P = P_new
        beta *= beta_update

    return P

# Function to warm start the algorithm with an approximate solution
def warm_start(graph1):
    """
    Generate an approximate initial solution for the assignment matrix.

    Parameters:
    graph1 : ndarray, adjacency matrix for graph 1

    Returns:
    P_init : ndarray, approximate initial assignment matrix
    """
    n = graph1.shape[0]
    # Generate a uniform initial guess for the assignment matrix
    P_init = np.ones((n, n)) / n
    return P_init

# Function to convert the permutation matrix into a node mapping
def permutation_to_mapping(P):
    """
    Convert a permutation matrix into a mapping between nodes.

    Parameters:
    P : ndarray, permutation matrix

    Returns:
    mapping : list, mapping of nodes in graph1 to nodes in graph2
    """
    mapping = list(np.argmax(P, axis=1))
    return mapping

# Function to calculate alignment score
def calculate_alignment_score(graph1, graph2, mapping):
    """
    Calculate the alignment score for two graphs given a node mapping.

    Parameters:
    graph1 : ndarray, adjacency matrix for graph 1
    graph2 : ndarray, adjacency matrix for graph 2
    mapping : list, mapping of nodes in graph1 to nodes in graph2

    Returns:
    alignment : float, alignment score
    """
    n = graph1.shape[0]
    alignment = 0
    for i in range(n):
        for j in range(n):
            alignment += min(graph1[i, j], graph2[mapping[i], mapping[j]])
    return alignment

n = 100
density = 0.75

# Generate sparse adjacency matrices
graph1 = np.random.rand(n, n) * (np.random.rand(n, n) < density)
graph2 = np.random.rand(n, n) * (np.random.rand(n, n) < density)

# Example usage:
# graph1 = np.array([
#     [0.0, 1.0, 0.0],
#     [0.0, 0.0, 2.0],
#     [3.0, 0.0, 0.0]
# ])

# graph2 = np.array([
#     [0.0, 1.1, 0.0],
#     [0.0, 0.0, 1.9],
#     [3.1, 0.0, 0.0]
# ])

# Warm start
P_init = warm_start(graph1)

# Match the graphs
P = graduated_assignment(graph1, graph2, P_init=P_init)

# Convert to mapping
mapping = permutation_to_mapping(P)

# Calculate alignment score
alignment_score = calculate_alignment_score(graph1, graph2, mapping)

print("Final assignment matrix:")
print(P)
print("Node mapping:")
print(mapping)
print("Alignment score:")
print(alignment_score)
