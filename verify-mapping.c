#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <ctype.h>

#define MAX_LINE_LENGTH 1024
#define NUM_NODES 18524

typedef struct {
    int* male_to_female;   // mapping from male to female vertices
    int* female_to_male;   // reverse mapping from female to male vertices
    bool* male_used;       // tracks which male vertices are mapped
    bool* female_used;     // tracks which female vertices are mapped
    int num_mappings;      // number of mappings found
} Mapping;

// Function to create new mapping structure
Mapping* new_mapping() {
    Mapping* m = malloc(sizeof(Mapping));
    if (!m) {
        fprintf(stderr, "Failed to allocate mapping structure\n");
        exit(1);
    }
    m->male_to_female = calloc(NUM_NODES + 1, sizeof(int));
    m->female_to_male = calloc(NUM_NODES + 1, sizeof(int));
    m->male_used = calloc(NUM_NODES + 1, sizeof(bool));
    m->female_used = calloc(NUM_NODES + 1, sizeof(bool));
    if (!m->male_to_female || !m->female_to_male || !m->male_used || !m->female_used) {
        fprintf(stderr, "Failed to allocate mapping arrays\n");
        exit(1);
    }
    m->num_mappings = 0;
    return m;
}

void free_mapping(Mapping* m) {
    if (m) {
        free(m->male_to_female);
        free(m->female_to_male);
        free(m->male_used);
        free(m->female_used);
        free(m);
    }
}

// Helper function to parse vertex IDs
int parse_vertex_id(const char* str) {
    // Skip whitespace
    while (*str && isspace(*str)) str++;
    
    // Skip 'm' or 'f' prefix if present
    if (*str == 'm' || *str == 'f') str++;
    
    // Parse the number
    return atoi(str);
}

// Function to verify header
bool verify_header(const char* header) {
    // List of valid headers (case-insensitive)
    const char* valid_headers[] = {
        "male node id,female node id",
        "male id,female id",
        "maleid,femaleid",
        "male,female",
        "from,to",
        NULL
    };
    
    // Make a lowercase copy of the header for comparison
    char* lower_header = strdup(header);
    for (int i = 0; lower_header[i]; i++) {
        lower_header[i] = tolower(lower_header[i]);
    }
    
    // Remove any whitespace
    char* cleaned = malloc(strlen(lower_header) + 1);
    int j = 0;
    for (int i = 0; lower_header[i]; i++) {
        if (!isspace(lower_header[i])) {
            cleaned[j++] = lower_header[i];
        }
    }
    cleaned[j] = '\0';
    
    // Check against valid headers
    bool valid = false;
    for (int i = 0; valid_headers[i]; i++) {
        char* cleaned_valid = malloc(strlen(valid_headers[i]) + 1);
        j = 0;
        for (int k = 0; valid_headers[i][k]; k++) {
            if (!isspace(valid_headers[i][k])) {
                cleaned_valid[j++] = tolower(valid_headers[i][k]);
            }
        }
        cleaned_valid[j] = '\0';
        
        if (strcmp(cleaned, cleaned_valid) == 0) {
            valid = true;
            free(cleaned_valid);
            break;
        }
        free(cleaned_valid);
    }
    
    free(lower_header);
    free(cleaned);
    return valid;
}

// Load mapping from file
Mapping* load_mapping(const char* filename) {
    FILE* file = fopen(filename, "r");
    if (!file) {
        fprintf(stderr, "Error opening file: %s\n", filename);
        return NULL;
    }
    
    Mapping* m = new_mapping();
    char line[MAX_LINE_LENGTH];
    int line_number = 0;
    
    // Read and verify header
    if (fgets(line, MAX_LINE_LENGTH, file)) {
        // Remove newline if present
        char* newline = strchr(line, '\n');
        if (newline) *newline = '\0';
        
        if (!verify_header(line)) {
            printf("Warning: Unrecognized header format in %s: %s\n", filename, line);
            printf("Continuing anyway, but please verify the file format.\n");
        }
    } else {
        printf("Warning: Empty file: %s\n", filename);
        fclose(file);
        free_mapping(m);
        return NULL;
    }
    
    // Read mappings
    while (fgets(line, MAX_LINE_LENGTH, file)) {
        line_number++;
        char male_str[20], female_str[20];
        
        // Try different formats
        if (strchr(line, ',') != NULL) {  // CSV format
            if (sscanf(line, "%[^,],%s", male_str, female_str) == 2) {
                int male_id = parse_vertex_id(male_str);
                int female_id = parse_vertex_id(female_str);
                
                // Validate IDs
                if (male_id <= 0 || male_id > NUM_NODES || 
                    female_id <= 0 || female_id > NUM_NODES) {
                    printf("Warning: Invalid vertex IDs on line %d: %s", 
                           line_number, line);
                    continue;
                }
                
                m->male_to_female[male_id] = female_id;
                m->female_to_male[female_id] = male_id;
                m->male_used[male_id] = true;
                m->female_used[female_id] = true;
                m->num_mappings++;
            } else {
                printf("Warning: Malformed line %d: %s", line_number, line);
            }
        } else {  // Space-separated format
            if (sscanf(line, "%s %s", male_str, female_str) == 2) {
                int male_id = parse_vertex_id(male_str);
                int female_id = parse_vertex_id(female_str);
                
                // Validate IDs
                if (male_id <= 0 || male_id > NUM_NODES || 
                    female_id <= 0 || female_id > NUM_NODES) {
                    printf("Warning: Invalid vertex IDs on line %d: %s", 
                           line_number, line);
                    continue;
                }
                
                m->male_to_female[male_id] = female_id;
                m->female_to_male[female_id] = male_id;
                m->male_used[male_id] = true;
                m->female_used[female_id] = true;
                m->num_mappings++;
            } else {
                printf("Warning: Malformed line %d: %s", line_number, line);
            }
        }
    }
    
    printf("Successfully loaded %d mappings from %s\n", m->num_mappings, filename);
    
    fclose(file);
    return m;
}

// Function to verify a mapping is valid
bool verify_mapping(Mapping* m) {
    bool valid = true;
    
    // Check for duplicate female assignments
    int* female_count = calloc(NUM_NODES + 1, sizeof(int));
    for (int i = 1; i <= NUM_NODES; i++) {
        if (m->male_used[i]) {
            female_count[m->male_to_female[i]]++;
            if (female_count[m->male_to_female[i]] > 1) {
                printf("ERROR: Female vertex %d (f%d) is assigned to multiple male vertices\n", 
                       m->male_to_female[i], m->male_to_female[i]);
                valid = false;
            }
        }
    }
    free(female_count);
    
    // Check for duplicate male assignments
    int* male_count = calloc(NUM_NODES + 1, sizeof(int));
    for (int i = 1; i <= NUM_NODES; i++) {
        if (m->female_used[i]) {
            male_count[m->female_to_male[i]]++;
            if (male_count[m->female_to_male[i]] > 1) {
                printf("ERROR: Male vertex %d (m%d) is assigned to multiple female vertices\n",
                       m->female_to_male[i], m->female_to_male[i]);
                valid = false;
            }
        }
    }
    free(male_count);
    
    return valid;
}

// Function to analyze differences between two mappings
void analyze_differences(Mapping* initial, Mapping* test) {
    printf("\nAnalyzing differences between mappings:\n");
    printf("----------------------------------------\n");
    
    int differences = 0;
    int missing_initial = 0;
    int missing_test = 0;
    
    // Check for differences and missing mappings
    for (int i = 1; i <= NUM_NODES; i++) {
        if (initial->male_used[i] && !test->male_used[i]) {
            printf("Male vertex %d (m%d) is in initial but missing from test mapping\n", 
                   i, i);
            missing_test++;
        }
        else if (!initial->male_used[i] && test->male_used[i]) {
            printf("Male vertex %d (m%d) is in test but missing from initial mapping\n", 
                   i, i);
            missing_initial++;
        }
        else if (initial->male_used[i] && test->male_used[i]) {
            if (initial->male_to_female[i] != test->male_to_female[i]) {
                printf("Difference: %d (m%d) maps to %d (f%d) in initial, %d (f%d) in test\n",
                       i, i, 
                       initial->male_to_female[i], initial->male_to_female[i],
                       test->male_to_female[i], test->male_to_female[i]);
                differences++;
            }
        }
    }
    
    // Print statistics
    printf("\nSummary Statistics:\n");
    printf("------------------\n");
    printf("Initial mapping count: %d\n", initial->num_mappings);
    printf("Test mapping count: %d\n", test->num_mappings);
    printf("Number of differences: %d\n", differences);
    printf("Vertices in initial but missing from test: %d\n", missing_test);
    printf("Vertices in test but missing from initial: %d\n", missing_initial);
    if (initial->num_mappings > 0) {
        printf("Percentage changed: %.2f%%\n", 
               (double)differences / initial->num_mappings * 100);
    }
    
    // Print histogram of changes
    if (differences > 0) {
        printf("\nChange Distribution:\n");
        printf("-------------------\n");
        int ranges[10] = {0}; // 0-10%, 10-20%, etc.
        for (int i = 1; i <= NUM_NODES; i++) {
            if (initial->male_used[i] && test->male_used[i] &&
                initial->male_to_female[i] != test->male_to_female[i]) {
                
                int range_idx = (i * 10) / NUM_NODES;
                if (range_idx >= 10) range_idx = 9;
                ranges[range_idx]++;
            }
        }
        
        for (int i = 0; i < 10; i++) {
            printf("%3d-%3d%%: ", i*10, (i+1)*10);
            for (int j = 0; j < ranges[i] * 50 / differences; j++) printf("*");
            printf(" (%d)\n", ranges[i]);
        }
    }
}

int main(int argc, char* argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <initial_mapping.csv> <test_mapping.csv>\n", argv[0]);
        return 1;
    }
    
    // Load mappings
    printf("Loading initial mapping from %s\n", argv[1]);
    Mapping* initial = load_mapping(argv[1]);
    if (!initial) {
        fprintf(stderr, "Failed to load initial mapping\n");
        return 1;
    }
    
    printf("Loading test mapping from %s\n", argv[2]);
    Mapping* test = load_mapping(argv[2]);
    if (!test) {
        fprintf(stderr, "Failed to load test mapping\n");
        free_mapping(initial);
        return 1;
    }
    
    // Verify both mappings are valid
    printf("\nVerifying initial mapping...\n");
    bool initial_valid = verify_mapping(initial);
    printf("Initial mapping is %s\n", initial_valid ? "valid" : "invalid");
    
    printf("\nVerifying test mapping...\n");
    bool test_valid = verify_mapping(test);
    printf("Test mapping is %s\n", test_valid ? "valid" : "invalid");
    
    // If both are valid, analyze differences
    if (initial_valid && test_valid) {
        analyze_differences(initial, test);
    }
    
    // Cleanup
    free_mapping(initial);
    free_mapping(test);
    
    return 0;
}