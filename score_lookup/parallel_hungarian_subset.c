#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdbool.h>
#include <time.h>
#include <omp.h>
#include "utils.h"
#include "parallel_hungarian.h"
#include "parallel_hungarian_subset.h"
#include "interrupts.h"

#define CURRENT_LOG_LEVEL LOG_LEVEL_INFO

void validate_mapping_changes(int* old_mapping, int* new_mapping, int max_node,
                            int node_m1, int node_m2) {
    for (int i = 1; i <= max_node; i++) {
        if (i != node_m1 && i != node_m2) {
            if (old_mapping[i] != new_mapping[i]) {
                LOG_ERROR("Unexpected mapping change for node %d: %d -> %d",
                         i, old_mapping[i], new_mapping[i]);
            }
        }
    }
}

int one_side_swap_delta(Graph* gm, Graph* gf, int* mapping, int node_m1, int node_m2) {
    int node_f1 = mapping[node_m1];
    int node_f2 = mapping[node_m2];
    int delta = 0;

    if (node_m1 == node_m2) {
        return 0;
    }

    // Handle outgoing edges from node_m1
    for (int i = 0; i < gm->edges[node_m1].count; i++) {
        int dst_m = gm->edges[node_m1].to_nodes[i];
        if (dst_m == node_m2 || dst_m == node_m1) {
            continue;  // Skip direct edge between swapped nodes
        }
        int weight_m = gm->edges[node_m1].weights[i];
        int dst_f = mapping[dst_m];

        // Remove old contribution
        int old_weight = MIN(weight_m, gf->adj_matrix[node_f1*NUM_NODES + dst_f]);
        delta -= old_weight;

        // Add new potential contribution
        int new_weight = MIN(weight_m, gf->adj_matrix[node_f2*NUM_NODES + dst_f]);
        delta += new_weight;
    }

    // Handle incoming edges to node_m1
    for (int i = 0; i < gm->reverse_edges[node_m1].count; i++) {
        int src_m = gm->reverse_edges[node_m1].to_nodes[i];
        if (src_m == node_m2 || src_m == node_m1) {
            continue;  // Skip direct edge between swapped nodes
        }
        int weight_m = gm->reverse_edges[node_m1].weights[i];
        int src_f = mapping[src_m];

        // Remove old contribution
        int old_weight = MIN(weight_m, gf->adj_matrix[src_f*NUM_NODES + node_f1]);
        delta -= old_weight;

        // Add new potential contribution
        int new_weight = MIN(weight_m, gf->adj_matrix[src_f*NUM_NODES + node_f2]);
        delta += new_weight;
    }

    return delta;
}

int* optimal_assignment(int k, double** cost_matrix){
    hungarian_problem_t problem;
    int mode = HUNGARIAN_MODE_MAXIMIZE_UTIL; // Solve for maximizing cost
    int matrix_size = hungarian_init(&problem, cost_matrix, k, k, mode);

    // Solve the assignment problem
    hungarian_solve(&problem);

    int* assignment = return_assignment(&problem);
    hungarian_free(&problem);
    
    return assignment;
}

void log_iteration_to_file_hungarian(const char* filename, long iteration, int score, int bestScore) {
    FILE* file = fopen(filename, "a");  // Open in append mode
    if (!file) {
        LOG_ERROR("Failed to open log file: %s", filename);
        return;
    }
    
    // Write iteration number and score
    fprintf(file, "%ld,%lu,%d,%d\n", iteration, (unsigned long) time(NULL), score, bestScore);
    
    fclose(file);
}


// Function to optimize mapping
hungarian_out optimize_hungarian(Graph* gm, Graph* gf, int* initial_mapping,
                     int current_score, int iters, const char* log_filename) {
    int max_node = NUM_NODES;

    int* current_mapping = malloc(sizeof(int) * (max_node + 1));
    int* old_mapping = malloc(sizeof(int) * (max_node + 1));  // For validation

    bool* updated_nodes = calloc(NUM_NODES+1, sizeof(bool));


    memcpy(current_mapping, initial_mapping, sizeof(int) * (max_node + 1));
    int* rev_mapping = malloc(sizeof(int) * (max_node + 1));
    for (int i=1; i<=max_node; i++){
        rev_mapping[current_mapping[i]] = i;
    }

    // int current_score = calculate_alignment_score(gm, gf, current_mapping);
    int outer_node_count = 0;
    int improvements = 0;
    time_t start_time = time(NULL);
    
    LOG_INFO("Starting optimization with initial score: %s", format_number(current_score));
    srand(time(NULL));
    int k=750; //choose 750 independent nodes
    // int iter=0;
    for (int iter = 0; iter < iters; iter++){
        if(interrupted != 0){
            fprintf(stderr, "Interrupted in Hungarian!\n");
            break;
        }
        srand(time(NULL));  

        log_iteration_to_file_hungarian(log_filename, iter, current_score, current_score);

        //optimization loop
        bool* available = malloc(sizeof(int) * (NUM_NODES + 1));
        int rem_nodes = NUM_NODES;
        // iter++;
        for (int i=1; i<=NUM_NODES; i++){
            available[i]=true;
        }
        int* subset = malloc(sizeof(int) * (k));
        //printf("YES\n");

        for (int i=0; i<k; i++){
            //printf("YES\n");

            //printf("i: %i, rem_nodes: %i", i, rem_nodes);
            if (rem_nodes<=0) break;
            int rand_ind = (rand() % rem_nodes)+1;
            int chosen=-1;
            for (int node=1; node<=NUM_NODES; node++){
                if (available[node]==false) continue;
                rand_ind--;
                if (rand_ind == 0){
                    chosen = node;
                    break;
                }
            }
            if (chosen==-1){
                printf("NOT FOUND ERROR!\n");
            }

            rem_nodes--;
            available[chosen]=false;
            subset[i] = chosen;

            //update the updated nodes
            // updated_nodes[chosen] = true; 

            //now, update all neighbors
            for (int j = 0; j < gm->edges[chosen].count; j++) {
                int dst = gm->edges[chosen].to_nodes[j];
                if (available[dst]){
                    rem_nodes--;
                }
                available[dst]=false;
            }
            for (int j = 0; j < gm->reverse_edges[chosen].count; j++) {
                int dst = gm->reverse_edges[chosen].to_nodes[j];
                if (available[dst]){
                    rem_nodes--;
                }
                available[dst]=false;
            }

        }
        
        free(available);

        if (rem_nodes>=NUM_NODES-k){
            printf("NOT ABLE TO FIND LARGE ENOUGH, %i\n", rem_nodes);
        }
        int* prevMapping = malloc(sizeof(int) * (k));
        for (int i=0; i<k; i++){
            prevMapping[i] = current_mapping[subset[i]];
            //printf("%i: %i\n", i,subset[i]);
        }

        //printf("STEP 4\n");
        double** cost_matrix = (double**)calloc(k, sizeof(double*));
        for (int i = 0; i < k; i++) {
            cost_matrix[i] = (double*)calloc(k, sizeof(double));
        }
        //printf("k: %i\n", k);
        const int maxCount = k * k;

        // for (int i=0; i<k; i++){
        //     for (int j=0; j<k; j++){
        #pragma omp parallel for schedule(dynamic, 10000)
        for(int n = 0; n < maxCount; n++) {
            int i = n / k;
            int j = n % k;
        
            if (i==j) {
                cost_matrix[i][j] = 0;
                continue;
            }
            int m_i = subset[i];
            int m_j = subset[j]; 
            //cost_matrix[i][j] = 0;
            cost_matrix[i][j] = one_side_swap_delta(gm, gf, current_mapping, m_i, m_j);
            //printf("%f ", cost_matrix[i][j]);
        //     }
        //     //printf("\n");
        // }
        }

        int* assignments = optimal_assignment(k, cost_matrix);
        int delta = 0;
        int changed=0;
        for (int i=0; i<k; i++){
            //printf("%i, %i\n", i, assignments[i]);
            if (assignments[i]!=i){
                changed++;
            }
            delta += cost_matrix[i][assignments[i]];
            current_mapping[subset[i]] = prevMapping[assignments[i]];
            rev_mapping[prevMapping[assignments[i]]] = subset[i];
        }

        current_score += delta;
        current_score = calculate_alignment_score(gm, gf, current_mapping);

        if(iter % 20 == 0 && CURRENT_LOG_LEVEL <= LOG_LEVEL_INFO){
            printf("Iter: %d, Score: %d, Delta: %d, Changed: %d\n", iter, current_score, delta, changed);
        }
        
        for (int i = 0; i < k; i++) {
            free(cost_matrix[i]);
        }
        free(cost_matrix);
        free(assignments);
        free(prevMapping);
        free(subset);
    }

    for(int i = 1; i < NUM_NODES+1; i++){
        if(initial_mapping[i] != current_mapping[i]){
            updated_nodes[i] = true;
        }
    }

    time_t end_time = time(NULL);
    LOG_INFO("Optimization completed:");
    LOG_INFO("  - Final score: %s", format_number(current_score));
    LOG_INFO("  - Total improvements: %s", format_number(improvements));
    LOG_INFO("  - Time taken: %.1f minutes", difftime(end_time, start_time) / 60);
    
    free(old_mapping);

    hungarian_out out = {current_mapping, updated_nodes};
    return out;
}