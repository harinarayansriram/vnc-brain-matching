#pragma once

#include <stdbool.h>

// Forward declarations of opaque structures
typedef struct SwapHeap SwapHeap;

// Swap structure definition
typedef struct {
    int nodeM1;
    int nodeM2;
    int delta;
    int minHeapIndex;  // Position in min heap
    int maxHeapIndex;  // Position in max heap
} Swap;

/**
 * Creates a new swap heap with the specified capacity.
 * Implementation uses a dual-heap structure to provide O(log n)
 * operations for both minimum and maximum element access.
 * 
 * @param capacity Maximum number of swaps the heap can hold
 * @return Pointer to the created heap, or NULL if allocation fails
 */
SwapHeap* create_swap_heap(int capacity);

/**
 * Inserts a new swap into the heap. If the heap is full but the new swap's
 * delta is greater than the minimum delta in the heap, the minimum element
 * will be evicted and the new swap will be inserted. Operation is O(log n).
 * 
 * @param heap Pointer to the swap heap
 * @param nodeM1 First node of the swap
 * @param nodeM2 Second node of the swap
 * @param delta Priority value for the swap
 * @return true if insertion successful (either direct or via eviction),
 *         false if heap is full and new delta is not better than minimum
 */
bool insert_swap(SwapHeap* heap, int nodeM1, int nodeM2, int delta);

/**
 * Extracts the swap with maximum delta from the heap. Operation is O(log n).
 * 
 * @param heap Pointer to the swap heap
 * @param result Pointer to store the extracted swap
 * @return true if extraction successful, false if heap is empty
 */
bool extract_max(SwapHeap* heap, Swap* result);

/**
 * Invalidates all swaps that contain the specified node value
 * as either nodeM1 or nodeM2. Operation is O(n log n) in worst case
 * where all elements need to be invalidated.
 * 
 * @param heap Pointer to the swap heap
 * @param nodeValue Node value to invalidate
 * @return Number of swaps that were invalidated
 */
int invalidate_swaps(SwapHeap* heap, int nodeValue);

/**
 * Checks if all delta values in the heap are zero.
 * 
 * @param heap Pointer to the swap heap
 * @return true if all delta values are zero, false otherwise
 */
bool all_zero_delta(SwapHeap* heap);
/**
 * Frees all memory associated with the swap heap.
 * 
 * @param heap Pointer to the swap heap to destroy
 */
void destroy_swap_heap(SwapHeap* heap);