import numpy as np
from scipy.optimize import linear_sum_assignment

def sinkhorn_normalization(P, max_iter=100, tol=1e-6):
    """
    Project a matrix onto the space of doubly stochastic matrices using Sinkhorn normalization.
    """
    for _ in range(max_iter):
        P /= P.sum(axis=1, keepdims=True)  # Row normalization
        P /= P.sum(axis=0, keepdims=True)  # Column normalization
        if np.allclose(P.sum(axis=1), 1, atol=tol) and np.allclose(P.sum(axis=0), 1, atol=tol):
            break
    return P

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


def graph_matching_gradient(graph1, graph2, max_iter=100, lr=0.01, tol=1e-4):
    """
    Match two graphs using gradient-based optimization on a relaxed doubly stochastic matrix.

    Parameters:
    graph1 : ndarray, adjacency matrix for graph 1
    graph2 : ndarray, adjacency matrix for graph 2
    max_iter : int, maximum number of iterations
    lr : float, learning rate
    tol : float, convergence tolerance

    Returns:
    P : ndarray, final assignment matrix (doubly stochastic)
    """
    n = graph1.shape[0]
    # Initialize P as a uniform doubly stochastic matrix
    P = np.ones((n, n)) / n

    for iteration in range(max_iter):
        
        # Compute soft alignment cost matrix
        # C = graph1 @ P @ graph2.T + graph1.T @ P @ graph2

      # Compute smooth alignment approximation
        diff = np.abs(graph1 - P @ graph2 @ P.T)
        alignment_approx = (graph1 + P @ graph2 @ P.T - diff) / 2

        if iteration % 10 == 0:
            print(f"Iteration {iteration}- Objective score: {alignment_approx}, Actual Score of P: {calculate_alignment_score(graph1, graph2, permutation_to_mapping(P))}")

        # Compute gradient of the objective
        grad = -alignment_approx

        # Gradient descent step
        P -= lr * grad

        # Project P back to the doubly stochastic space
        P = sinkhorn_normalization(P)

        # Check for convergence
        grad_norm = np.linalg.norm(grad, ord='fro')
        if grad_norm < tol:
            break
    

    row_ind, col_ind = linear_sum_assignment(-P)
    P_hard = np.zeros_like(P)
    P_hard[row_ind, col_ind] = 1
    
    return P_hard
n = 100
density = 0.75

# Generate sparse adjacency matrices
graph1 = np.random.rand(n, n) * (np.random.rand(n, n) < density)
graph2 = np.random.rand(n, n) * (np.random.rand(n, n) < density)

# Match the graphs
P = graph_matching_gradient(graph1, graph2)

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
