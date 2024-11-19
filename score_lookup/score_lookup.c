#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "heap.h"

#define SAVE_INTERVAL 25
#define UPDATE_INTERVAL 20
#define MAX_LINE_LENGTH 1024
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define MAX_NODES 100000

const int NUM_NODES = 18524;
const int HEAP_CAPACITY = 10000;
const bool ACCEPT_ZERO_DELTA = true;
const int SAVE_FREQUENCY = 800;
const int PROBABILISTIC_INTERVAL = 50;
const int ITERATIONS = 10000;

typedef enum {
  LOG_LEVEL_INFO = 0,
  LOG_LEVEL_DEBUG = 1,
  LOG_LEVEL_ERROR = 2
} LogLevel;

#define CURRENT_LOG_LEVEL LOG_LEVEL_INFO

#define LOG_ERROR(fmt, ...)                                         \
    if (CURRENT_LOG_LEVEL <= LOG_LEVEL_ERROR) {                       \
    fprintf(stderr, "[ERROR] %s:%d: " fmt "\n", __func__, __LINE__, \
            ##__VA_ARGS__);                                         \
    }

#define LOG_INFO(fmt, ...)                     \
    if (CURRENT_LOG_LEVEL <= LOG_LEVEL_INFO) {   \
    printf("[INFO] " fmt "\n", ##__VA_ARGS__); \
    }

#define LOG_DEBUG(fmt, ...)                                   \
    if (CURRENT_LOG_LEVEL <= LOG_LEVEL_DEBUG) {                 \
    printf("[DEBUG] %s: " fmt "\n", __func__, ##__VA_ARGS__); \
    }

// Structure definitions
typedef struct EdgeMap {
    int *to_nodes;
    int *weights;
    int count;
    int capacity;
} EdgeMap;

typedef struct Graph {
    EdgeMap *edges;
    EdgeMap *reverse_edges;
    short *adj_matrix;
    int node_capacity;
} Graph;

// Progress bar function
void print_progress(int current, int total, const char *prefix) {
    const int bar_width = 50;
    float progress = (float)current / total;
    int filled = (int)(bar_width * progress);

    printf("\r%s [", prefix);
    for (int i = 0; i < bar_width; i++) {
    if (i < filled)
        printf("=");
    else if (i == filled)
        printf(">");
    else
        printf(" ");
    }
    printf("] %.1f%%", progress * 100);
    fflush(stdout);
    if (current == total) printf("\n");
}

// Function to format numbers with commas
char *format_number(int num) {
    static char formatted[32];
    char temp[32];
    int i = 0, j = 0;

    sprintf(temp, "%d", num);
    int len = strlen(temp);

    while (len > 0) {
        if (i > 0 && i % 3 == 0) formatted[j++] = ',';
        
        formatted[j++] = temp[len - 1];
        len--;
        i++;
    }
    formatted[j] = '\0';

    // Reverse the string
    for (i = 0; i < j / 2; i++) {
        char t = formatted[i];
        formatted[i] = formatted[j - 1 - i];
        formatted[j - 1 - i] = t;
    }

    return formatted;
}

EdgeMap *new_edge_map() {
    EdgeMap *em = malloc(sizeof(EdgeMap));
    if (!em) {
    LOG_ERROR("Failed to allocate EdgeMap");
    exit(1);
    }
    em->capacity = 100;
    em->count = 0;
    em->to_nodes = malloc(sizeof(int) * em->capacity);
    em->weights = malloc(sizeof(int) * em->capacity);
    if (!em->to_nodes || !em->weights) {
        LOG_ERROR("Failed to allocate EdgeMap arrays");
        exit(1);
    }
    return em;
}

Graph *new_graph() {
    Graph *g = malloc(sizeof(Graph));
    if (!g) {
    LOG_ERROR("Failed to allocate Graph");
    exit(1);
    }
    g->edges = NULL;
    g->reverse_edges = NULL;
    g->adj_matrix = NULL;
    // g->adj_matrix =
    //     (short *)calloc((NUM_NODES + 1) * (NUM_NODES + 1), sizeof(short *));
    g->adj_matrix =
        (short *)calloc((NUM_NODES + 1) * (NUM_NODES + 1), sizeof(short));
    g->node_capacity = 10000;
    return g;
}

void add_to_edge_map(EdgeMap *em, int to, int weight) {
    if (em->count >= em->capacity) {
        em->capacity *= 2;
        int *new_to_nodes = realloc(em->to_nodes, sizeof(int) * em->capacity);
        int *new_weights = realloc(em->weights, sizeof(int) * em->capacity);
        if (!new_to_nodes || !new_weights) {
            LOG_ERROR("Failed to reallocate EdgeMap arrays");
            exit(1);
        }
        em->to_nodes = new_to_nodes;
        em->weights = new_weights;
    }
    em->to_nodes[em->count] = to;
    em->weights[em->count] = weight;
    em->count++;
}

void add_edge(Graph *g, int from, int to, int weight) {
    //    LOG_DEBUG("Adding edge: %d -> %d (weight: %d)", from, to, weight);
    g->adj_matrix[from * NUM_NODES + to] = weight;

    if (g->edges == NULL) {
        g->edges = calloc(MAX_NODES, sizeof(EdgeMap));
        g->reverse_edges = calloc(MAX_NODES, sizeof(EdgeMap));

        if (!g->edges || !g->reverse_edges) {
            LOG_ERROR("Failed to allocate edges arrays");
            exit(1);
        }
    }

    if (g->edges[from].count == 0) {
        g->edges[from] = *new_edge_map();
    }
    if (g->reverse_edges[to].count == 0) {
        g->reverse_edges[to] = *new_edge_map();
    }

    add_to_edge_map(&g->edges[from], to, weight);
    add_to_edge_map(&g->reverse_edges[to], from, weight);
}

static inline int get_weight(Graph *g, int from, int to) {
    return g->adj_matrix[from * NUM_NODES + to];
}

int calculate_alignment_score(Graph *gm, Graph *gf, int *mapping) {
    int score = 0;

    for (int src_m = 1; src_m <= NUM_NODES; src_m++) {
    // int src_m = gm->i;
        for (int j = 0; j < gm->edges[src_m].count; j++) {
            int dst_m = gm->edges[src_m].to_nodes[j];
            int weight_m = gm->edges[src_m].weights[j];
            int src_f = mapping[src_m];
            int dst_f = mapping[dst_m];
            score += MIN(weight_m, gf->adj_matrix[src_f * NUM_NODES + dst_f]);
        }
    }

    return score;
}

int calculate_swap_delta(Graph *gm, Graph *gf, int *mapping, int node_m1,
                         int node_m2) {
    int node_f1 = mapping[node_m1];
    int node_f2 = mapping[node_m2];
    int delta = 0;

    // Handle outgoing edges from node_m1
    for (int i = 0; i < gm->edges[node_m1].count; i++) {
        int dst_m = gm->edges[node_m1].to_nodes[i];
        if (dst_m == node_m2) continue;  // Skip direct edge between swapped nodes

        int weight_m = gm->edges[node_m1].weights[i];
        int dst_f = mapping[dst_m];

        // Remove old contribution
        int old_weight = MIN(weight_m, gf->adj_matrix[node_f1 * NUM_NODES + dst_f]);
        // Add new contribution
        int new_weight = MIN(weight_m, gf->adj_matrix[node_f2 * NUM_NODES + dst_f]);

        delta += new_weight - old_weight;
    }

    // Handle incoming edges to node_m1
    for (int i = 0; i < gm->reverse_edges[node_m1].count; i++) {
        int src_m = gm->reverse_edges[node_m1].to_nodes[i];
        if (src_m == node_m2) continue;  // Skip direct edge between swapped nodes

        int weight_m = gm->reverse_edges[node_m1].weights[i];
        int src_f = mapping[src_m];

        // Remove old contribution
        int old_weight = MIN(weight_m, gf->adj_matrix[src_f * NUM_NODES + node_f1]);
        // Add new contribution
        int new_weight = MIN(weight_m, gf->adj_matrix[src_f * NUM_NODES + node_f2]);

        delta += new_weight - old_weight;
    }

    // Handle outgoing edges from node_m2
    for (int i = 0; i < gm->edges[node_m2].count; i++) {
        int dst_m = gm->edges[node_m2].to_nodes[i];
        if (dst_m == node_m1) continue;  // Skip direct edge between swapped nodes

        int weight_m = gm->edges[node_m2].weights[i];
        int dst_f = mapping[dst_m];

        // Remove old contribution
        int old_weight = MIN(weight_m, gf->adj_matrix[node_f2 * NUM_NODES + dst_f]);
        // Add new contribution
        int new_weight = MIN(weight_m, gf->adj_matrix[node_f1 * NUM_NODES + dst_f]);

        delta += new_weight - old_weight;
    }

    // Handle incoming edges to node_m2
    for (int i = 0; i < gm->reverse_edges[node_m2].count; i++) {
        int src_m = gm->reverse_edges[node_m2].to_nodes[i];
        if (src_m == node_m1) continue;  // Skip direct edge between swapped nodes

        int weight_m = gm->reverse_edges[node_m2].weights[i];
        int src_f = mapping[src_m];

        // Remove old contribution
        int old_weight = MIN(weight_m, gf->adj_matrix[src_f * NUM_NODES + node_f2]);
        // Add new contribution
        int new_weight = MIN(weight_m, gf->adj_matrix[src_f * NUM_NODES + node_f1]);

        delta += new_weight - old_weight;
    }

    // Handle direct edges between the swapped nodes
    // From m1 to m2
    int m1_to_m2 = gm->adj_matrix[node_m1 * NUM_NODES + node_m2];
    if (m1_to_m2 > 0) {
        int old_weight = MIN(m1_to_m2, gf->adj_matrix[node_f1 * NUM_NODES + node_f2]);
        int new_weight = MIN(m1_to_m2, gf->adj_matrix[node_f2 * NUM_NODES + node_f1]);
        delta += new_weight - old_weight;
    }

    // From m2 to m1
    int m2_to_m1 = gm->adj_matrix[node_m2 * NUM_NODES + node_m1];
    if (m2_to_m1 > 0) {
        int old_weight = MIN(m2_to_m1, gf->adj_matrix[node_f2 * NUM_NODES + node_f1]);
        int new_weight = MIN(m2_to_m1, gf->adj_matrix[node_f1 * NUM_NODES + node_f2]);
        delta += new_weight - old_weight;
    }

    return delta;
}

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

            if (lookup[i * NUM_NODES + j] > 0 || (ACCEPT_ZERO_DELTA && lookup[i * NUM_NODES + j] == 0)) {
                insert_swap(heap, (Swap){i, j, lookup[i * NUM_NODES + j]});
            }

            if(lookup[i * NUM_NODES + j] > 0 && prints < maxPrints) {
                prints++;
                LOG_INFO("Loaded swap (%d, %d) with positive delta %d", i, j, lookup[i * NUM_NODES + j]);
            }
        }
    }

    fclose(file);
    return lookup;
}

void reinsert_into_heap(SwapHeap *heap, short *lookup) {
    for (int i = 1; i <= NUM_NODES; i++) {
        for (int j = 1; j <= NUM_NODES; j++) {
            if (lookup[i * NUM_NODES + j] > 0) {
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

// Function to load benchmark mapping from CSV
int *load_mapping(const char *filename, int max_node) {
    FILE *file = fopen(filename, "r");
    if (!file) {
        LOG_ERROR("Failed to open file: %s", filename);
        return NULL;
    }

    int *mapping = calloc(max_node + 1, sizeof(int));
    char line[MAX_LINE_LENGTH];
    int count = 0;

    // Try to get expected score from filename
    int expected_score = 0;
    const char *underscore = strrchr(filename, '_');
    if (underscore) {
        expected_score = atoi(underscore + 1);
        LOG_INFO("Expected score from filename: %d", expected_score);
    }

    // Skip header
    fgets(line, MAX_LINE_LENGTH, file);

    LOG_INFO("Loading benchmark mapping from %s", filename);

    while (fgets(line, MAX_LINE_LENGTH, file)) {
        int male_id, female_id;

        // Try direct integer format first
        if (sscanf(line, "%d,%d", &male_id, &female_id) == 2) {
            mapping[male_id] = female_id;
            count++;
        } else {
            // Try format with prefixes
            char male_str[20], female_str[20];
            if (sscanf(line, "%[^,],%s", male_str, female_str) == 2) {
                male_id = atoi(male_str + (male_str[0] == 'm' ? 1 : 0));
                female_id = atoi(female_str + (female_str[0] == 'f' ? 1 : 0));
                mapping[male_id] = female_id;
                count++;
            }
        }
    }

    LOG_INFO("Loaded %s mappings", format_number(count));

    fclose(file);
    return mapping;
}

void save_mapping(const char *filename, int *mapping) {
    FILE *file = fopen(filename, "w");
    if (!file) {
        LOG_ERROR("Error creating file: %s", filename);
        fclose(file);
        return;
    }

    fprintf(file, "Male Node ID,Female Node ID\n");
    for (int i = 1; i <= NUM_NODES; i++) {
        fprintf(file, "m%d,f%d\n", i, mapping[i]);
    }

    fclose(file);
}

int get_max_node(Graph *g) { return NUM_NODES; }

// Function to clean up graph memory
void free_graph(Graph *g) {
    if (g->edges) {
        for (int i = 0; i < MAX_NODES; i++) {
            if (g->edges[i].count > 0) {
                free(g->edges[i].to_nodes);
                free(g->edges[i].weights);
            }
        }
        free(g->edges);
    }

    if (g->reverse_edges) {
        for (int i = 0; i < MAX_NODES; i++) {
            if (g->reverse_edges[i].count > 0) {
                free(g->reverse_edges[i].to_nodes);
                free(g->reverse_edges[i].weights);
            }
        }
        free(g->reverse_edges);
    }

    if (g->adj_matrix) {
        free(g->adj_matrix);
        g->adj_matrix = NULL;
    }
    free(g);
}

Graph *load_graph_from_csv(const char *filename) {
    FILE *file = fopen(filename, "r");
    if (!file) {
    LOG_ERROR("Failed to open file: %s", filename);
    return NULL;
    }

    Graph *graph = new_graph();
    char line[MAX_LINE_LENGTH];
    int line_count = 0;
    int total_lines = 0;

    // Count total lines for progress bar
    while (fgets(line, MAX_LINE_LENGTH, file)) total_lines++;
    rewind(file);

    // Skip header
    fgets(line, MAX_LINE_LENGTH, file);
    total_lines--;  // Adjust for header

    LOG_INFO("Loading graph from %s (%s lines)", filename,
            format_number(total_lines));

    time_t start_time = time(NULL);
    while (fgets(line, MAX_LINE_LENGTH, file)) {
        int from, to, weight;
        if (sscanf(line, "%d,%d,%d", &from, &to, &weight) == 3) {
            add_edge(graph, from, to, weight);
            line_count++;
            if (line_count % 100000 == 0) {
                print_progress(line_count, total_lines, "Loading graph");
            }
        } else {
            LOG_ERROR("Malformed line in CSV: %s", line);
        }
    }

    time_t end_time = time(NULL);
    LOG_INFO("Graph loaded successfully:");
    LOG_INFO("  - Nodes: %s", format_number(NUM_NODES));
    LOG_INFO("  - Edges: %s", format_number(line_count));
    LOG_INFO("  - Time taken: %lld seconds", end_time - start_time);

    fclose(file);
    return graph;
}

void update_lookup_and_heap(short *lookup, SwapHeap *swapHeap, Graph *gm,
                         Graph *gf, int *bestMapping, int nodeM1, int nodeM2) {
    for (int node = 1; node <= NUM_NODES; node++) {
        const int swapNodes[2] = {nodeM1, nodeM2};

        for (int i = 0; i < 2; i++) {
            // int swapDelta =
            //     calculate_swap_delta(gm, gf, bestMapping, node, swapNodes[i]);
            int swapDelta1 = calculate_swap_delta(gm, gf, bestMapping, node, swapNodes[i]);
            int swapDelta2 = calculate_swap_delta(gm, gf, bestMapping, swapNodes[i], node);

            lookup[node * NUM_NODES + swapNodes[i]] = (short) swapDelta1;
            lookup[swapNodes[i] * NUM_NODES + node] = (short) swapDelta2;

            if (swapDelta1 > 0 || (ACCEPT_ZERO_DELTA && swapDelta1 == 0) ) {
                insert_swap(swapHeap, (Swap){node, swapNodes[i], swapDelta1});
            }

            if (swapDelta2 > 0 || (ACCEPT_ZERO_DELTA && swapDelta2 == 0) ) {
                insert_swap(swapHeap, (Swap){swapNodes[i], node, swapDelta2});
            }
        }
    }
}

// Random number between 0 and 1
double random_double(){
    unsigned int rnd = rand() & 0x7fff;
    rnd |= (rand() & 0x7fff) << 15;
    return (double)rnd / (double)0x3fffffff; //2^30 - 1
}

static inline bool acceptProbabilisticSwap(int delta, double temperature) { 
    return random_double() < exp((double) delta / temperature); 
}

int probabilistic_swaps(short *lookup, SwapHeap *swapHeap, Graph *gm,
                         Graph *gf, int *bestMapping, int score, int numSwaps, double temperature, bool acceptZeroDelta) {
    
    LOG_INFO("Performing %d probabilistic swaps with temperature %f", numSwaps, temperature);
    int swaps = 0;
    int evaluatedSwaps = 0;
    int newScore = score;
    while (swaps < numSwaps) {
        evaluatedSwaps++;
        int nodeM1 = (rand() % (NUM_NODES-1)) + 1;
        int nodeM2 = rand() % NUM_NODES + 1;
        if (nodeM1 == nodeM2) nodeM2++;

        int delta = lookup[nodeM1 * NUM_NODES + nodeM2];

        if(evaluatedSwaps == 1){
            LOG_INFO("First swap delta: %d", delta);
            LOG_INFO("Actual delta: %d", calculate_swap_delta(gm, gf, bestMapping, nodeM1, nodeM2));
        }
        // int delta = calculate_swap_delta(gm, gf, bestMapping, nodeM1, nodeM2);

        if (delta == 0 && !acceptZeroDelta) continue;

        if(delta > 0 || (acceptZeroDelta && delta == 0) || acceptProbabilisticSwap(delta, temperature)) {
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

int *optimize_mapping(Graph *gm, Graph *gf, int *inMapping, short *lookup,
                     int *outMapping, SwapHeap *swapHeap, const char* outMappingFile, const char* outLookupFile) {
    int score = calculate_alignment_score(gm, gf, inMapping);
    int *bestMapping = calloc(NUM_NODES + 1, sizeof(int));
    memcpy(bestMapping, inMapping, (NUM_NODES + 1) * sizeof(int));

    const int probabilisticSwaps = 4;
    const double probabilisticTemperature = 1.0;

    int bestScore = score;
    bool changed = false;

    for (int i = 0; i < ITERATIONS; i++) {
        if(i % PROBABILISTIC_INTERVAL == 0 && all_zero_delta(swapHeap)){
            LOG_INFO("Performing probabilistic swaps at iteration %d", i);
            score = probabilistic_swaps(lookup, swapHeap, gm, gf, inMapping, score, probabilisticSwaps, probabilisticTemperature, false);
        }
        Swap bestSwap;

        if(!extract_max(swapHeap, &bestSwap)) {
            LOG_ERROR("Failed to extract swap from heap at iteration %d; most likely heap is empty", i);
            break;
        }

        int nodeM1 = bestSwap.nodeM1;
        int nodeM2 = bestSwap.nodeM2;
        int delta = bestSwap.delta;

        score += delta;

        int temp = inMapping[nodeM1];
        inMapping[nodeM1] = inMapping[nodeM2];
        inMapping[nodeM2] = temp;
        
        invalidate_swaps(swapHeap, nodeM1);
        invalidate_swaps(swapHeap, nodeM2);

        update_lookup_and_heap(lookup, swapHeap, gm, gf, inMapping, nodeM1, nodeM2);

        if(i % 100 == 0){
            int actual_score = calculate_alignment_score(gm, gf, inMapping);
            LOG_INFO("Iteration %d:\tScore = %d\tActual score: %d", i, score, actual_score);
            if (actual_score != score){
                LOG_INFO("Score and actual score do not match, discrepancy of %d", actual_score - score);
            }

            score = actual_score;

            if(actual_score > bestScore){
                bestScore = actual_score;
                changed = true;

                LOG_INFO("New best score: %d", bestScore);

                memcpy(bestMapping, inMapping, (NUM_NODES + 1) * sizeof(int));
            }
        }

        if (changed && i != 0 && i % SAVE_FREQUENCY == 0) {
            LOG_INFO("Saving mapping and lookup at iteration %d with score %d", i, bestScore);
            save_lookup(outLookupFile, lookup);
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

    srand(time(NULL));

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