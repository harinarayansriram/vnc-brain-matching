import numpy as np
import scipy.sparse as sp
from scipy.sparse import csr_matrix
from scipy.optimize import linear_sum_assignment

import cvxpy as cp

n = 200  # Example large size


A = cp.Parameter((n//2, n//2), nonneg=True)
B = cp.Parameter((n//2, n//2), nonneg=True)

P = cp.Variable((n//2, n//2), nonneg=True)

ones_n = np.ones(n//2)

# Objective function
objective = cp.Minimize(
    cp.sum_squares(P @ A - B @ P)
)

# Constraints: row and column sums must equal to 1
constraints = [
    # P >= 0,  # Non-negativity of P
    P @ ones_n == ones_n,  # Row sum constraints
    # P.T @ ones_n == ones_n   # Column sum constraints
]

# Problem setup
prob = cp.Problem(objective, constraints)


def graph_matching_blocked(_A, _B, block_size=100, lambda1=10, lambda2=10, tol=1e-6):
    """
    Solve the large graph matching problem by dividing it into smaller subproblems,
    and solving them separately while maintaining doubly stochastic constraints using Sinkhorn-Knopp.
    
    Parameters:
    A, B : np.ndarray or sparse matrix
        Adjacency matrices of the two graphs (n x n).
    block_size : int
        Size of the smaller subproblems (e.g., 100 or 200).
    lambda1, lambda2 : float
        Regularization parameters for row/column sum constraints.
    tol : float
        Convergence tolerance for the solver.
    
    Returns:
    P : np.ndarray
        Approximate permutation matrix (n x n).
    """

    # Initialize the result matrix for the permutation matrix
    # P.value = np.zeros((n, n))

    # List to hold all blocks of the permutation matrix
    P_blocks = []

    # Iterate over blocks of the adjacency matrix
    for i in range(0, n, block_size):
        for j in range(0, n, block_size):
            # Define subproblems: submatrices of A and B
            A_block = _A[i:i+block_size, j:j+block_size]
            B_block = _B[i:i+block_size, j:j+block_size]

            A.value = A_block
            B.value = B_block
            
            # Solve the graph matching for this block
            P_block = graph_matching_osqp(tol)
            
            # Store the block (without modifying P yet)
            P_blocks.append((i, j, P_block))

    # Now stitch the blocks together and apply Sinkhorn-Knopp to enforce doubly stochastic
    P = stitch_blocks_sinkhorn(P_blocks, n, block_size)

    return P

def stitch_blocks_sinkhorn(P_blocks, n, block_size, max_iter=100, tol=1e-6):
    """
    Stitch together the blocks and apply Sinkhorn-Knopp to enforce doubly stochastic constraints.
    This function adjusts the placement of blocks to ensure that the final matrix P
    remains doubly stochastic (i.e., row and column sums are equal to 1).
    
    Parameters:
    P_blocks : list of tuples (i, j, P_block)
        List of blocks (row_start, col_start, block_matrix) from the graph matching solutions.
    n : int
        Size of the full matrix.
    block_size : int
        Size of each block.
    max_iter : int
        Maximum number of iterations for Sinkhorn-Knopp.
    tol : float
        Tolerance for convergence.
    
    Returns:
    P : np.ndarray
        The full permutation matrix.
    """
    _P = np.zeros((n, n))
    
    # Place each block in its corresponding position
    for i, j, P_block in P_blocks:
        _P[i:i+block_size, j:j+block_size] = P_block
    
    # Apply Sinkhorn-Knopp to enforce doubly stochastic constraints
    _P = sinkhorn_knopp(_P, max_iter, tol)

    return _P

def sinkhorn_knopp(_P, max_iter=100, tol=1e-6):
    """
    Apply Sinkhorn-Knopp algorithm to make the matrix doubly stochastic.
    
    Parameters:
    P : np.ndarray
        The matrix to be adjusted.
    max_iter : int
        Maximum number of iterations for Sinkhorn-Knopp.
    tol : float
        Tolerance for convergence.
    
    Returns:
    P : np.ndarray
        Doubly stochastic matrix.
    """
    n = _P.shape[0]
    
    for _ in range(max_iter):
        # Row normalization
        row_sums = np.sum(P, axis=1)
        _P = _P / row_sums[:, np.newaxis]

        # Column normalization
        col_sums = np.sum(_P, axis=0)
        _P = _P / col_sums[np.newaxis, :]
        
        # Check for convergence (if row and column sums are close to 1)
        if np.allclose(np.sum(_P, axis=1), np.ones(n), atol=tol) and np.allclose(np.sum(_P, axis=0), np.ones(n), atol=tol):
            break
    
    return _P

def graph_matching_osqp(tol=1e-6):
    """
    Solve the graph matching problem for small adjacency matrices A and B.
    """

    # Convert to sparse matrices
    # A = csr_matrix(A)
    # B = csr_matrix(B)

    # Define optimization variables
   
    # Solve with OSQP
    prob.solve(solver=cp.OSQP, eps_abs=tol, verbose=True)

    return P.value

def project_to_permutation(_P):
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
    row_ind, col_ind = linear_sum_assignment(-_P)  # Maximize weights
    P_perm = np.zeros_like(_P)
    P_perm[row_ind, col_ind] = 1
    return P_perm

def permutation_to_mapping(permutation):
    return list(map(int,np.argmax(permutation, axis=1)))


if __name__ == "__main__":
    # Example: Sparse adjacency matrices
    density = 0.25

    # Generate sparse adjacency matrices
    _A = np.random.rand(n, n) * (np.random.rand(n, n) < density)
    _B = np.random.rand(n, n) * (np.random.rand(n, n) < density)

    # Solve graph matching using blocked approach with Sinkhorn-Knopp
    _P = graph_matching_blocked(_A, _B, block_size=100)
    print("Approximate Permutation Matrix:\n", _P)
    mapping = permutation_to_mapping(project_to_permutation(_P))
    print("Mapping:", mapping)
