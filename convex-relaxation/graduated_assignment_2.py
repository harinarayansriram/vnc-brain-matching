import numpy as np
from scipy import sparse
import numpy.ma as ma

from scipy.optimize import linear_sum_assignment

def graduated_assignment(A, B, beta_0=0.5, beta_f=10, beta_r=1.075, 
                       max_iter=300, inner_iter=30, e_conv=1e-3):
    """
    Graduated Assignment algorithm for graph matching.
    
    Parameters:
    -----------
    A, B : scipy.sparse.csr_matrix or numpy.ndarray
        Adjacency matrices of the graphs to be matched
    beta_0 : float
        Initial inverse temperature
    beta_f : float
        Final inverse temperature
    beta_r : float
        Factor to increase beta each outer iteration
    max_iter : int
        Maximum number of outer iterations
    inner_iter : int
        Maximum number of inner iterations per temperature
    e_conv : float
        Convergence threshold
    
    Returns:
    --------
    P : numpy.ndarray
        Permutation matrix representing the matching
    score : float
        Final matching score
    """
    n = A.shape[0]
    if sparse.issparse(A):
        A = A.toarray()
    if sparse.issparse(B):
        B = B.toarray()
    
    # Initialize with uniform distribution
    M = np.ones((n, n)) / n
    beta = beta_0
    
    def compute_Q():
        # Compute compatibility matrix
        return A @ M @ B.T + A.T @ M @ B
    
    def softmax(X, beta):
        # Sinkhorn normalization with temperature
        exp_X = np.array(np.exp(beta * X))
        for _ in range(20):  # Max iterations for Sinkhorn
            # Row normalization
            row_sums = np.sum(exp_X, axis=1, keepdims=True)
            exp_X = exp_X / row_sums
            # Column normalization
            col_sums = np.sum(exp_X, axis=0, keepdims=True)
            exp_X = exp_X / col_sums
        return exp_X
    
    best_score = -np.inf
    best_M = None
    
    # Main loop - graduated assignment
    while beta < beta_f:
        for _ in range(max_iter):
            old_M = M.copy()
            
            # Compute compatibility matrix
            Q = compute_Q()
            
            # Update M using Softmax + Sinkhorn
            M = softmax(Q, beta)
            
            # Check convergence
            diff = np.linalg.norm(M - old_M) / (n * n)
            if diff < e_conv:
                break
        
        # Calculate current score
        current_score = np.sum(np.minimum(A @ M @ B.T, A.T @ M @ B))
        if current_score > best_score:
            best_score = current_score
            best_M = M.copy()
        
        # Increase beta
        beta *= beta_r
    
    # Convert soft assignment to hard assignment using Hungarian algorithm
    row_ind, col_ind = linear_sum_assignment(-best_M)
    
    # Create final permutation matrix
    P = np.zeros_like(best_M)
    P[row_ind, col_ind] = 1
    
    return P, best_score

# Test the implementation
def generate_test_graphs(n=100, density=0.1):
    """Generate random test graphs with some structural similarity."""
    # Base adjacency matrix
    A = sparse.random(n, n, density=density, format='csr')
    A = (A + A.T) / 2  # Make symmetric
    A.data[:] = np.random.rand(len(A.data))
    
    # Create B as a perturbed version of A
    P = np.eye(n)  # Start with identity permutation
    # Add some random permutations
    for _ in range(n // 10):
        i, j = np.random.choice(n, 2, replace=False)
        P[[i, j]] = P[[j, i]]
    
    noise = sparse.random(n, n, density=density/2, format='csr')
    noise = (noise + noise.T) / 2
    B = P.T @ A @ P + noise
    
    return A, B, P

if __name__ == "__main__":
    # Generate test graphs
    n = 900
    A, B, true_P = generate_test_graphs(n, density=0.15)
    
    # Run graduated assignment
    estimated_P, score = graduated_assignment(A, B)
    
    # Calculate accuracy
    accuracy = np.sum(estimated_P * true_P) / n
    print(f"Matching accuracy: {accuracy:.3f}")
    print(f"Final score: {score:.3f}")