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

def graph_matching_relaxed(A, B):
    n = A.shape[0]
    # P = cp.Variable((n, n), nonneg=True)

    k = 50  # Rank
    U = cp.Variable((n, k))
    V = cp.Variable((n, k))
    P = U @ V.T
    #constraints = [
    #    P @ np.ones(n) == np.ones(n),
    #    P.T @ np.ones(n) == np.ones(n),
    #    P >= 0
    #]
    objective = cp.Minimize(cp.norm(P @ A - B @ P, "fro") ** 2)
    #prob = cp.Problem(objective, constraints)
    #prob.solve(solver=cp.SCS, verbose=True)


    # Constraint relaxation
    #objective = cp.Minimize(cp.norm(P @ A - B @ P, "fro") ** 2 +
     #                       cp.norm(P @ np.ones(n) - np.ones(n), 2) ** 2 +
     #                       cp.norm(P.T @ np.ones(n) - np.ones(n), 2) ** 2)

    # Sample a subset of constraints
    indices = np.random.choice(n, size=5000, replace=False)
    constraints = [
        P[indices, :] @ np.ones(n) == np.ones(len(indices)),
        P[:, indices].T @ np.ones(n) == np.ones(len(indices)),
        P >= 0
    ]

    prob = cp.Problem(objective, constraints)
    prob.solve(solver=cp.SCS, verbose=True)

    return P.value

def alternating_optimization(A, B, rank=50, max_iter=10):
    n = A.shape[0]
    U = np.random.rand(n, rank)
    V = np.random.rand(n, rank)

    for _ in range(max_iter):
        # Solve for V while fixing U
        V_var = cp.Variable((n, rank))
        objective = cp.Minimize(cp.norm(U @ V_var.T @ A - B @ (U @ V_var.T), "fro") ** 2)
        prob = cp.Problem(objective)
        prob.solve(solver=cp.SCS, verbose=True, sparse=True)
        V = V_var.value

        # Solve for U while fixing V
        U_var = cp.Variable((n, rank))
        objective = cp.Minimize(cp.norm(U_var @ V.T @ A - B @ (U_var @ V.T), "fro") ** 2)
        prob = cp.Problem(objective)
        prob.solve(solver=cp.SCS, verbose=True, sparse=True)
        U = U_var.value


    # Reconstruct P
    # Relaxed solution
    P_relaxed = U @ V.T
    # Step 2: Project to Permutation Matrix
    row_ind, col_ind = linear_sum_assignment(-P_relaxed)
    P_final = np.zeros_like(P_relaxed)
    P_final[row_ind, col_ind] = 1

    return P_final


# Example Usage
if __name__ == "__main__":
    # graphA = [
    #     (0, 1, 1.0),
    #     (0, 2, 2.0),
    #     (1, 3, 3.0),
    #     (2, 3, 1.5)
    # ]
    # graphB = [
    #     (0, 2, 1.1),
    #     (0, 3, 2.1),
    #     (1, 0, 3.1),
    #     (2, 1, 1.4)
    # ]
    graphA = read_csv_to_tuples("gm.csv")
    graphB = read_csv_to_tuples("gf.csv")

    print("Read graphs")

    num_nodes = 18524

    # Example adjacency matrices
    # A = np.array([
    #     [0, 1, 0],
    #     [1, 0, 1],
    #     [0, 1, 0]
    # ])
    A = csr_matrix(build_adjacency_matrix(graphA, num_nodes))
    B = csr_matrix(build_adjacency_matrix(graphB, num_nodes))   
    # B = np.array([
    #     [0, 1, 1],
    #     [1, 0, 0],
    #     [1, 0, 0]
    # ])

    P = alternating_optimization(A, B)
    print("Finished matching")
    mapping = permutation_to_mapping(P)
    # print("Permutation Matrix:\n", P)
    print("Mapping: ", mapping)
    save_mapping(mapping, 'convex-finetune.csv')
    print("Saved")