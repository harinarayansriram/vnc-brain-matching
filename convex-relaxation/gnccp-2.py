import numpy as np
import scipy.sparse as sp
import scipy.optimize
import numba

def load_graph(filename, num_nodes):
    edges = np.loadtxt(filename, delimiter=',', skiprows=1, dtype=int)
    adj = sp.lil_matrix((num_nodes, num_nodes), dtype=np.float64)
    for u, v, w in edges:
        adj[u-1, v-1] = w
    return adj.tocsr()

def load_mapping(filename, num_nodes):
    mapping = np.loadtxt(filename, delimiter=',', skiprows=1, dtype=str)
    map_dict = {int(m[0][1:]) - 1: int(m[1][1:]) - 1 for m in mapping}
    P0 = np.zeros((num_nodes, num_nodes))
    for i, j in map_dict.items():
        P0[i, j] = 1
    return P0

@numba.njit
def project_onto_permutation(P):
    row_ind, col_ind = scipy.optimize.linear_sum_assignment(-P)
    P_perm = np.zeros_like(P)
    P_perm[row_ind, col_ind] = 1
    return P_perm

def gnccp(A, B, P0=None, max_iter=50, tol=1e-4):
    num_nodes = A.shape[0]
    P = P0 if P0 is not None else np.ones((num_nodes, num_nodes)) / num_nodes
    for _ in range(max_iter):
        grad = A @ P @ B.T
        P_new = project_onto_permutation(grad)
        if np.linalg.norm(P_new - P, 'fro') < tol:
            break
        P = P_new
    return P

def compute_alignment_score(A, B, P):
    alignment = 0
    mapping = np.argmax(P, axis=1)  # Compute mapping once
    num_nonzero = A.nnz
    count = 0
    for i, j in zip(*A.nonzero()):  # Iterate over nonzero edges in A
        count += 1
        mapped_i, mapped_j = mapping[i], mapping[j]
        alignment += min(A[i, j], B[mapped_i, mapped_j])
        if count % 1000 == 0:
            print(f"Processed {count}/{num_nonzero} edges")
    return alignment

# def compute_alignment_score(A_data, A_indices, A_indptr, B_data, B_indices, B_indptr, mapping):
#     alignment = 0
#     outer_loop_num = A_indptr.shape[0] - 1
#     outer_loop_cnt = 0
#     for i in range(A_indptr.shape[0] - 1):
#         outer_loop_cnt += 1
#         if outer_loop_cnt % 1000 == 0:
#             print(f"Processed {outer_loop_cnt}/{outer_loop_num} edges")
#         for idx in range(A_indptr[i], A_indptr[i + 1]):
#             j = A_indices[idx]
#             mapped_i, mapped_j = mapping[i], mapping[j]
#             B_idx = np.searchsorted(B_indices[B_indptr[mapped_i]:B_indptr[mapped_i + 1]], mapped_j)
#             if B_idx < (B_indptr[mapped_i + 1] - B_indptr[mapped_i]) and B_indices[B_indptr[mapped_i] + B_idx] == mapped_j:
#                 alignment += min(A_data[idx], B_data[B_indptr[mapped_i] + B_idx])
#     return alignment


if __name__ == "__main__":
    num_nodes = 18524
    A = load_graph("../gm.csv", num_nodes)
    print("Finshed gm")
    B = load_graph("../gf.csv", num_nodes)
    print("Finshed gf")
    P0 = load_mapping("../score_lookup/5849425.csv", num_nodes)
    print("Finshed mapping")
    # P_opt = gnccp(A, B, P0)
    
    # np.savetxt("optimized_mapping.csv", np.column_stack((np.arange(1, num_nodes+1), np.argmax(P_opt, axis=1) + 1)), delimiter=',', fmt='%d')
    
    alignment_score = compute_alignment_score(A, B, P0)
    # alignment_score = compute_alignment_score(A.data, A.indices, A.indptr, B.data, B.indices, B.indptr, P0)
    print(f"Alignment Score: {alignment_score}")
