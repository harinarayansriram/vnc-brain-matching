#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include <string.h>
#include <time.h>
#include <omp.h>

#include "heap.h"
#include "xoshiro.h"
#include "utils.h"
#include "hungarian-subset.h"

#define CURRENT_LOG_LEVEL LOG_LEVEL_INFO

const int HEAP_CAPACITY = 200 * 1000;
const bool ACCEPT_ZERO_DELTA = true;
const int SAVE_FREQUENCY = 800;
const int ITERATIONS = 2 * 1000 * 1000;
const int REINSERT_INTERVAL = 50 * 1000; //HEAP_CAPACITY / 4; only needs to be HEAP_CAPACITY / 2 (or possibly HEAP_CAPACITY) but just for testing

const bool PROBABILISTIC = true;
const bool SIMULATED_ANNEALING = true;
const bool HUNGARIAN = true;
const int PROBABILISTIC_INTERVAL = 200;
const int PROBABILISTIC_SWAPS = 12;
const int SIMULATED_ANNEALING_INTERVAL = 5000;
const double PROBABILISTIC_TEMPERATURE = 1.0;
const int HUNGARIAN_ITERS = 1000;
const int HUNGARIAN_INTERVAL = 1000;

short *load_lookup(const char *filename, SwapHeap *heap) {
    LOG_INFO("Loading score lookup...");

    FILE *file = fopen(filename, "r");
    if (!file) {
        LOG_ERROR("Failed to open file: %s", filename);
        return NULL;
    }

    short *lookup =
        (short *)calloc((NUM_NODES + 1) * (NUM_NODES + 1), sizeof(short));

    int maxPrints = 100;
    int prints = 0;

    for (int i = 1; i <= NUM_NODES; i++) {
        if (i % 1000 == 0) print_progress(i, NUM_NODES, "Loading lookup...");

        for (int j = 1; j <= NUM_NODES; j++) {
            if (fscanf(file, "%hd,", &lookup[i * NUM_NODES + j]) != 1) {
                fprintf(stderr, "Error reading file: %s at row %d, column %d\n",
                        filename, i, j);
                fclose(file);
                free(lookup);
                return NULL;
            }

            short delta = lookup[i*NUM_NODES + j];

            if (i > j && (delta > 0 || (ACCEPT_ZERO_DELTA && delta == 0))) {
                insert_swap(heap, (Swap){i, j, delta});
            }

            if(delta > 0 && prints < maxPrints) {
                prints++;
                LOG_INFO("Loaded swap (%d, %d) with positive delta %d", i, j, delta);
            }
        }
    }

    fclose(file);
    return lookup;
}

void reinsert_into_heap(SwapHeap *heap, short *lookup, bool acceptZero) {
    for (int i = 1; i <= NUM_NODES; i++) {
        for (int j = 1; j <= NUM_NODES; j++) {
            if (i > j && (lookup[i * NUM_NODES + j] > 0 || (acceptZero && lookup[i * NUM_NODES + j] == 0))) {
                insert_swap(heap, (Swap){i, j, lookup[i * NUM_NODES + j]});
            }
        }
    }
}

void save_lookup(const char *filename, short *lookup) {
    FILE *file = fopen(filename, "w");
    if (!file) {
        LOG_ERROR("Error creating file: %s", filename);
        fclose(file);
        return;
    }

    for (int i = 0; i < NUM_NODES; i++) {
        for (int j = 0; j < NUM_NODES - 1; j++) {
            fprintf(file, "%d,", lookup[i * NUM_NODES + j]);
        }
        fprintf(file, "%d", lookup[i * NUM_NODES + NUM_NODES - 1]);
        fprintf(file, "\n");
    }

    fclose(file);
}

void update_lookup_and_heap(short *lookup, SwapHeap *swapHeap, Graph *gm,
                         Graph *gf, int *bestMapping, int nodeM1, int nodeM2) {
    // Use OpenMP to parallelize the nested loops
    #pragma omp parallel
    {
        // Create thread-local heaps to avoid contention
        SwapHeap *local_heap = create_swap_heap(1000);

        #pragma omp for schedule(dynamic)
        for (int node = 1; node <= NUM_NODES; node++) {
            const int swapNodes[2] = {nodeM1, nodeM2};

            for (int i = 0; i < 2; i++) {
                // Calculate swap delta, which is thread-safe as it doesn't modify shared state
                int swapDelta = calculate_swap_delta(gm, gf, bestMapping, node, swapNodes[i]);

                // Use atomic updates to safely modify shared lookup array
                #pragma omp critical
                {
                    lookup[node * NUM_NODES + swapNodes[i]] = (short) swapDelta;
                    lookup[swapNodes[i] * NUM_NODES + node] = (short) swapDelta;
                }

                // Collect swaps with positive or zero delta
                if (swapNodes[i] != node && (swapDelta > 0 || (ACCEPT_ZERO_DELTA && swapDelta == 0))) {
                    insert_swap(local_heap, (Swap){node, swapNodes[i], swapDelta});
                }
            }
        }

        // Merge local heap into global heap with a critical section
        #pragma omp critical
        {
            for (int i = 0; i < local_heap->size; i++) {
                insert_swap(swapHeap, local_heap->data[i]);
            }
        }

        // Clean up local heap
        destroy_swap_heap(local_heap);
    }
}

void update_lookup_and_heap_from_selected_nodes(short *lookup, SwapHeap *swapHeap, Graph *gm, 
                                              Graph *gf, int *bestMapping, bool *selectedNodes) {
    #pragma omp parallel
    {
        // Create thread-local heap to avoid contention
        SwapHeap *local_heap = create_swap_heap(1000);
        
        // First loop: each thread processes a subset of all nodes
        #pragma omp for schedule(dynamic)
        for (int node1 = 1; node1 <= NUM_NODES; node1++) {
            // Only process if this node needs updating
            if (selectedNodes[node1]) {
                // For each selected node, we need to calculate its interaction with all other nodes
                for (int node2 = 1; node2 <= NUM_NODES; node2++) {
                    if (node1 != node2) {
                        int swapDelta = calculate_swap_delta(gm, gf, bestMapping, node1, node2);
                        
                        // Update lookup table - needs synchronization
                        #pragma omp critical
                        {
                            lookup[node1 * NUM_NODES + node2] = (short)swapDelta;
                            lookup[node2 * NUM_NODES + node1] = (short)swapDelta;
                        }
                        
                        // Add to heap if it's a beneficial swap
                        if (node1 > node2 && (swapDelta > 0 || (ACCEPT_ZERO_DELTA && swapDelta == 0))) {
                            insert_swap(local_heap, (Swap){node1, node2, swapDelta});
                        }
                    }
                }
            }
        }
        
        // Merge thread-local heap into global heap
        #pragma omp critical
        {
            for (int i = 0; i < local_heap->size; i++) {
                insert_swap(swapHeap, local_heap->data[i]);
            }
        }
        
        // Clean up local heap
        destroy_swap_heap(local_heap);
    }
}
// Random number between 0 and 1
static inline double random_double(struct xoshiro256ss_state *state){
    return ((double) xoshiro256ss(state)) / (double) UINT64_MAX;
}

static inline bool acceptProbabilisticSwap(int delta, double temperature, struct xoshiro256ss_state *state) { 
    return random_double(state) < exp((double) delta / temperature); 
}

int probabilistic_swaps(short *lookup, SwapHeap *swapHeap, Graph *gm,
                         Graph *gf, int *bestMapping, int score, int numSwaps, double temperature, bool acceptZeroDelta, struct xoshiro256ss_state *state) {
    
    LOG_INFO("Performing %d probabilistic swaps with temperature %f", numSwaps, temperature);
    int swaps = 0;
    int evaluatedSwaps = 0;
    int newScore = score;
    while (swaps < numSwaps) {
        evaluatedSwaps++;
        int nodeM1 = (int) (xoshiro256ss(state) % (NUM_NODES-1)) + 1;
        int nodeM2 = (int) (xoshiro256ss(state) % NUM_NODES) + 1;
        if (nodeM1 == nodeM2) nodeM1++;

        int delta = lookup[nodeM1 * NUM_NODES + nodeM2];

        if (delta == 0 && !acceptZeroDelta) continue;

        if(delta > 0 || (acceptZeroDelta && delta == 0) || acceptProbabilisticSwap(delta, temperature, state)) {
            swaps++;
            
            int temp = bestMapping[nodeM1];
            bestMapping[nodeM1] = bestMapping[nodeM2];
            bestMapping[nodeM2] = temp;
            
            newScore += delta;

            invalidate_swaps(swapHeap, nodeM1);
            invalidate_swaps(swapHeap, nodeM2);

            update_lookup_and_heap(lookup, swapHeap, gm, gf, bestMapping, nodeM1, nodeM2);
        }
    }

    LOG_INFO("Evaluated %d swaps, performed %d swaps", evaluatedSwaps, numSwaps);
    LOG_INFO("New score: %d, actual new score: %d, total delta: %d", newScore, calculate_alignment_score(gm, gf, bestMapping), newScore - score);

    return newScore;
}

int simulated_annealing(short *lookup, SwapHeap *swapHeap, Graph *gm,
                         Graph *gf, int *inMapping, int score, int iterations, double tmin, double tmax, struct xoshiro256ss_state *state) {
    LOG_INFO("Performing %d simulated annealing iterations from T=%.2lf to T=%.2lf", iterations, tmax, tmin);
    
    double t_factor = log(tmin / tmax);

    int curScore = score;
    int swaps = 0;

    int* bestMapping = calloc(NUM_NODES + 1, sizeof(int));
    int bestScore = score;

    memcpy(bestMapping, inMapping, (NUM_NODES + 1) * sizeof(int));

    for(int i = 0; i < iterations; i++){
        
        double temperature = tmax * exp(t_factor * i / (double) iterations);
        
        if(i % 10000000 == 0){
            LOG_INFO("Iteration %d of %d (%.2f%% complete, T=%.2lf). Performed %d swaps. Current score: %d, best score: %d", i, iterations, 100.0 * i / iterations, temperature, swaps, curScore, bestScore);
        }

        int nodeM1 = (int) (xoshiro256ss(state) % (NUM_NODES-1)) + 1;
        int nodeM2 = (int) (xoshiro256ss(state) % NUM_NODES) + 1;
        if (nodeM1 == nodeM2) nodeM1++;

        if(nodeM1 == 0 || nodeM2 == 0){
            LOG_DEBUG("Swap with node 0 in iteration %d of simulated annealing", i);
            continue;
        }

        if(nodeM1 == nodeM2){
            LOG_DEBUG("Swap with same node in iteration %d of simulated annealing", i);
            continue;
        }

        int delta = lookup[nodeM1 * NUM_NODES + nodeM2];

        if (delta >= 0 || acceptProbabilisticSwap(delta, temperature, state) ) {
            swaps++;

            int temp = inMapping[nodeM1];
            inMapping[nodeM1] = inMapping[nodeM2];
            inMapping[nodeM2] = temp;
            
            curScore += delta;

            invalidate_swaps(swapHeap, nodeM1);
            invalidate_swaps(swapHeap, nodeM2);

            update_lookup_and_heap(lookup, swapHeap, gm, gf, inMapping, nodeM1, nodeM2);
            
            if(curScore > bestScore){
                bestScore = curScore;
                memcpy(bestMapping, inMapping, (NUM_NODES + 1) * sizeof(int));
            }
        }
    }

    LOG_INFO("Performed %d swaps", swaps);
    LOG_INFO("New score: %d, actual new score: %d, total delta: %d", curScore, calculate_alignment_score(gm, gf, inMapping), curScore - score);

    return calculate_alignment_score(gm, gf, inMapping);
}

int *optimize_mapping(Graph *gm, Graph *gf, int *inMapping, short *lookup,
                     int *outMapping, SwapHeap *swapHeap, const char* outMappingFile, const char* outLookupFile) {
    int score = calculate_alignment_score(gm, gf, inMapping);
    int *bestMapping = calloc(NUM_NODES + 1, sizeof(int));
    memcpy(bestMapping, inMapping, (NUM_NODES + 1) * sizeof(int));

    int bestScore = score;
    bool changed = false;

    int lastImproved = 0;

    xoshiro256ss_state state;
    xoshiro256ss_init(&state, time(NULL));

    for (int i = 0; i < ITERATIONS; i++) {
        if(i % REINSERT_INTERVAL == 0){
            LOG_INFO("Reinserting into heap at iteration %d", i);
            reinsert_into_heap(swapHeap, lookup, true);
            LOG_INFO("Finished reinsertion");
        } 

        if( (PROBABILISTIC || SIMULATED_ANNEALING || HUNGARIAN) && (i - lastImproved) > 1500 && i % PROBABILISTIC_INTERVAL == 0 && no_positive_deltas(swapHeap)){
            if(SIMULATED_ANNEALING && i % SIMULATED_ANNEALING_INTERVAL == 0){
                LOG_INFO("Performing simulated annealing at iteration %d", i);
                score = simulated_annealing(lookup, swapHeap, gm, gf, inMapping, calculate_alignment_score(gm, gf, inMapping), (int) 5*pow(10,7), 0.1, 1.0, &state);
            }else if(HUNGARIAN && i % HUNGARIAN_INTERVAL == 0){
                LOG_INFO("Performing hungarian at iteration %d", i);
                hungarian_out hungarianResult = optimize_hungarian(gm, gf, inMapping, calculate_alignment_score(gm, gf, inMapping), HUNGARIAN_ITERS);;
                inMapping = hungarianResult.mapping;
                update_lookup_and_heap_from_selected_nodes(lookup, swapHeap, gm, gf, inMapping, hungarianResult.updated_nodes);
                free(hungarianResult.updated_nodes);
                score = calculate_alignment_score(gm, gf, inMapping);
            }
            else if(PROBABILISTIC){
                LOG_INFO("Performing probabilistic swaps at iteration %d", i);
                score = probabilistic_swaps(lookup, swapHeap, gm, gf, inMapping, score, PROBABILISTIC_SWAPS, PROBABILISTIC_TEMPERATURE, false, &state);
            }

            reinsert_into_heap(swapHeap, lookup, true);
        }

        Swap bestSwap;

        while(!extract_max(swapHeap, &bestSwap)) {
            // LOG_ERROR("Failed to extract swap from heap at iteration %d; most likely heap is empty", i);
            // break;
            LOG_INFO("Reinserting into heap at iteration %d", i);
            reinsert_into_heap(swapHeap, lookup, true);
        }

        int nodeM1 = bestSwap.nodeM1;
        int nodeM2 = bestSwap.nodeM2;
        int delta = bestSwap.delta;

        if(nodeM1 == 0 || nodeM2 == 0){
            LOG_DEBUG("Swap with node 0 in iteration %d of optimize_mapping", i);
            invalidate_swaps(swapHeap, 0);
            update_lookup_and_heap(lookup, swapHeap, gm, gf, inMapping, 0, MAX(nodeM1, nodeM2));
            continue;
        }

        if(nodeM1 == nodeM2){
            LOG_DEBUG("Swap with same node (%d) in iteration %d of optimize_mapping", i, nodeM1);
            invalidate_swaps(swapHeap, nodeM1);
            update_lookup_and_heap(lookup, swapHeap, gm, gf, inMapping, nodeM1, nodeM2);
            continue;
        }

        if(i % 100 == 0){
            LOG_INFO("Best Swap: Score = %d\tDelta = %d\tNode 1 = %d\tNode 2 = %d, All zero delta: %s", score, delta, nodeM1, nodeM2, no_positive_deltas(swapHeap) ? "yes" : "no");
            invalidate_swaps(swapHeap, nodeM1);
            invalidate_swaps(swapHeap, nodeM2);
        }

        score += delta;

        int temp = inMapping[nodeM1];
        inMapping[nodeM1] = inMapping[nodeM2];
        inMapping[nodeM2] = temp;
        
        invalidate_swaps(swapHeap, nodeM1);
        invalidate_swaps(swapHeap, nodeM2);

        update_lookup_and_heap(lookup, swapHeap, gm, gf, inMapping, nodeM1, nodeM2);

        invalidate_swaps(swapHeap, nodeM1);
        invalidate_swaps(swapHeap, nodeM2);

        if(i % 100 == 0){
            int actual_score = calculate_alignment_score(gm, gf, inMapping);
            LOG_INFO("Iteration %d:\tScore = %d\tActual score: %d\tHeap size: %d", i, score, actual_score, swapHeap->size);
            if (actual_score != score){
                LOG_INFO("Score and actual score do not match, discrepancy of %d", actual_score - score);
            }

            score = actual_score;

            if(actual_score > bestScore){
                bestScore = actual_score;
                changed = true;
                lastImproved = i;

                LOG_INFO("New best score: %d", bestScore);

                memcpy(bestMapping, inMapping, (NUM_NODES + 1) * sizeof(int));
            }
        }

        if (changed && i != 0 && i % SAVE_FREQUENCY == 0) {
            LOG_INFO("Saving mapping and lookup at iteration %d with score %d", i, bestScore);
            // save_lookup(outLookupFile, lookup);
            save_mapping(outMappingFile, bestMapping);

            changed = false;
        }
    }

    LOG_INFO("Final score: %d", score);
    int final_score = calculate_alignment_score(gm, gf, inMapping);
    LOG_INFO("Final actual score: %d", calculate_alignment_score(gm, gf, inMapping));

    if(final_score > bestScore){
        bestScore = final_score;
        memcpy(bestMapping, inMapping, (NUM_NODES + 1) * sizeof(int));
    }
    LOG_INFO("Saving final mapping and lookup with score %d", bestScore);

    save_lookup(outLookupFile, lookup);
    save_mapping(outMappingFile, bestMapping);

    return bestMapping;
}

// Main function
int main(int argc, char *argv[]) {
    if (argc < 5) {
        LOG_ERROR(
            "Usage: %s <male graph> <female graph> <in mapping> <in lookup> <out mapping> <out lookup>",
            argv[0]);
        return 1;
    }

    time_t total_start = time(NULL);
    LOG_INFO("Score Lookup Tool v1.0");
    LOG_INFO("Starting process with:");
    LOG_INFO("  - Male graph: %s", argv[1]);
    LOG_INFO("  - Female graph: %s", argv[2]);
    LOG_INFO("  - In Mapping: %s", argv[3]);
    LOG_INFO("  - In Lookup: %s", argv[4]);
    LOG_INFO("  - Output mapping: %s", argv[5]);
    LOG_INFO("  - Output Lookup: %s", argv[6]);

    Graph *gm, *gf = NULL;
    int *inMapping = NULL;
    int *bestMapping = NULL;
    short *lookup = NULL;
    SwapHeap *swapHeap = create_swap_heap(HEAP_CAPACITY);

    int EXIT_STATUS = 0;

    gm = load_graph_from_csv(argv[1]);
    if (!gm) {
        LOG_ERROR("Failed to load male graph");
        EXIT_STATUS = 1;
        goto cleanup;
    }

    gf = load_graph_from_csv(argv[2]);
    if (!gf) {
        LOG_ERROR("Failed to load female graph");
        EXIT_STATUS = 1;
        goto cleanup;
    }

    int max_node = MAX(get_max_node(gm), get_max_node(gf));

    inMapping = load_mapping(argv[3], max_node);
    if (!inMapping) {
        LOG_ERROR("Failed to load input mapping");
        EXIT_STATUS = 1;
        goto cleanup;
    }

    lookup = load_lookup(argv[4], swapHeap);
    if (!lookup) {
        LOG_ERROR("Failed to load lookup file");
        EXIT_STATUS = 1;
        goto cleanup;
    }

    int initial_score = calculate_alignment_score(gm, gf, inMapping);
    LOG_INFO("Initial alignment score: %s", format_number(initial_score));

    bestMapping = optimize_mapping(gm, gf, inMapping, lookup, inMapping, swapHeap, argv[5], argv[6]);

    int final_score = calculate_alignment_score(gm, gf, bestMapping);

    time_t total_end = time(NULL);
    LOG_INFO("Process completed:");
    LOG_INFO("  - Initial score: %s", format_number(initial_score));
    LOG_INFO("  - Final score: %s", format_number(final_score));
    LOG_INFO("  - Improvement: %s", format_number(initial_score - final_score));
    LOG_INFO("  - Total time: %.1f minutes",
            difftime(total_end, total_start) / 60);

    cleanup:
        free_graph(gm);
        free_graph(gf);
        free(lookup);
        free(inMapping);
        free(bestMapping);
        destroy_swap_heap(swapHeap);

    return EXIT_STATUS;
}