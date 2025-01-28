import warnings
import numpy as np
from scipy import sparse
from scipy.optimize import linear_sum_assignment

warnings.filterwarnings('ignore')  # Suppress warnings from numpy operations

def project_doubly_stochastic(X, max_iter=1000, epsilon=1e-10):
    """Project matrix onto doubly stochastic matrices using Sinkhorn-Knopp."""
    Y = np.asarray(X.copy())
    for _ in range(max_iter):
        prev_Y = Y.copy()
        # Row normalization
        row_sums = Y.sum(axis=1, keepdims=True)
        Y = Y / np.maximum(row_sums, epsilon)
        # Column normalization
        col_sums = Y.sum(axis=0, keepdims=True)
        Y = Y / np.maximum(col_sums, epsilon)
        
        # Check convergence
        if np.max(np.abs(Y - prev_Y)) < epsilon:
            break
    
    return Y
    
def compute_score(X):
    """Compute the matching score."""
    return np.sum(np.minimum(A @ X @ B.T, A.T @ X @ B))

def gnccp_matching(A, B, zeta_0=0.1, zeta_f=1e-10, alpha=0.9, max_iter=100, 
                  inner_iter=30, e_conv=1e-6, initial_X=None, verbose=True):
    """
    GNCCP algorithm for graph matching with warm start capability.
    
    Parameters:
    -----------
    A, B : scipy.sparse.csr_matrix or numpy.ndarray
        Adjacency matrices of the graphs to be matched
    zeta_0 : float
        Initial concavity parameter
    zeta_f : float
        Final concavity parameter
    alpha : float
        Reduction factor for zeta
    max_iter : int
        Maximum number of outer iterations
    inner_iter : int
        Maximum number of inner iterations per concavity level
    e_conv : float
        Convergence threshold
    initial_X : numpy.ndarray, optional
        Initial permutation matrix for warm start
        
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
    
    # Initialize X (doubly stochastic matrix)
    if initial_X is not None:
        X = initial_X.copy()
    else:
        X = np.ones((n, n)) / n
    
    # Initialize momentum terms
    momentum = np.zeros_like(X)
    momentum_beta = 0.9

    # Precompute constant terms
    AB = A @ B.T
    BA = B @ A.T
    
    def compute_gradient(X, zeta):
        """Compute gradient of the objective function."""
        grad = 2 * (A @ X @ B.T + A.T @ X @ B)
        # Add concave term
        grad -= 2 * zeta * X
        return grad
    
    best_score = -np.inf
    best_X = None
    zeta = zeta_0

    # Adaptive step size parameters
    step_size = 1.0
    step_increase = 1.1
    step_decrease = 0.5
    min_improvement = 1e-4
    
     # Main GNCCP loop
    outer_iter = 0
    while zeta > zeta_f:
        if verbose:
            print(f"\nOuter iteration {outer_iter}, zeta = {zeta:.8f}")
        
        # Path following
        inner_iter_count = 0
        prev_score = compute_score(X)
        
        for i in range(max_iter):
            old_X = X.copy()
            
            # Compute gradient
            grad = compute_gradient(X, zeta)
            
            # Apply momentum and gradient step
            momentum = momentum_beta * momentum + (1 - momentum_beta) * grad
            
            # Try step
            success = False
            local_step = step_size
            max_attempts = 5
            
            for _ in range(max_attempts):
                new_X = X + local_step * momentum
                new_X = project_doubly_stochastic(new_X)
                
                if np.all(np.isfinite(new_X)):
                    new_score = compute_score(new_X)
                    improvement = new_score - prev_score
                    
                    if improvement > -min_improvement:  # Allow small decreases
                        X = new_X
                        success = True
                        
                        # Adapt step size
                        if improvement > min_improvement:
                            step_size = min(step_size * step_increase, 1.0)
                        
                        prev_score = new_score
                        break
                
                local_step *= step_decrease
            
            if not success:
                step_size *= step_decrease
                if verbose:
                    print(f"  Step size reduced to {step_size:.8f}")
                if step_size < 1e-10:
                    break
            
            # Calculate change
            change = np.linalg.norm(X - old_X)
            
            if verbose and i % 5 == 0:
                print(f"  Inner iter {i}: change = {change:.8f}, "
                      f"score = {prev_score:.2f}, "
                      f"step_size = {step_size:.8f}")
            
            inner_iter_count += 1
            
            # Check convergence
            if change < e_conv and i > 5:  # Ensure minimum iterations
                if verbose:
                    print(f"  Converged after {inner_iter_count} iterations")
                break
        
        # Update best solution
        current_score = compute_score(X)
        if current_score > best_score:
            best_score = current_score
            best_X = X.copy()
            if verbose:
                print(f"  New best score: {best_score:.2f}")
        
        # Update zeta
        zeta *= alpha
        outer_iter += 1
    
    # Final discretization
    row_ind, col_ind = linear_sum_assignment(-best_X)
    P = np.zeros_like(best_X)
    P[row_ind, col_ind] = 1
    
    final_score = compute_score(P)
    return P, final_score

def create_warm_start(A, B, method='degree'):
    """
    Create initial matching based on simple heuristics.
    
    Parameters:
    -----------
    A, B : scipy.sparse.csr_matrix or numpy.ndarray
        Adjacency matrices of the graphs to be matched
    method : str
        Method to use for creating initial matching ('degree' or 'eigenvector')
        
    Returns:
    --------
    X : numpy.ndarray
        Initial doubly stochastic matrix
    """
    n = A.shape[0]
    if method == 'degree':
        # Match based on degree similarity
        degrees_A = np.sum(A, axis=0)
        degrees_B = np.sum(B, axis=0)
        
        # Create similarity matrix based on degree differences
        sim_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                sim_matrix[i,j] = -abs(degrees_A[0,i] - degrees_B[0,i])
        
        # Use Hungarian algorithm to find initial matching
        row_ind, col_ind = linear_sum_assignment(sim_matrix)
        X = np.zeros((n, n))
        X[row_ind, col_ind] = 1
        
    elif method == 'eigenvector':
        print(A.toarray())
        print(repr(B))
        # Match based on leading eigenvector similarity
        eig_A = np.linalg.eigh(A.toarray())[1][:, -1]
        eig_B = np.linalg.eigh(B)[1][:, -1]
        
        # Create similarity matrix based on eigenvector components
        sim_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                sim_matrix[i,j] = -abs(abs(eig_A[i]) - abs(eig_B[j]))
        
        # Use Hungarian algorithm to find initial matching
        row_ind, col_ind = linear_sum_assignment(sim_matrix)
        X = np.zeros((n, n))
        X[row_ind, col_ind] = 1
    
    # Add some noise and project to doubly stochastic
    X = X + np.random.rand(n, n) * 0.1
    X = X / np.sum(X)
    X = project_doubly_stochastic(X)
    return X

if __name__ == "__main__":
    # Test the implementation
    from graduated_assignment_2 import generate_test_graphs
    
    # Generate test graphs
    n = 200
    A, B, true_P = generate_test_graphs(n, density=0.15)
    
    # Create warm start
    # initial_X = create_warm_start(A, B, method='eigenvector')
    initial_X = np.ones((n, n)) / n

    row_ind, col_ind = linear_sum_assignment(-initial_X)
    P = np.zeros_like(initial_X)
    P[row_ind, col_ind] = 1
    
    initial_score = compute_score(P)
    
    # Run GNCCP with warm start
    estimated_P, score = gnccp_matching(A, B, initial_X=initial_X)
    
    # Calculate accuracy
    accuracy = np.sum(estimated_P * true_P) / n
    print(f"Matching accuracy with warm start: {accuracy:.3f}")
    print(f"Initial score: {initial_score:.3f}")
    print(f"Final score: {score:.3f}")
    
    # Compare with cold start
    # estimated_P_cold, score_cold = gnccp_matching(A, B)
    # accuracy_cold = np.sum(estimated_P_cold * true_P) / n
    # print(f"\nMatching accuracy without warm start: {accuracy_cold:.3f}")
    # print(f"Final score: {score_cold:.3f}")