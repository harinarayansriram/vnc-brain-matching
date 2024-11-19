#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

typedef struct {
    int nodeM1;
    int nodeM2;
    double delta;
} Swap;

typedef struct {
    Swap *data;      // Array of Swaps
    int capacity;    // Maximum capacity of the heap
    int size;        // Current number of elements
} SwapHeap;

// Helper macros for parent and child indices
#define PARENT(i) ((i - 1) / 2)
#define LEFT(i)   (2 * i + 1)
#define RIGHT(i)  (2 * i + 2)

// Function prototypes
SwapHeap *create_swap_heap(int capacity);
void insert_swap(SwapHeap *heap, Swap swap);
bool extract_max(SwapHeap *heap, Swap* best);
void invalidate_swaps(SwapHeap *heap, int node_to_invalidate);
void heapify_down(SwapHeap *heap, int index);
void heapify_up(SwapHeap *heap, int index);

// Create a max heap with given capacity
SwapHeap *create_swap_heap(int capacity) {
    SwapHeap *heap = (SwapHeap *)malloc(sizeof(SwapHeap));
    heap->data = (Swap *)malloc(capacity * sizeof(Swap));
    heap->capacity = capacity;
    heap->size = 0;
    return heap;
}

// Insert a new Swap into the heap
void insert_swap(SwapHeap *heap, Swap swap) {
    if (heap->size < heap->capacity) {
        // Add the new Swap at the end and heapify up
        heap->data[heap->size] = swap;
        heapify_up(heap, heap->size);
        heap->size++;
    } else if (swap.delta > heap->data[0].delta) {
        // Replace the root (smallest delta in max heap) if the new swap is better
        heap->data[0] = swap;
        heapify_down(heap, 0);
    }
}

// Extract the Swap with the highest delta
bool extract_max(SwapHeap *heap, Swap* best) {
    if (heap->size == 0) {
        fprintf(stderr, "Heap is empty!\n");
        return false;
    }
    Swap max_swap = heap->data[0];
    heap->data[0] = heap->data[--heap->size];
    heapify_down(heap, 0);
    *best = max_swap;
    return true;
}

// Invalidate swaps if either nodeM1 or male_node2 matches the given node
void invalidate_swaps(SwapHeap *heap, int node_to_invalidate) {
    for (int i = 0; i < heap->size; ) {
        if (heap->data[i].nodeM1 == node_to_invalidate || 
            heap->data[i].nodeM2 == node_to_invalidate) {
            // Remove this swap by replacing it with the last element and heapify
            heap->data[i] = heap->data[--heap->size];
            heapify_down(heap, i);
        } else {
            i++;
        }
    }
}

// Heapify down to maintain max-heap property
void heapify_down(SwapHeap *heap, int index) {
    int largest = index;
    int left = LEFT(index);
    int right = RIGHT(index);

    if (left < heap->size && heap->data[left].delta > heap->data[largest].delta)
        largest = left;
    if (right < heap->size && heap->data[right].delta > heap->data[largest].delta)
        largest = right;

    if (largest != index) {
        // Swap and continue heapifying
        Swap temp = heap->data[index];
        heap->data[index] = heap->data[largest];
        heap->data[largest] = temp;
        heapify_down(heap, largest);
    }
}

// Heapify up to maintain max-heap property
void heapify_up(SwapHeap *heap, int index) {
    while (index > 0 && heap->data[PARENT(index)].delta < heap->data[index].delta) {
        // Swap with parent
        Swap temp = heap->data[index];
        heap->data[index] = heap->data[PARENT(index)];
        heap->data[PARENT(index)] = temp;
        index = PARENT(index);
    }
}

// Free the heap's memory
void destroy_swap_heap(SwapHeap *heap) {
    free(heap->data);
    free(heap);
}

bool all_zero_delta(SwapHeap *heap){
    for(int i = 0; i < heap->size; i++){
        if(heap->data[i].delta != 0) return false;
    }
    return true;
}