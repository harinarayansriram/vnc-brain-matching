#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <lemon/list_graph.h>
#include <lemon/hungarian.h>

#define MAX_NODES 20000

// Sparse adjacency matrix structure
typedef struct {
    int n;            // Number of nodes
    int nnz;          // Number of non-zero elements
    int *row_ptr;     // Row pointers (size n+1)
    int *col_idx;     // Column indices (size nnz)
    double *values;   // Non-zero values (size nnz)
} SparseMatrix;

// Function prototypes
SparseMatrix* create_sparse_matrix(int n, int nnz);
void free_sparse_matrix(SparseMatrix *matrix);
SparseMatrix* load_adjacency_matrix(const char *filename, int *node_count);
void project_to_permutation(const SparseMatrix *P, int *permutation);

// Main function
int main(int argc, char **argv) {
    if (argc < 2) {
        printf("Usage: %s <graph_file>\n", argv[0]);
        return -1;
    }

    int node_count;
    SparseMatrix *P = load_adjacency_matrix(argv[1], &node_count);

    int *permutation = (int *)malloc(node_count * sizeof(int));
    if (!permutation) {
        perror("Failed to allocate permutation array");
        free_sparse_matrix(P);
        return -1;
    }

    project_to_permutation(P, permutation);

    // Print the resulting permutation
    printf("Optimal permutation:\n");
    for (int i = 0; i < node_count; i++) {
        printf("%d -> %d\n", i, permutation[i]);
    }

    free(permutation);
    free_sparse_matrix(P);
    return 0;
}

// Create a sparse matrix structure
SparseMatrix* create_sparse_matrix(int n, int nnz) {
    SparseMatrix *matrix = (SparseMatrix *)malloc(sizeof(SparseMatrix));
    matrix->n = n;
    matrix->nnz = nnz;
    matrix->row_ptr = (int *)malloc((n + 1) * sizeof(int));
    matrix->col_idx = (int *)malloc(nnz * sizeof(int));
    matrix->values = (double *)malloc(nnz * sizeof(double));
    return matrix;
}

// Free a sparse matrix
void free_sparse_matrix(SparseMatrix *matrix) {
    if (matrix) {
        free(matrix->row_ptr);
        free(matrix->col_idx);
        free(matrix->values);
        free(matrix);
    }
}

// Load adjacency matrix from a file
SparseMatrix* load_adjacency_matrix(const char *filename, int *node_count) {
    FILE *file = fopen(filename, "r");
    if (!file) {
        perror("Failed to open file");
        return NULL;
    }

    int from, to, nnz = 0, max_node = 0;
    double weight;

    // Count edges and find the maximum node index
    while (fscanf(file, "%d %d %lf", &from, &to, &weight) != EOF) {
        nnz++;
        if (from > max_node) max_node = from;
        if (to > max_node) max_node = to;
    }
    *node_count = max_node + 1;

    // Allocate sparse matrix
    SparseMatrix *matrix = create_sparse_matrix(*node_count, nnz);

    rewind(file);

    // Fill the sparse matrix
    int current_row = 0, row_idx = 0, edge_idx = 0;
    matrix->row_ptr[0] = 0;
    while (fscanf(file, "%d %d %lf", &from, &to, &weight) != EOF) {
        while (current_row < from) {
            matrix->row_ptr[++current_row] = edge_idx;
        }
        matrix->col_idx[edge_idx] = to;
        matrix->values[edge_idx++] = weight;
    }
    matrix->row_ptr[current_row + 1] = edge_idx;

    fclose(file);
    return matrix;
}

// Project doubly stochastic matrix P to a permutation matrix
void project_to_permutation(const SparseMatrix *P, int *permutation) {
    using namespace lemon;

    // Create Lemon graph
    ListGraph g;
    ListGraph::NodeMap<int> supply(g);  // Row nodes supply
    ListGraph::NodeMap<int> demand(g); // Column nodes demand
    ListGraph::EdgeMap<double> cost(g);

    int n = P->n;

    // Create nodes for rows and columns
    ListGraph::Node row_nodes[MAX_NODES];
    ListGraph::Node col_nodes[MAX_NODES];
    for (int i = 0; i < n; i++) {
        row_nodes[i] = g.addNode();
        col_nodes[i] = g.addNode();
        supply[row_nodes[i]] = 1;   // Each row has 1 unit of supply
        demand[col_nodes[i]] = -1; // Each column has 1 unit of demand
    }

    // Add edges between row and column nodes with weights from P
    for (int i = 0; i < n; i++) {
        for (int j = P->row_ptr[i]; j < P->row_ptr[i + 1]; j++) {
            ListGraph::Edge e = g.addEdge(row_nodes[i], col_nodes[P->col_idx[j]]);
            cost[e] = -P->values[j]; // Negate weights to maximize
        }
    }

    // Solve the assignment problem
    ListGraph::EdgeMap<int> flow(g);
    bool success = hungarian(g, supply, demand, cost, flow);
    if (!success) {
        fprintf(stderr, "Hungarian algorithm failed.\n");
        return;
    }

    // Extract the permutation
    for (ListGraph::NodeIt r(g); r != INVALID; ++r) {
        if (g.id(r) < n) {
            for (ListGraph::IncEdgeIt e(g, r); e != INVALID; ++e) {
                if (flow[e] > 0) {
                    permutation[g.id(r)] = g.id(g.oppositeNode(r, e)) - n;
                }
            }
        }
    }
}
