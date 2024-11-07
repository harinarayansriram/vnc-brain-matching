package main

import (
    "container/heap"
)

// // Swap represents a swap operation between two nodes
// type Swap struct {
//     MaleNode1   int
//     MaleNode2 int
//     Delta        int
// }

// // internal version of Swap that includes heap index
// type swapWithIndex struct {
//     Swap
//     index int
// }

// // SwapHeap implements heap.Interface and holds Swaps with indexing
// type SwapHeap struct {
//     items         []swapWithIndex
//     maxSize       int
//     maleIndex1     map[int][]int   // maps male ID to slice of heap indices
//     maleIndex2   map[int][]int   // maps female ID to slice of heap indices
// }

// // NewBoundedMaxHeap creates a new bounded max heap with the specified maximum size
// func NewBoundedMaxHeap(maxSize int) *SwapHeap {
//     return &SwapHeap{
//         items:       make([]swapWithIndex, 0, maxSize),
//         maxSize:     maxSize,
//         maleIndex1:   make(map[int][]int),
//         maleIndex2: make(map[int][]int),
//     }
// }

// // Len implements sort.Interface
// func (h *SwapHeap) Len() int { return len(h.items) }

// // Less implements sort.Interface
// func (h *SwapHeap) Less(i, j int) bool {
//     return h.items[i].Delta > h.items[j].Delta
// }

// // Swap implements sort.Interface
// func (h *SwapHeap) Swap(i, j int) {
//     h.items[i], h.items[j] = h.items[j], h.items[i]
//     h.items[i].index = i
//     h.items[j].index = j
// }

// // Push implements heap.Interface
// func (h *SwapHeap) Push(x interface{}) {
//     n := len(h.items)
//     item := x.(swapWithIndex)
//     item.index = n
//     h.items = append(h.items, item)
    
//     // Update indices
//     h.maleIndex1[item.MaleNode1] = append(h.maleIndex1[item.MaleNode1], n)
//     h.maleIndex2[item.MaleNode2] = append(h.maleIndex2[item.MaleNode2], n)
// }

// // Pop implements heap.Interface
// func (h *SwapHeap) Pop() interface{} {
//     old := h.items
//     n := len(old)
//     item := old[n-1]
//     h.items = old[0 : n-1]
    
//     // Remove from indices
//     h.removeFromIndices(item.MaleNode1, item.MaleNode2, item.index)
//     return item.Swap  // Return just the Swap part
// }

// func (h *SwapHeap) removeFromIndices(maleID, femaleID, index int) {
//     h.removeIndex(h.maleIndex1, maleID, index)
//     h.removeIndex(h.maleIndex2, femaleID, index)
// }

// func (h *SwapHeap) removeIndex(indices map[int][]int, id, index int) {
//     idxList := indices[id]
//     for i, idx := range idxList {
//         if idx == index {
//             lastIdx := len(idxList) - 1
//             idxList[i] = idxList[lastIdx]
//             indices[id] = idxList[:lastIdx]
//             if len(indices[id]) == 0 {
//                 delete(indices, id)
//             }
//             return
//         }
//     }
// }

// // Insert adds a new swap to the heap
// func (h *SwapHeap) Insert(swap Swap) bool {
//     n := len(h.items)
    
//     if n < h.maxSize {
//         heap.Push(h, swapWithIndex{Swap: swap})
//         return true
//     }
    
//     if swap.Delta <= h.items[n-1].Delta {
//         return false
//     }
    
//     // Remove old indices before replacing
//     oldItem := h.items[n-1]
//     h.removeFromIndices(oldItem.MaleNode1, oldItem.MaleNode2, oldItem.index)
    
//     // Add new swap and update indices
//     h.items[n-1] = swapWithIndex{Swap: swap, index: n-1}
//     h.maleIndex1[swap.MaleNode1] = append(h.maleIndex1[swap.MaleNode1], n-1)
//     h.maleIndex2[swap.MaleNode2] = append(h.maleIndex2[swap.MaleNode2], n-1)
    
//     heap.Fix(h, n-1)
//     return true
// }

// // UpdateDeltasByMaleID updates all swaps with the given male ID
// func (h *SwapHeap) UpdateDeltasByMale1(maleID int, newDelta int) {
//     indices := h.maleIndex1[maleID]
//     for _, idx := range indices {
//         h.items[idx].Delta = newDelta
//         heap.Fix(h, idx)
//     }
// }

// // UpdateDeltasByFemaleID updates all swaps with the given female ID
// func (h *SwapHeap) UpdateDeltasByMale2(femaleID int, newDelta int) {
//     indices := h.maleIndex2[femaleID]
//     for _, idx := range indices {
//         h.items[idx].Delta = newDelta
//         heap.Fix(h, idx)
//     }
// }

// // ExtractMax removes and returns the swap with the maximum delta
// func (h *SwapHeap) ExtractMax() (Swap, bool) {
//     if len(h.items) == 0 {
//         return Swap{}, false
//     }
//     return heap.Pop(h).(Swap), true
// }

// // ExtractN removes and returns up to n maximum elements
// func (h *SwapHeap) ExtractN(n int) []Swap {
//     if n <= 0 {
//         return nil
//     }
    
//     result := make([]Swap, 0, n)
//     for i := 0; i < n && len(h.items) > 0; i++ {
//         swap := heap.Pop(h).(Swap)
//         result = append(result, swap)
//     }
//     return result
// }

// // InsertMany efficiently inserts multiple swaps
// func (h *SwapHeap) InsertMany(swaps []Swap) {
//     // If heap is empty, we can optimize the initial insertion
//     if len(h.items) == 0 {
//         // Copy only up to maxSize elements
//         toCopy := len(swaps)
//         if toCopy > h.maxSize {
//             toCopy = h.maxSize
//         }
        
//         // Pre-allocate indices capacity
//         for i := 0; i < toCopy; i++ {
//             swap := swaps[i]
//             h.maleIndex1[swap.MaleNode1] = make([]int, 0, 4)   // Assuming average of 4 swaps per ID
//             h.maleIndex2[swap.MaleNode2] = make([]int, 0, 4)
//         }
        
//         // Convert to internal format and add indices
//         h.items = make([]swapWithIndex, toCopy)
//         for i := 0; i < toCopy; i++ {
//             h.items[i] = swapWithIndex{Swap: swaps[i], index: i}
//             h.maleIndex1[swaps[i].MaleNode1] = append(h.maleIndex1[swaps[i].MaleNode1], i)
//             h.maleIndex2[swaps[i].MaleNode2] = append(h.maleIndex2[swaps[i].MaleNode2], i)
//         }
        
//         heap.Init(h)
//         return
//     }

//     // Otherwise insert one by one
//     for _, swap := range swaps {
//         h.Insert(swap)
//     }
// }

// package heap

// import (
//     "container/heap"
// )

// Swap represents a swap operation between two nodes
type Swap struct {
    MaleNode1   int
    MaleNode2 int
    Delta        int
}

// SwapHeap implements heap.Interface and holds Swaps
type SwapHeap struct {
    items   []Swap
    maxSize int
}

// NewBoundedMaxHeap creates a new bounded max heap with the specified maximum size
func NewBoundedMaxHeap(maxSize int) *SwapHeap {
    return &SwapHeap{
        items:   make([]Swap, 0, maxSize),
        maxSize: maxSize,
    }
}

// Len implements sort.Interface
func (h *SwapHeap) Len() int { return len(h.items) }

// Less implements sort.Interface
func (h *SwapHeap) Less(i, j int) bool {
    return h.items[i].Delta > h.items[j].Delta
}

// Swap implements sort.Interface
func (h *SwapHeap) Swap(i, j int) {
    h.items[i], h.items[j] = h.items[j], h.items[i]
}

// Push implements heap.Interface
func (h *SwapHeap) Push(x interface{}) {
    h.items = append(h.items, x.(Swap))
}

// Pop implements heap.Interface
func (h *SwapHeap) Pop() interface{} {
    old := h.items
    n := len(old)
    item := old[n-1]
    h.items = old[0 : n-1]
    return item
}

// Insert adds a new swap to the heap
func (h *SwapHeap) Insert(swap Swap) bool {
    n := len(h.items)
    
    if n < h.maxSize {
        heap.Push(h, swap)
        return true
    }
    
    if swap.Delta <= h.items[n-1].Delta {
        return false
    }
    
    h.items[n-1] = swap
    heap.Fix(h, n-1)
    return true
}

// InsertMany efficiently inserts multiple swaps
func (h *SwapHeap) InsertMany(swaps []Swap) {
    for _, swap := range swaps {
        h.Insert(swap)
    }
}

// RemoveByMale1 removes all swaps with the given MaleNode1 ID
func (h *SwapHeap) RemoveByMale1(maleID1 int) {
    // Filter items to exclude those with the specified MaleNode1
    filteredItems := h.items[:0] // Reuse the existing slice with zeroed length
    for _, item := range h.items {
        if item.MaleNode1 != maleID1 {
            filteredItems = append(filteredItems, item)
        }
    }
    
    // Reassign the filtered items and rebuild the heap
    h.items = filteredItems
    heap.Init(h)
}

func (h *SwapHeap) RemoveByMale1AndMale2(maleID_1, maleID_2 int) {
	filteredItems := h.items[:0] // Reuse the existing slice with zeroed length
	for _, item := range h.items {
		if item.MaleNode1 != maleID_1 && item.MaleNode1 != maleID_2 && item.MaleNode2 != maleID_1 && item.MaleNode2 != maleID_2 {
			filteredItems = append(filteredItems, item)
		}
	}

	// Reassign the filtered items and rebuild the heap
	h.items = filteredItems
	heap.Init(h)
}

// RemoveByMale2 removes all swaps with the given MaleNode2 ID
func (h *SwapHeap) RemoveByMale2(maleID2 int) {
    // Filter items to exclude those with the specified MaleNode2
    filteredItems := h.items[:0] // Reuse the existing slice with zeroed length
    for _, item := range h.items {
        if item.MaleNode2 != maleID2 {
            filteredItems = append(filteredItems, item)
        }
    }
    
    // Reassign the filtered items and rebuild the heap
    h.items = filteredItems
    heap.Init(h)
}


// ExtractMax removes and returns the swap with the maximum delta
func (h *SwapHeap) ExtractMax() (Swap, bool) {
    if len(h.items) == 0 {
        return Swap{}, false
    }
    return heap.Pop(h).(Swap), true
}

// ExtractN removes and returns up to n maximum elements
func (h *SwapHeap) ExtractN(n int) []Swap {
    if n <= 0 {
        return nil
    }
    
    result := make([]Swap, 0, n)
    for i := 0; i < n && len(h.items) > 0; i++ {
        swap := heap.Pop(h).(Swap)
        result = append(result, swap)
    }
    return result
}