import numpy as np
import cvxpy as cp
import csv
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix

# Function to build adjacency matrix from graph
# Graph is a list of tuples (from_node, to_node, weight)
def build_adjacency_matrix(graph, num_nodes):
    adjacency = np.zeros((num_nodes, num_nodes))
    for from_node, to_node, weight in graph:
        adjacency[from_node, to_node] = weight
    return adjacency

def read_csv_to_tuples(filename):
    """
    Read a CSV file and return a list of tuples.
    
    Args:
        filename (str): Path to the CSV file
    
    Returns:
        list: A list of tuples containing node connections and weights
    """
    connections = []
    
    with open(filename, 'r') as csvfile:
        # Skip the header row
        csv_reader = csv.reader(csvfile)
        next(csv_reader)
        
        # Convert each row to a tuple of integers
        for row in csv_reader:
            from_node = int(row[0])-1
            to_node = int(row[1])-1
            weight = int(row[2])
            connections.append((from_node, to_node, weight))
    
    return connections

def save_mapping(mapping, filename):
    with open(filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Male Node ID', 'Female Node ID'])
        
        for m_id, f_id in enumerate(mapping, start=1):
            csv_writer.writerow([f'm{m_id+1}', f'f{f_id+1}'])

def permutation_to_mapping(permutation):
    return list(map(int,np.argmax(permutation, axis=1)))

def graph_matching(A, B, P_approx=None, time_limit=10):
    """
    Implements convex relaxation of the graph isomorphism problem
    with time and iteration limits, projecting the solution to permutation matrices.
    
    Parameters:
    A, B: np.ndarray
        Adjacency matrices of the two graphs (n x n), which can
        be weighted and directed.
    P_approx: np.ndarray, optional
        Approximate solution for warm start (n x n).
    time_limit: int, optional
        Time limit for the solver in seconds (default: 10).
    max_iters: int, optional
        Maximum iterations for the solver (default: 1000).
    
    Returns:
    P_final: np.ndarray
        The final permutation matrix (n x n).
    """
    n = A.shape[0]

    # Step 1: Convex Relaxation with Time and Iteration Limits
    P = cp.Variable((n, n), nonneg=True)

    if P_approx is not None:
        P.value = P_approx

    objective = cp.Minimize(cp.norm(P @ A - B @ P, 'fro') ** 2)
    constraints = [P @ np.ones(n) == np.ones(n), P.T @ np.ones(n) == np.ones(n)]
    # Relaxed constraints for sparsity
    # epsilon = 1e-3
    # constraints = [
    #     P @ np.ones(n) - np.ones(n) <= epsilon,
    #     -P @ np.ones(n) + np.ones(n) <= epsilon,
    #     P.T @ np.ones(n) - np.ones(n) <= epsilon,
    #     -P.T @ np.ones(n) + np.ones(n) <= epsilon,
    #     P >= 0
    # ]
    prob = cp.Problem(objective, constraints)

    # Solver-specific options
    solver_opts = {
        "time_limit_secs": time_limit
    }
    
    # Solve using SCS with options
    prob.solve(solver=cp.MOSEK, **solver_opts, verbose=True, canon_backend=cp.SCIPY_CANON_BACKEND)

    # Relaxed solution
    P_relaxed = P.value

    # Step 2: Project to Permutation Matrix
    row_ind, col_ind = linear_sum_assignment(-P_relaxed)
    P_final = np.zeros_like(P_relaxed)
    P_final[row_ind, col_ind] = 1

    return P_final


def sinkhorn_knopp(P, max_iter=100, tol=1e-6):
    """
    Enforces approximate doubly stochastic constraints on matrix P
    using the Sinkhorn-Knopp algorithm.

    Parameters:
    P : np.ndarray
        Initial matrix (n x n) with positive entries.
    max_iter : int
        Maximum number of iterations.
    tol : float
        Convergence tolerance.

    Returns:
    np.ndarray
        Approximately doubly stochastic matrix.
    """
    for _ in range(max_iter):
        # Normalize rows
        P /= P.sum(axis=1, keepdims=True)
        # Normalize columns
        P /= P.sum(axis=0, keepdims=True)
        # Check convergence
        if np.allclose(P.sum(axis=1), 1, atol=tol) and np.allclose(P.sum(axis=0), 1, atol=tol):
            break
    return P

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

def graph_matching_sinkhorn(A, B, max_iter=200, tol=1e-6):
    """
    Performs approximate graph matching using Sinkhorn-Knopp
    to enforce doubly stochastic constraints.

    Parameters:
    A, B : np.ndarray
        Adjacency matrices of the two graphs (n x n).
    max_iter : int
        Maximum number of Sinkhorn iterations.
    tol : float
        Convergence tolerance.

    Returns:
    P : np.ndarray
        Approximate permutation matrix (n x n).
    """
    n = A.shape[0]

    # Initialize P with positive entries (e.g., uniform)
    P = np.random.rand(n, n)

    # Sinkhorn-Knopp normalization to approximate doubly stochastic
    # P = sinkhorn_knopp(P, max_iter=max_iter, tol=tol)

    # Compute objective: ||PA - BP||_F^2
    for _ in range(max_iter):
        gradient = -2 * (A @ P - P @ B)
        P -= 0.01 * gradient  # Gradient descent step
        P = np.maximum(P, 0)
        P = sinkhorn_knopp(P, max_iter=max_iter, tol=tol)  # Re-normalize to doubly stochastic
        P_perm = project_to_permutation(P)

         # Check convergence (optional)
        if np.linalg.norm(P - P_perm, 'fro') < tol:
            break

        # Update P to the projected permutation matrix
        P = P_perm


    return P

def graph_matching_sparse_mosek(A, B, tol=1e-6, max_iter=1000):
    """
    Graph matching using sparse representation, constraint relaxation,
    and MOSEK solver.

    Parameters:
    A, B : np.ndarray or sparse matrix
        Adjacency matrices of the two graphs (n x n).
    tol : float
        Convergence tolerance.
    max_iter : int
        Maximum number of iterations.

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

    # Relax constraints
    objective = cp.Minimize(cp.norm(P @ A - B @ P, "fro") ** 2 +
                            cp.norm(P @ np.ones(n) - np.ones(n), 2) ** 2 +
                            cp.norm(P.T @ np.ones(n) - np.ones(n), 2) ** 2)

    # Add non-negativity constraint
    constraints = [P >= 0]

    # Set up the problem
    prob = cp.Problem(objective, constraints)

    # Solve with MOSEK (or other sparse-capable solver)
    prob.solve(solver=cp.MOSEK, verbose=True)

    return project_to_permutation(P.value)


# Example Usage
if __name__ == "__main__":
    graphA = [
        (0, 1, 1.0),
        (0, 2, 2.0),
        (1, 3, 3.0),
        (2, 3, 1.5)
    ]
    graphB = [
        (0, 2, 1.1),
        (0, 3, 2.1),
        (1, 0, 3.1),
        (2, 1, 1.4)
    ]
    # graphA = read_csv_to_tuples("gm.csv")
    # graphB = read_csv_to_tuples("gf.csv")

    print("Read graphs")

    # num_nodes = 18524
    num_nodes = 4

    # Example adjacency matrices
    # A = np.array([
    #     [0, 1, 0],
    #     [1, 0, 1],
    #     [0, 1, 0]
    # ])
    # A = build_adjacency_matrix(graphA, num_nodes)
    # B = build_adjacency_matrix(graphB, num_nodes)
    A = np.random.rand(100,100)
    A_mask = np.random.rand(100,100) < 0.75
    B = np.random.rand(100, 100)
    B_mask = np.random.rand(100, 100) < 0.75
    
    A[A_mask] = 0
    B[B_mask] = 0


    # A_sparse = csr_matrix(A)
    # B_sparse = csr_matrix(B)

    # print(A_sparse)
    # B = np.array([
    #     [0, 1, 1],
    #     [1, 0, 0],
    #     [1, 0, 0]
    # ])

    P = graph_matching_sparse_mosek(A, B)
    print("Finished matching")
    mapping = permutation_to_mapping(P)
    # print("Permutation Matrix:\n", P)
    print("Mapping: ", mapping)
    save_mapping(mapping, 'convex-finetune.csv')
    print("Saved")
