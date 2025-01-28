# graph_matching.py
# Python implementation of convex relaxation for graph matching

import numpy as np
from scipy.optimize import linear_sum_assignment
# from scipy.sparse import coo_matrix
# import osqp
# import cvxpy as cp
# from gurobipy import Model, GRB, quicksum
import gurobipy as gp
import csv


# Function to build adjacency matrix from graph
# Graph is a list of tuples (from_node, to_node, weight)
def build_adjacency_matrix(graph, num_nodes):
    adjacency = np.zeros((num_nodes, num_nodes), dtype=np.int32)
    for from_node, to_node, weight in graph:
        adjacency[from_node, to_node] = weight
    return adjacency

# Solve relaxed quadratic program using OSQP
'''
def solve_relaxed_qp(A, B, initial_guess=None, max_iter=1000):
    n = A.shape[0]

    # Quadratic cost matrix (Q)
    # Q = 2 * (np.kron(np.eye(n), A.T @ A) + np.kron(B.T @ B, np.eye(n)))
    # Define a linear operator for efficient QP setup
    def matvec(v):
        V = v.reshape(n, n)  # Reshape to n x n
        result = 2 * (A.T @ (A @ V) + (V @ B.T) @ B)  # Efficiently compute Q*v
        return result.flatten()

    # Linear term (c)
    c = -2 * (B @ A.T).flatten()

    # Incorporate initial guess into the linear term
    if initial_guess is not None:
        c += -2 * initial_guess.flatten()

    # Constraints for doubly stochastic matrix
    row_constraints = np.kron(np.eye(n), np.ones(n))
    col_constraints = np.kron(np.ones(n), np.eye(n))
    A_constraints = np.vstack([row_constraints, col_constraints])
    l_constraints = np.ones(2 * n)
    u_constraints = np.ones(2 * n)

    # OSQP setup
    qp = osqp.OSQP()
    # Create a sparse matrix for the linear operator
    P_linear_operator = coo_matrix((n * n, n * n), dtype=np.float64)
    P_linear_operator.matvec = matvec  # Attach efficient matvec

    qp.setup(P=P_linear_operator, q=c, A=coo_matrix(A_constraints), l=l_constraints, u=u_constraints, verbose=False)

    # qp.setup(P=coo_matrix(Q), q=c, A=coo_matrix(A_constraints), l=l_constraints, u=u_constraints, verbose=True)
    
    # Modify OSQP settings for early stopping
    # qp.warm_start()
    qp.update_settings(max_iter=max_iter)
    
    # Solve QP
    result = qp.solve()
    # Check if the solver stopped early
    if result.info.status != 'solved' and result.info.iter <= max_iter:
        print(f"Solver stopped early after {result.info.iter} iterations.")

    # Reshape solution to n x n matrix
    P = result.x.reshape(n, n)
    return P
'''

# def solve_relaxed_qp(A, B, initial_guess=None, max_iter=1000):
#     n = A.shape[0]

#     # Quadratic cost matrix (Q)
#     I_n = np.eye(n)
#     Q = 2 * (np.kron(I_n, A.T @ A) + np.kron(B.T @ B, I_n))

#     # Linear term (c)
#     c = -2 * (B @ A.T).flatten()

#     # Incorporate initial guess into the linear term
#     if initial_guess is not None:
#         c += -2 * initial_guess.flatten()

#     # Constraints for doubly stochastic matrix
#     row_constraints = np.kron(I_n, np.ones(n))
#     col_constraints = np.kron(np.ones(n), I_n)
#     A_constraints = np.vstack([row_constraints, col_constraints])

#     # Sparse representation
#     A_constraints = coo_matrix(A_constraints)
#     Q = coo_matrix(Q)

#     l_constraints = np.ones(2 * n)
#     u_constraints = np.ones(2 * n)

#     # OSQP setup
#     qp = osqp.OSQP()
#     qp.setup(P=Q, q=c, A=A_constraints, l=l_constraints, u=u_constraints, verbose=True)

#     # Modify OSQP settings for early stopping
#     # qp.warm_start()
#     qp.update_settings(max_iter=max_iter)

#     # Solve QP
#     result = qp.solve()
#     if result.info.status != 'solved':
#         raise ValueError(f"QP solver failed: {result.info.status}")

#     # Reshape solution to n x n matrix
#     P = result.x.reshape(n, n)
#     return P

# def solve_relaxed_qp(A, B, initial_guess=None, max_iter=1000):
#     n = A.shape[0]

#     # Linear term (c)
#     c = -2 * (B @ A.T).flatten()

#     # Constraints for doubly stochastic matrix
#     row_constraints = np.kron(np.eye(n), np.ones(n))
#     col_constraints = np.kron(np.ones(n), np.eye(n))
#     A_constraints = np.vstack([row_constraints, col_constraints])
#     l_constraints = np.ones(2 * n)
#     u_constraints = np.ones(2 * n)

#     # Approximate P as diagonal for simplicity
#     # Equivalent to 2 * (kron(I, A^T A) + kron(B^T B, I)) but only diagonal values
#     diag_entries = []
#     for i in range(n):
#         for j in range(n):
#             diag_entries.append(2 * (np.dot(A[:, i], A[:, j]) + np.dot(B[i, :], B[j, :])))

#     # Create a sparse diagonal matrix
#     P_sparse = coo_matrix((diag_entries, (np.arange(n * n), np.arange(n * n))), shape=(n * n, n * n))

#     # OSQP setup
#     qp = osqp.OSQP()
#     qp.setup(P=P_sparse, q=c, A=coo_matrix(A_constraints), l=l_constraints, u=u_constraints, verbose=True)

#     # Solve QP
#     result = qp.solve()
#     if result.info.status != 'solved':
#         raise ValueError(f"QP solver failed: {result.info.status}")

#     # Reshape solution to n x n matrix
#     P = result.x.reshape(n, n)
#     return P

'''
def solve_relaxed_qp(A, B, initial_guess=None, max_iter=1000):
    n = A.shape[0]

    # Define optimization variable P and auxiliary variable M
    P = cp.Variable((n, n), nonneg=True)
    M = cp.Variable((n, n))

    # Objective: Minimize ||PA - BP||_F^2 using an auxiliary variable
    term1 = cp.sum_squares(M @ A)  # ||PA||_F^2
    term2 = cp.sum_squares(B @ M)  # ||BP||_F^2
    objective = cp.Minimize(term1 + term2)

    # Constraints for doubly stochastic matrices
    constraints = [
        cp.sum(P, axis=0) == 1,  # Row sums equal 1
        cp.sum(P, axis=1) == 1,  # Column sums equal 1
        M == P,                  # Auxiliary variable to maintain equality
    ]

    # Define and solve the problem
    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.OSQP, verbose=True)

    # Check if the solver succeeded
    if problem.status not in ["optimal", "optimal_inaccurate"]:
        raise ValueError(f"CVXPY solver failed: {problem.status}")

    # Return the solution
    return P.value
'''


def solve_relaxed_qp(A, B, initial_guess=None, max_iter=1000):
    n = A.shape[0]

    # Create a new Gurobi model
    model = gp.Model("graph_matching")

    # Add variables for the doubly stochastic matrix PF
    P = model.addVars(n, n, lb=0, ub=1, name="P")

    # Objective function components
    # Frobenius norm terms ||PA||_F^2 + ||BP||_F^2
    term1 = gp.quicksum(P[i, j] * A[j, k] * P[i, k] for i in range(n) for j in range(n) for k in range(n))
    term2 = gp.quicksum(P[i, j] * B[k, i] * P[k, j] for i in range(n) for j in range(n) for k in range(n))
    cross_term = gp.quicksum(P[i, j] * A[j, k] * B[k, i] * P[k, j] for i in range(n) for j in range(n) for k in range(n))

    # Objective: Minimize ||PA - BP||_F^2
    model.setObjective(term1 + term2 - 2 * cross_term, gp.GRB.MINIMIZE)

    # Add row and column sum constraints (doubly stochastic)
    for i in range(n):
        model.addConstr(gp.quicksum(P[i, j] for j in range(n)) == 1, name=f"row_sum_{i}")
    for j in range(n):
        model.addConstr(gp.quicksum(P[i, j] for i in range(n)) == 1, name=f"col_sum_{j}")

    # Solve the model
    model.optimize()

    # Check if the solver succeeded
    if model.status != gp.GRB.OPTIMAL:
        raise ValueError(f"Gurobi solver failed with status {model.status}")

    # Extract the solution
    P_matrix = np.zeros((n, n), dtype=np.int32)
    for i in range(n):
        for j in range(n):
            P_matrix[i, j] = P[i, j].X

    return P_matrix

def graph_matching(graphA, graphB, num_nodes):
    # Build adjacency matrices
    A = build_adjacency_matrix(graphA, num_nodes)
    B = build_adjacency_matrix(graphB, num_nodes)

    # Solve relaxed QP
    P = solve_relaxed_qp(A, B)

    if P is None:
        print("QP solver failed to produce a solution. Exiting...")
        return None, None

    # Project to permutation matrix
    permutation = project_to_permutation(P)

    return P, permutation

# Project relaxed solution to permutation matrix using Hungarian Algorithm
def project_to_permutation(P):
    row_ind, col_ind = linear_sum_assignment(-P)  # Maximization -> Minimization
    permutation = np.zeros_like(P, dtype=np.int32)
    permutation[row_ind, col_ind] = 1
    return permutation

# Convert permutation matrix to mapping (list of assignments)
def permutation_to_mapping(permutation):
    return list(map(int,np.argmax(permutation, axis=1)))

# Convert mapping (list of assignments) to permutation matrix
def mapping_to_permutation(mapping, num_nodes):
    permutation = np.zeros((num_nodes, num_nodes), dtype=np.int32)
    for i, j in enumerate(mapping):
        permutation[i, j] = 1
    return permutation

# Main function for graph matching
def graph_matching(graphA, graphB, num_nodes, initial_guess=None, max_iter=1000):
    # Build adjacency matrices
    A = build_adjacency_matrix(graphA, num_nodes)
    B = build_adjacency_matrix(graphB, num_nodes)

    # Solve relaxed QP with warm start
    P = solve_relaxed_qp(A, B, initial_guess, max_iter=max_iter)

    # Project to permutation matrix
    permutation = project_to_permutation(P)

    return P, permutation

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


if __name__ == "__main__":
    # Non-trivial example graphs
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

    # 0 --> 0, 1 --> 2, 2 --> 3, 3 --> 

    num_nodes = 4

    # Perform graph matching
    P, permutation = graph_matching(graphA, graphB, num_nodes)

    # Output results
    print("Relaxed Solution (P):\n", P)
    print("Permutation Matrix:\n", permutation)
    print("Mapping: ", permutation_to_mapping(permutation))

# if __name__ == "__main__":
#     graphA = [(0, 1, 1.0), (1, 2, 2.0), (2, 0, 3.0)]
#     graphB = [(0, 1, 1.0), (1, 2, 2.0), (2, 0, 3.0)]

#     num_nodes = 3

#     # Approximate solution as a warm start
#     initial_guess = np.array([[1, 0, 0],
#                               [0, 0, 1],
#                               [0, 1, 0]])

#     # Perform graph matching with warm start
#     P, permutation = graph_matching(graphA, graphB, num_nodes, initial_guess)

#     # Output results
#     print("Relaxed Solution (P):\n", P)
#     print("Permutation Matrix:\n", permutation)
#     print("Mapping: ", permutation_to_mapping(permutation))

# if __name__ == "__main__":
#     # graphA = [[0, 5, 4], [0, 6, 7], [0, 8, 6], [0, 9, 6], [1, 4, 9], [1, 7, 5], [2, 0, 3], [2, 3, 2], [2, 5, 6], [2, 7, 5], [3, 0, 7], [3, 2, 7], [4, 2, 1], [4, 5, 2], [4, 6, 8], [5, 3, 7], [5, 4, 6], [5, 7, 5], [6, 4, 8], [6, 5, 2], [6, 7, 6], [6, 9, 1], [7, 4, 4], [8, 2, 1], [8, 6, 8], [8, 7, 8], [9, 3, 6], [9, 6, 9]]
#     # graphB = [[0, 3, 7], [0, 4, 6], [0, 7, 5], [1, 4, 8], [1, 5, 2], [1, 7, 6], [1, 9, 1], [2, 2, 1], [2, 5, 2], [2, 6, 8], [3, 3, 6], [3, 6, 9], [4, 2, 1], [4, 6, 8], [4, 7, 8], [5, 4, 9], [5, 7, 5], [6, 0, 7], [6, 2, 7], [7, 5, 4], [7, 6, 7], [7, 8, 6], [7, 9, 6], [8, 4, 4], [9, 0, 3], [9, 3, 2], [9, 5, 6], [9, 7, 5]]
#     graphA, graphB, answer = create_test_graph()
#     A_adj, B_adj = build_adjacency_matrix(graphA, 10), build_adjacency_matrix(graphB, 10)
#     num_nodes = 10

#     P, permutation = graph_matching(graphA, graphB, num_nodes)

#     print("Relaxed Solution (P):\n", P)
#     print("Permutation Matrix:\n", permutation)
#     mapping = permutation_to_mapping(permutation)
#     print("Mapping: ", mapping, "  Score of: ", score_mapping(mapping, A_adj, B_adj))
#     print("Answer: ", answer, "  Score of: ", score_mapping(answer, A_adj, B_adj))


# if __name__ == "__main__":
#     graphA = read_csv_to_tuples("../gm.csv")
#     graphB = read_csv_to_tuples("../gf.csv")

#     print("Read graphs")

#     num_nodes = 18524

#     P, permutation = graph_matching(graphA, graphB, num_nodes, max_iter=10_000)

#     print("Finished matching")

#     mapping = permutation_to_mapping(permutation)

#     save_mapping(mapping, 'convex-finetune.csv')

#     print("Saved")