#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>    

typedef struct {
    int nodeM1;
    int nodeM2;
    int delta;
    int minHeapIndex;
    int maxHeapIndex;
} Swap;

typedef struct {
    Swap* swaps;       // Array of swap elements
    int* minHeapIdx;   // Array of indices for min heap
    int* maxHeapIdx;   // Array of indices for max heap
    int capacity;
    int size;
} SwapHeap;

//TODO: Bugfixes in the heap code, still not correctly retreiving the max element for some reason

// Helper functions for heap operations
static inline int parent(int i) { return (i - 1) / 2; }
static inline int leftChild(int i) { return 2 * i + 1; }
static inline int rightChild(int i) { return 2 * i + 2; }

SwapHeap* create_swap_heap(int capacity) {
    SwapHeap* heap = (SwapHeap*)malloc(sizeof(SwapHeap));
    heap->swaps = (Swap*)malloc(sizeof(Swap) * capacity);
    heap->minHeapIdx = (int*)malloc(sizeof(int) * capacity);
    heap->maxHeapIdx = (int*)malloc(sizeof(int) * capacity);
    heap->capacity = capacity;
    heap->size = 0;
    return heap;
}

static void swap_min_heap_indices(SwapHeap* heap, int i, int j) {
    int temp = heap->minHeapIdx[i];
    heap->minHeapIdx[i] = heap->minHeapIdx[j];
    heap->minHeapIdx[j] = temp;
    
    heap->swaps[heap->minHeapIdx[i]].minHeapIndex = i;
    heap->swaps[heap->minHeapIdx[j]].minHeapIndex = j;
}

static void swap_max_heap_indices(SwapHeap* heap, int i, int j) {
    int temp = heap->maxHeapIdx[i];
    heap->maxHeapIdx[i] = heap->maxHeapIdx[j];
    heap->maxHeapIdx[j] = temp;
    
    heap->swaps[heap->maxHeapIdx[i]].maxHeapIndex = i;
    heap->swaps[heap->maxHeapIdx[j]].maxHeapIndex = j;
}

static void heapify_up_min(SwapHeap* heap, int index) {
    while (index > 0) {
        int p = parent(index);
        if (heap->swaps[heap->minHeapIdx[index]].delta < 
            heap->swaps[heap->minHeapIdx[p]].delta) {
            swap_min_heap_indices(heap, index, p);
            index = p;
        } else {
            break;
        }
    }
}

static void heapify_down_min(SwapHeap* heap, int index) {
    int minIndex = index;
    int size = heap->size;
    
    while (true) {
        int left = leftChild(index);
        int right = rightChild(index);

        if (left < size && 
            heap->swaps[heap->minHeapIdx[left]].delta < 
            heap->swaps[heap->minHeapIdx[minIndex]].delta) {
            minIndex = left;
        }
        
        if (right < size && 
            heap->swaps[heap->minHeapIdx[right]].delta < 
            heap->swaps[heap->minHeapIdx[minIndex]].delta) {
            minIndex = right;
        }

        if (minIndex != index) {
            swap_min_heap_indices(heap, index, minIndex);
            index = minIndex;
        } else {
            break;
        }
    }
}

static void heapify_up_max(SwapHeap* heap, int index) {
    while (index > 0) {
        int p = parent(index);
        int pSwap = heap->maxHeapIdx[p];
        int indexSwap = heap->maxHeapIdx[index];
        if (heap->swaps[pSwap].delta < heap->swaps[indexSwap].delta) {
            swap_max_heap_indices(heap, index, p);
            index = p;
        } else {
            break;
        }
    }
}

static void heapify_down_max(SwapHeap* heap, int index) {
    int maxIndex = index;
    int size = heap->size;
    
    while (true) {
        int left = leftChild(index);
        int right = rightChild(index);
        int maxSwap = heap->maxHeapIdx[maxIndex];

        if (left < size) {
            int leftSwap = heap->maxHeapIdx[left];
            if (heap->swaps[leftSwap].delta > heap->swaps[maxSwap].delta) {
                maxIndex = left;
                maxSwap = leftSwap;
            }
        }
        
        if (right < size) {
            int rightSwap = heap->maxHeapIdx[right];
            if (heap->swaps[rightSwap].delta > heap->swaps[maxSwap].delta) {
                maxIndex = right;
            }
        }

        if (maxIndex != index) {
            swap_max_heap_indices(heap, index, maxIndex);
            index = maxIndex;
        } else {
            break;
        }
    }
}

static void remove_from_heaps(SwapHeap* heap, int swapIndex) {
    // Get indices in both heaps for the element we're removing
    int minIdx = heap->swaps[swapIndex].minHeapIndex;
    int maxIdx = heap->swaps[swapIndex].maxHeapIndex;
    
    // Get the last element's indices
    int lastElement = heap->size - 1;
    int lastSwapIdx = heap->minHeapIdx[lastElement];
    
    // If we're not removing the last element
    if (swapIndex != lastSwapIdx) {
        // Copy the last swap's data to the removed position
        heap->swaps[swapIndex] = heap->swaps[lastSwapIdx];
        
        // Get the last element's positions in both heaps
        int lastMinIdx = heap->swaps[lastSwapIdx].minHeapIndex;  // This should be lastElement
        int lastMaxIdx = heap->swaps[lastSwapIdx].maxHeapIndex;
        
        // Update the moved element's positions in both heaps
        heap->minHeapIdx[minIdx] = swapIndex;
        heap->maxHeapIdx[maxIdx] = swapIndex;
        
        // Update the moved element's index references
        heap->swaps[swapIndex].minHeapIndex = minIdx;
        heap->swaps[swapIndex].maxHeapIndex = maxIdx;
        
        // Heapify from both positions where elements were affected
        heapify_up_min(heap, minIdx);
        heapify_down_min(heap, minIdx);
        heapify_up_max(heap, maxIdx);
        heapify_down_max(heap, maxIdx);
    }
    
    // Reduce size before returning
    heap->size--;
}
bool extract_max(SwapHeap* heap, Swap* result) {
    if (heap->size == 0) {
        return false;
    }

    // Get the max element and copy it to result
    int maxSwapIdx = heap->maxHeapIdx[0];
    *result = heap->swaps[maxSwapIdx];
    
    // Remove the element from both heaps
    remove_from_heaps(heap, maxSwapIdx);
    heap->size--;
    
    return true;
}

bool insert_swap(SwapHeap* heap, int nodeM1, int nodeM2, int delta) {
    if (delta < 0) {
        return false;
    }

    if (heap->size < heap->capacity) {
        // Regular insertion
        int idx = heap->size;
        Swap newSwap = {nodeM1, nodeM2, delta, idx, idx};
        heap->swaps[idx] = newSwap;
        
        heap->minHeapIdx[idx] = idx;
        heap->maxHeapIdx[idx] = idx;
        
        heapify_up_min(heap, idx);
        heapify_up_max(heap, idx);
        
        heap->size++;
        return true;
    } else {
        // Check if better than minimum
        int minSwapIdx = heap->minHeapIdx[0];
        
        // Find this swap's position in the max heap
        int maxHeapPos = -1;
        for (int i = 0; i < heap->size; i++) {
            if (heap->maxHeapIdx[i] == minSwapIdx) {
                maxHeapPos = i;
                break;
            }
        }
        
        if (delta > heap->swaps[minSwapIdx].delta && maxHeapPos != -1) {
            // Replace minimum element
            heap->swaps[minSwapIdx].nodeM1 = nodeM1;
            heap->swaps[minSwapIdx].nodeM2 = nodeM2;
            heap->swaps[minSwapIdx].delta = delta;
            
            // Heapify both heaps
            heapify_down_min(heap, 0);
            heapify_up_max(heap, maxHeapPos);
            heapify_down_max(heap, maxHeapPos);
            return true;
        }
    }
    return false;
}

int invalidate_swaps(SwapHeap* heap, int nodeValue) {
    int invalidated = 0;
    
    // We need to scan from the end to avoid issues with shifting indices
    for (int i = heap->size - 1; i >= 0; i--) {
        if (heap->swaps[i].nodeM1 == nodeValue || 
            heap->swaps[i].nodeM2 == nodeValue) {
            remove_from_heaps(heap, i);
            invalidated++;
        }
    }
    
    heap->size -= invalidated;
    return invalidated;
}

bool all_zero_delta(SwapHeap* heap) {
    for (int i = 0; i < heap->size; i++) {
        if (heap->swaps[i].delta != 0) {
            printf("[INFO] Heap contains swap (%d, %d) with positive delta %d at index %d\n", 
                   heap->swaps[i].nodeM1, heap->swaps[i].nodeM2, heap->swaps[i].delta, i);
            printf("[INFO] Heap max index is %d, which corresponds to a swap delta of %d\n", heap->maxHeapIdx[0], heap->swaps[heap->maxHeapIdx[0]].delta);
            return false;
        }
    }
    return true;
}

void destroy_swap_heap(SwapHeap* heap) {
    free(heap->swaps);
    free(heap->minHeapIdx);
    free(heap->maxHeapIdx);
    free(heap);
}