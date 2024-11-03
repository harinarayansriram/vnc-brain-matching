#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <sys/stat.h>
#include <ctype.h>

#define MAX_BASE_ID_LENGTH 31
#define MAX_ID_LENGTH (MAX_BASE_ID_LENGTH + 1)
#define HASH_SIZE 65536
#define BUFFER_SIZE (1024 * 1024)  // 1MB buffer
#define LINE_BUFFER_SIZE 1024      // For reading lines

typedef struct Vertex {
    char id[MAX_ID_LENGTH];
    bool has_outgoing_edge;
    bool has_incoming_edge;
    bool in_matching;
    struct Vertex *next;
} Vertex;

typedef struct {
    Vertex **buckets;
    size_t count;
} VertexHash;

typedef struct {
    char male_id[MAX_ID_LENGTH];
    char female_id[MAX_ID_LENGTH];
} MatchingPair;

static inline void safe_strcpy(char *dst, const char *src, size_t size) {
    if (!dst || !src) return;
    size_t len = strlen(src);
    if (len >= size) {
        len = size - 1;
    }
    memcpy(dst, src, len);
    dst[len] = '\0';
}

static inline unsigned int hash_string(const char *str) {
    if (!str) return 0;
    unsigned int hash = 0;
    while (*str) {
        hash = hash * 31 + *str++;
    }
    return hash % HASH_SIZE;
}

bool init_vertex_hash(VertexHash *vh) {
    if (!vh) return false;
    vh->buckets = calloc(HASH_SIZE, sizeof(Vertex*));
    if (!vh->buckets) {
        fprintf(stderr, "Failed to allocate hash table of size %d\n", HASH_SIZE);
        return false;
    }
    vh->count = 0;
    return true;
}

void free_vertex_hash(VertexHash *vh) {
    if (!vh || !vh->buckets) return;
    
    for (int i = 0; i < HASH_SIZE; i++) {
        Vertex *current = vh->buckets[i];
        while (current) {
            Vertex *next = current->next;
            free(current);
            current = next;
        }
    }
    free(vh->buckets);
    vh->buckets = NULL;
    vh->count = 0;
}

Vertex* find_vertex(VertexHash *vh, const char *id) {
    if (!vh || !vh->buckets || !id) return NULL;
    
    unsigned int bucket = hash_string(id);
    Vertex *current = vh->buckets[bucket];
    
    while (current) {
        if (strcmp(current->id, id) == 0) {
            return current;
        }
        current = current->next;
    }
    return NULL;
}

Vertex* add_vertex(VertexHash *vh, const char *id, bool in_matching) {
    if (!vh || !vh->buckets || !id) return NULL;
    
    unsigned int bucket = hash_string(id);
    
    // Check if already exists
    Vertex *existing = find_vertex(vh, id);
    if (existing) {
        if (in_matching) {
            existing->in_matching = true;
        }
        return existing;
    }
    
    // Create new vertex
    Vertex *new_vertex = malloc(sizeof(Vertex));
    if (!new_vertex) {
        fprintf(stderr, "Failed to allocate new vertex\n");
        return NULL;
    }
    
    safe_strcpy(new_vertex->id, id, MAX_ID_LENGTH);
    new_vertex->has_outgoing_edge = false;
    new_vertex->has_incoming_edge = false;
    new_vertex->in_matching = in_matching;
    new_vertex->next = vh->buckets[bucket];
    vh->buckets[bucket] = new_vertex;
    vh->count++;
    
    return new_vertex;
}

bool process_matching_file(const char *filename, MatchingPair **matches, 
                         size_t *match_count, size_t *match_capacity,
                         VertexHash *male_vertices, VertexHash *female_vertices) {
    FILE *file = fopen(filename, "r");
    if (!file) {
        fprintf(stderr, "Cannot open matching file: %s\n", filename);
        return false;
    }
    
    printf("Opened matching file successfully\n");
    
    // Read and verify header
    char header[LINE_BUFFER_SIZE];
    if (!fgets(header, sizeof(header), file)) {
        fprintf(stderr, "Failed to read header from matching file\n");
        fclose(file);
        return false;
    }
    
    printf("Read header: %s", header);
    
    // Count lines to pre-allocate
    size_t line_count = 0;
    char ch;
    while ((ch = fgetc(file)) != EOF) {
        if (ch == '\n') line_count++;
    }
    
    printf("Counted %zu lines in matching file\n", line_count);
    
    // Reset file position
    rewind(file);
    fgets(header, sizeof(header), file);  // Skip header again
    
    // Allocate matches array
    *match_capacity = line_count;
    printf("Allocating matches array for %zu entries\n", *match_capacity);
    
    *matches = malloc(*match_capacity * sizeof(MatchingPair));
    if (!*matches) {
        fprintf(stderr, "Failed to allocate matches array\n");
        fclose(file);
        return false;
    }
    
    // Process matches
    char line[LINE_BUFFER_SIZE];
    *match_count = 0;
    size_t line_number = 1;  // Start after header
    
    while (fgets(line, sizeof(line), file)) {
        line_number++;
        char male_id[MAX_ID_LENGTH] = {0};
        char female_id[MAX_ID_LENGTH] = {0};
        
        // Remove newline if present
        char *newline = strchr(line, '\n');
        if (newline) *newline = '\0';
        
        if (sscanf(line, "%[^,],%s", male_id, female_id) != 2) {
            fprintf(stderr, "Error parsing line %zu: %s\n", line_number, line);
            continue;
        }
        
        // Verify IDs aren't too long
        if (strlen(male_id) >= MAX_ID_LENGTH || strlen(female_id) >= MAX_ID_LENGTH) {
            fprintf(stderr, "ID too long at line %zu\n", line_number);
            continue;
        }
        
        // Store the match
        safe_strcpy((*matches)[*match_count].male_id, male_id, MAX_ID_LENGTH);
        safe_strcpy((*matches)[*match_count].female_id, female_id, MAX_ID_LENGTH);
        
        // Add to vertex tables, marking as in_matching
        if (!add_vertex(male_vertices, male_id, true) || 
            !add_vertex(female_vertices, female_id, true)) {
            fprintf(stderr, "Failed to add vertices at line %zu\n", line_number);
            continue;
        }
        
        (*match_count)++;
        if (*match_count % 1000 == 0) {
            printf("Processed %zu matching pairs\n", *match_count);
        }
    }
    
    printf("Completed processing matching file: %zu valid pairs\n", *match_count);
    fclose(file);
    return true;
}

bool process_graph_file(const char *input_filename, const char *output_filename, 
                       VertexHash *vertices, char prefix) {
    FILE *input = fopen(input_filename, "r");
    FILE *output = fopen(output_filename, "w");
    if (!input || !output) {
        fprintf(stderr, "Failed to open graph files: %s or %s\n", 
                input_filename, output_filename);
        if (input) fclose(input);
        if (output) fclose(output);
        return false;
    }
    
    // Count input lines first
    size_t input_lines = 0;
    char ch;
    while ((ch = fgetc(input)) != EOF) {
        if (ch == '\n') input_lines++;
    }
    if (!feof(input)) input_lines++; // Handle last line without newline
    rewind(input);
    printf("Input file %s has %zu lines\n", input_filename, input_lines);

    // Use line buffering for output
    setvbuf(output, NULL, _IOLBF, 0);
    
    char line[LINE_BUFFER_SIZE];
    size_t line_count = 0;
    size_t edge_count = 0;
    size_t error_count = 0;
    
    // Copy header and verify write
    if (fgets(line, sizeof(line), input)) {
        if (fprintf(output, "%s", line) < 0) {
            fprintf(stderr, "Failed to write header\n");
            goto cleanup;
        }
        line_count++;
    } else {
        fprintf(stderr, "Failed to read header from %s\n", input_filename);
        goto cleanup;
    }
    
    // Process edges
    while (fgets(line, sizeof(line), input)) {
        line_count++;
        
        // Remove newline if present
        char *newline = strchr(line, '\n');
        if (newline) *newline = '\0';
        
        // Skip empty lines
        if (strlen(line) == 0) {
            fprintf(stderr, "Empty line at line %zu\n", line_count);
            continue;
        }

        char from[MAX_ID_LENGTH] = {0};
        char to[MAX_ID_LENGTH] = {0};
        int weight;
        char read_prefix1, read_prefix2;
        char base_from[MAX_BASE_ID_LENGTH] = {0};
        char base_to[MAX_BASE_ID_LENGTH] = {0};
        
        // Parse line with prefixes
        if (sscanf(line, "%c%[^,],%c%[^,],%d", 
                   &read_prefix1, base_from, &read_prefix2, base_to, &weight) != 5 ||
            read_prefix1 != prefix || read_prefix2 != prefix) {
            fprintf(stderr, "Error parsing line %zu: %s\n", line_count, line);
            error_count++;
            continue;
        }
        
        // Verify base ID lengths
        size_t base_from_len = strlen(base_from);
        size_t base_to_len = strlen(base_to);
        
        if (base_from_len >= MAX_BASE_ID_LENGTH || base_to_len >= MAX_BASE_ID_LENGTH) {
            fprintf(stderr, "Base ID too long at line %zu\n", line_count);
            error_count++;
            continue;
        }
        
        // Safely create full IDs (prefix + base)
        from[0] = prefix;
        to[0] = prefix;
        memcpy(from + 1, base_from, base_from_len);
        memcpy(to + 1, base_to, base_to_len);
        from[base_from_len + 1] = '\0';
        to[base_to_len + 1] = '\0';
        
        // Add vertices with prefixes
        add_vertex(vertices, from, false);
        add_vertex(vertices, to, false);
        
        // Mark vertices with their edge directions
        Vertex *v_from = find_vertex(vertices, from);
        Vertex *v_to = find_vertex(vertices, to);
        
        if (v_from) v_from->has_outgoing_edge = true;
        if (v_to) v_to->has_incoming_edge = true;
        
        // Write output with stripped prefixes and verify write
        if (fprintf(output, "%s,%s,%d\n", base_from, base_to, weight) < 0) {
            fprintf(stderr, "Write error at line %zu\n", line_count);
            error_count++;
            continue;
        }
        edge_count++;
        
        if (edge_count % 10000 == 0) {
            printf("Processed %zu edges in %c graph\n", edge_count, prefix);
            fflush(output);
        }
    }
    
    // Final flush
    fflush(output);
    
    printf("\nFile processing summary for %s:\n", input_filename);
    printf("Total input lines: %zu\n", input_lines);
    printf("Lines processed: %zu\n", line_count);
    printf("Edges written: %zu\n", edge_count);
    printf("Parse errors: %zu\n", error_count);
    
cleanup:
    if (input) fclose(input);
    if (output) {
        fflush(output);
        fclose(output);
    }
    return edge_count > 0;
}

void add_self_edges(const char *filename, VertexHash *vh, char prefix) {
    FILE *output = fopen(filename, "a");
    if (!output) {
        fprintf(stderr, "Failed to open file for self-edges: %s\n", filename);
        return;
    }
    
    setvbuf(output, NULL, _IOLBF, 0);  // Line buffering for output

    size_t singleton_count = 0;
    size_t matching_count = 0;
    for (int i = 0; i < HASH_SIZE; i++) {
        Vertex *current = vh->buckets[i];
        while (current) {
            if (current->in_matching) {
                matching_count++;
                // Only add self-edge if vertex has no incoming or outgoing edges
                if (!current->has_outgoing_edge && !current->has_incoming_edge) {
                    const char* base_id = current->id + 1;  // Skip prefix
                    fprintf(output, "%s,%s,1\n", base_id, base_id);
                    fflush(output);  // Ensure immediate write
                    singleton_count++;
                    if (singleton_count % 1000 == 0) {
                        printf("Added %zu self-edges for %c graph\n", singleton_count, prefix);
                    }
                }
            }
            current = current->next;
        }
    }
    
    printf("Found %zu vertices in matching file for %c graph\n", matching_count, prefix);
    printf("Added %zu self-edges for true singleton vertices (no incoming or outgoing edges) in %c graph\n", 
           singleton_count, prefix);
    
    fflush(output);
    fclose(output);
}

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "Usage: %s <male_graph.csv> <female_graph.csv> <matching.csv>\n", argv[0]);
        return 1;
    }

    VertexHash male_vertices = {0};
    VertexHash female_vertices = {0};
    MatchingPair *matches = NULL;
    size_t match_count = 0;
    size_t match_capacity = 0;
    bool success = true;

    printf("Starting graph processing...\n");
    printf("Input files:\n");
    printf("  Male graph:   %s\n", argv[1]);
    printf("  Female graph: %s\n", argv[2]);
    printf("  Matching:     %s\n", argv[3]);

    printf("\nInitializing hash tables...\n");
    if (!init_vertex_hash(&male_vertices) || !init_vertex_hash(&female_vertices)) {
        fprintf(stderr, "Failed to initialize hash tables\n");
        success = false;
        goto cleanup;
    }

    printf("\nProcessing matching file...\n");
    if (!process_matching_file(argv[3], &matches, &match_count, &match_capacity,
                             &male_vertices, &female_vertices)) {
        fprintf(stderr, "Failed to process matching file\n");
        success = false;
        goto cleanup;
    }

    printf("\nProcessing graph files...\n");
    if (!process_graph_file(argv[1], "gm.csv", &male_vertices, 'm') ||
        !process_graph_file(argv[2], "gf.csv", &female_vertices, 'f')) {
        fprintf(stderr, "Failed to process graph files\n");
        success = false;
        goto cleanup;
    }

    printf("\nAdding self-edges for singletons...\n");
    add_self_edges("gm.csv", &male_vertices, 'm');
    add_self_edges("gf.csv", &female_vertices, 'f');

    printf("\nFinal Statistics:\n");
    printf("Total matching pairs: %zu\n", match_count);
    printf("Unique male vertices: %zu\n", male_vertices.count);
    printf("Unique female vertices: %zu\n", female_vertices.count);

cleanup:
    printf("\nCleaning up...\n");
    free_vertex_hash(&male_vertices);
    free_vertex_hash(&female_vertices);
    free(matches);

    printf("Program %s\n", success ? "completed successfully" : "failed");
    return success ? 0 : 1;
}