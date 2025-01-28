import numpy as np
from scipy.sparse import csr_matrix
from scipy.optimize import linear_sum_assignment
import cvxpy as cp

def graph_matching_osqp(A, B, tol=1e-6):
    """
    Graph matching using OSQP solver with sparse matrix handling.

    Parameters:
    A, B : np.ndarray or sparse matrix
        Adjacency matrices of the two graphs (n x n).
    lambda1, lambda2 : float
        Regularization parameters for soft row/column sum constraints.
    max_iter : int
        Maximum number of iterations for the solver.
    tol : float
        Convergence tolerance.

    Returns:
    P : np.ndarray
        Approximate permutation matrix (n x n).
    """
    n = A.shape[0]

    # Convert to sparse matrices
    A = csr_matrix(A)
    B = csr_matrix(B)

    # Define optimization variables
    P = cp.Variable((n, n), nonneg=True)

    ones_n = np.ones(n)

    # Objective function
    objective = cp.Minimize(
        cp.sum_squares(P @ A - B @ P)
    )

    # Constraints: row and column sums must equal to 1
    # Weakened pseudostochastic constraints that hold in the case of friendly graphs and are approximately true for unfriendly ones 
    constraints = [
        # P >= 0,  # Non-negativity of P
        P @ ones_n == ones_n,  # Row sum constraints
        # P.T @ ones_n == ones_n   # Column sum constraints
    ]

    # epsilon = 1e-3
    # constraints = [
    #     P @ ones_n - ones_n <= epsilon,
    #     -P @ ones_n + ones_n <= epsilon,
    #     P.T @ ones_n - ones_n <= epsilon,
    #     -P.T @ ones_n + ones_n <= epsilon,
    #     P >= 0
    # ]

    # Problem setup
    prob = cp.Problem(objective, constraints)

    # Solve with OSQP
    prob.solve(solver=cp.MOSEK, verbose=True)

    return P.value

def project_to_permutation(P):
    """
    Projects a doubly stochastic matrix to the nearest permutation matrix
    using the Hungarian algorithm.

    Parameters:
    P : np.ndarray
        Doubly stochastic matrix (n x n).

    Returns:
    np.ndarray
        Valid permutation matrix (n x n).
    """
    row_ind, col_ind = linear_sum_assignment(-P)  # Maximize weights
    P_perm = np.zeros_like(P)
    P_perm[row_ind, col_ind] = 1
    return P_perm

def permutation_to_mapping(permutation):
    return list(map(int,np.argmax(permutation, axis=1)))

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

if __name__ == "__main__":
    # Example: Sparse adjacency matrices
    n = 100
    density = 0.75

    # Generate sparse adjacency matrices
    A = np.random.rand(n, n) * (np.random.rand(n, n) < density)
    B = np.random.rand(n, n) * (np.random.rand(n, n) < density)
    # print(A)
    # Solve graph matching
    P = graph_matching_osqp(A, B)
    print("Approximate Permutation Matrix:\n", P)
    mapping = permutation_to_mapping(project_to_permutation(P))
    print("Mapping:", mapping)

    # Calculate alignment score
    alignment_score = calculate_alignment_score(A, B, mapping)
    print("Alignment Score:", alignment_score)
