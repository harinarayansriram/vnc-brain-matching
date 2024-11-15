package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"os"
	"strconv"
)

const updateInterval int = 20

const nodeCount int = 18524

const heapCapacity int = 5000

type AdjacencyMetricsEdges struct {
	adjMatrix    []int16
	metrics      [][]int
	forwardEdges map[int]map[int]int
	reverseEdges map[int]map[int]int
}

func createAdjacencyMatrix(filename string) AdjacencyMetricsEdges {
	file, err := os.Open(filename)
	if err != nil {
		panic(err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	// Skip header
	_, err = reader.Read()
	if err != nil {
		panic(err)
	}

	adjMatrix := make([]int16, nodeCount*nodeCount)
	metrics := make([][]int, nodeCount)
	forwardEdges := make(map[int]map[int]int)
	reverseEdges := make(map[int]map[int]int)

	for {
		record, err := reader.Read()
		if err != nil {
			break
		}

		weight, err := strconv.Atoi(record[2])
		if err != nil {
			panic(err)
		}

		from, err := strconv.Atoi(record[0])
		if err != nil {
			panic(err)
		}
		from -= 1

		to, err := strconv.Atoi(record[1])
		if err != nil {
			panic(err)
		}
		to -= 1

		adjMatrix[from*nodeCount+to] = int16(weight)

		if forwardEdges[from] == nil {
			forwardEdges[from] = make(map[int]int)
		}
		forwardEdges[from][to] = weight

		if reverseEdges[to] == nil {
			reverseEdges[to] = make(map[int]int)
		}
		reverseEdges[to][from] = weight

		if metrics[from] == nil {
			metrics[from] = make([]int, 3)
		}

		if metrics[to] == nil {
			metrics[to] = make([]int, 3)
		}
		// total weight
		metrics[from][0] += weight
		metrics[to][0] += weight

		// out degree
		metrics[from][1]++

		// in degree
		metrics[to][2]++

	}
	return AdjacencyMetricsEdges{adjMatrix, metrics, forwardEdges, reverseEdges}
}

// Calculates alignment score for current mapping
func calculateAlignmentScore(adjMatrixM []int16, adjMatrixF []int16, forwardEdgesM map[int]map[int]int, mapping map[int]int) int {
	var score int

	for srcM := 0; srcM < nodeCount; srcM++ {
		for dstM, weightM := range forwardEdgesM[srcM] {
			srcF := mapping[srcM]
			dstF := mapping[int(dstM)]
			score += min(weightM, int(adjMatrixF[srcF*nodeCount+dstF]))
		}
	}
	return score
}

// Loads benchmark mapping from CSV
func loadBenchmarkMapping(filename string) (map[int]int, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	// Skip header
	_, err = reader.Read()
	if err != nil {
		return nil, err
	}

	mapping := make(map[int]int)

	for {
		record, err := reader.Read()
		if err != nil {
			break
		}
		from, err := strconv.Atoi(record[0][1:])
		if err != nil {
			panic(err)
		}
		to, err := strconv.Atoi(record[1][1:])
		if err != nil {
			panic(err)
		}
		mapping[from-1] = to - 1
	}

	return mapping, nil
}

func loadScoreLookup(filename string, heapCapacity int) ([]int16, *SwapHeap, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	scanner := reader

	adjMatrix := make([]int16, nodeCount*nodeCount)
	heap := NewBoundedMaxHeap(heapCapacity)

	for i := 0; i < nodeCount; i++ {
		row, err := scanner.Read()
		if err != nil {
			return nil, nil, err
		}
		if i%1000 == 0 {
			log.Println("Loaded", i, "rows")
		}
		//read the row
		// fmt.Println("Text: ", text)
		// row := strings.Split(text, ",")
		swaps := make([]Swap, 0, 32)
		for j := 0; j < nodeCount; j++ {
			delta, err := strconv.Atoi(row[j])
			if err != nil {
				log.Println("Erroring row index:", i, "column index:", j)
				log.Println(row)
				return nil, nil, err
			}
			adjMatrix[i*nodeCount+j] = int16(delta)
			if delta >= 0 {
				swaps = append(swaps, Swap{i, j, delta})
			}
		}
		heap.InsertMany(swaps)
	}
	return adjMatrix, heap, nil
}

// Calculate change in alignment score for swapping two nodes
func calculateSwapDelta(graphM AdjacencyMetricsEdges, graphF AdjacencyMetricsEdges, mapping map[int]int, nodeM1, nodeM2 int) int {
	nodeF1 := mapping[nodeM1]
	nodeF2 := mapping[nodeM2]
	var delta int

	// Remove old contributions

	for node := range graphM.forwardEdges[nodeM1] {
		if int(node) == nodeM2 {
			continue
		}
		// Outgoing edges from nodeM1
		weightM := graphM.adjMatrix[nodeM1*nodeCount+node]

		oldF := min(weightM, graphF.adjMatrix[nodeF1*nodeCount+mapping[node]])
		newF := min(weightM, graphF.adjMatrix[nodeF2*nodeCount+mapping[node]])
		delta += int(newF - oldF)
	}

	for node := range graphM.forwardEdges[nodeM2] {
		if node == nodeM1 {
			continue
		}
		// Outgoing edges from nodeM2
		weightM := graphM.adjMatrix[nodeM2*nodeCount+node]

		oldF := min(weightM, graphF.adjMatrix[nodeF2*nodeCount+mapping[node]])
		newF := min(weightM, graphF.adjMatrix[nodeF1*nodeCount+mapping[node]])
		delta += int(newF - oldF)
	}

	for node := range graphM.reverseEdges[nodeM1] {
		if node == nodeM2 {
			continue
		}
		// Incoming edges to nodeM1
		weightM := graphM.adjMatrix[node*nodeCount+nodeM1]

		oldF := min(weightM, graphF.adjMatrix[mapping[node]*nodeCount+nodeF1])
		newF := min(weightM, graphF.adjMatrix[mapping[node]*nodeCount+nodeF2])
		delta += int(newF - oldF)
	}

	for node := range graphM.reverseEdges[nodeM2] {
		if node == nodeM1 {
			continue
		}
		// Incoming edges to nodeM2
		weightM := graphM.adjMatrix[node*nodeCount+nodeM2]

		oldF := min(weightM, graphF.adjMatrix[mapping[node]*nodeCount+nodeF2])
		newF := min(weightM, graphF.adjMatrix[mapping[node]*nodeCount+nodeF1])
		delta += int(newF - oldF)
	}

	// 3. Edges between nodeM1 and nodeM2
	weightM12 := graphM.adjMatrix[nodeM1*nodeCount+nodeM2]
	weightM21 := graphM.adjMatrix[nodeM2*nodeCount+nodeM1]
	if weightM12 > 0 {
		oldF := min(weightM12, graphF.adjMatrix[nodeF1*nodeCount+nodeF2])
		newF := min(weightM12, graphF.adjMatrix[nodeF2*nodeCount+nodeF1])
		delta += int(newF - oldF)
	}
	if weightM21 > 0 {
		oldF := min(weightM21, graphF.adjMatrix[nodeF2*nodeCount+nodeF1])
		newF := min(weightM21, graphF.adjMatrix[nodeF1*nodeCount+nodeF2])
		delta += int(newF - oldF)
	}

	return delta
}

func writeMapping(filename string, mapping map[int]int) {
	file, err := os.Create(filename)
	if err != nil {
		panic(err)
	}
	defer file.Close()

	wr := csv.NewWriter(file)
	defer wr.Flush()
	header := []string{"Male Node ID", "Female Node ID"}
	wr.Write(header)

	for male_node_id, female_node_id := range mapping {
		wr.Write([]string{"m" + strconv.Itoa(male_node_id+1), "f" + strconv.Itoa(female_node_id+1)})
	}

	wr.Flush()
}

func saveSwapMatrix(filename string, swapMatrix []int16) {
	log.Println("Saving swap matrix...")
	file, err := os.Create(filename)
	if err != nil {
		panic(err)
	}
	defer file.Close()

	wr := csv.NewWriter(file)
	defer wr.Flush()

	for i := 0; i < nodeCount; i++ {
		swaps := make([]string, nodeCount)
		for j := 0; j < nodeCount; j++ {
			swaps[j] = strconv.Itoa(int(swapMatrix[i*nodeCount+j]))
		}
		wr.Write(swaps)
		wr.Flush()
	}
}

// Optimizes mapping using local search with node similarity heuristics
func optimizeMapping(graphM, graphF AdjacencyMetricsEdges, initialMapping map[int]int, scoreLookup []int16, swapHeap *SwapHeap, outPath string, matrixPath string) map[int]int {
	currentMapping := make(map[int]int)
	for k, v := range initialMapping {
		currentMapping[k] = v
	}

	currentScore := calculateAlignmentScore(graphM.adjMatrix, graphF.adjMatrix, graphM.forwardEdges, currentMapping)

	for i := 0; i < 5000; i++ {
		log.Println("Iteration: ", i, "Score: ", currentScore)
		if swapHeap.items == nil || len(swapHeap.items) == 0 {
			saveSwapMatrix(matrixPath, scoreLookup)
			writeMapping(outPath, currentMapping)
			log.Println("Error: No swaps found!")
			return currentMapping
		}

		if i%100 == 0 && i != 0 {
			log.Println("Saving Iteration: ", i, "Score: ", currentScore)
			saveSwapMatrix(matrixPath, scoreLookup)
			writeMapping(outPath, currentMapping)
		}

		bestSwap, ok := swapHeap.ExtractMax()
		if !ok {
			saveSwapMatrix(matrixPath, scoreLookup)
			writeMapping(outPath, currentMapping)
			log.Println("Extract max failed")
			return currentMapping
		}

		nodeM1, nodeM2, swapDelta := bestSwap.MaleNode1, bestSwap.MaleNode2, bestSwap.Delta

		currentMapping[nodeM1], currentMapping[nodeM2] = currentMapping[nodeM2], currentMapping[nodeM1]
		currentScore += swapDelta

		// scoreLookup[nodeM1*nodeCount+nodeM2] = -int16(swapDelta)
		// scoreLookup[nodeM2*nodeCount+nodeM1] = -int16(swapDelta)

		// swapHeap.RemoveByMale1(nodeM1)
		// swapHeap.RemoveByMale1(nodeM2)
		// swapHeap.RemoveByMale2(nodeM1)
		// swapHeap.RemoveByMale2(nodeM2)
		swapHeap.RemoveByMale1AndMale2(nodeM1, nodeM2)

		//Update every node in the swap lookup that swapped with either nodeM1 or nodeM2
		updatedSwaps := make([]Swap, 0, 32)
		for node := 0; node < nodeCount; node++ {
			// if node == nodeM1 || node == nodeM2 {
			// 	continue
			// }

			delta := int16(calculateSwapDelta(graphM, graphF, currentMapping, node, nodeM1))
			scoreLookup[node*nodeCount+nodeM1] = delta
			scoreLookup[nodeM1*nodeCount+node] = delta

			if delta >= 0 {
				updatedSwaps = append(updatedSwaps, Swap{node, nodeM1, int(delta)})
			}

			delta = int16(calculateSwapDelta(graphM, graphF, currentMapping, node, nodeM2))
			scoreLookup[node*nodeCount+nodeM2] = delta
			scoreLookup[nodeM2*nodeCount+node] = delta

			if delta >= 0 {
				updatedSwaps = append(updatedSwaps, Swap{node, nodeM2, int(delta)})
			}
		}

		swapHeap.InsertMany(updatedSwaps)
	}

	saveSwapMatrix(matrixPath, scoreLookup)

	return currentMapping
}

func main() {
	if len(os.Args) < 7 {
		fmt.Println("Usage:", os.Args[0], "<male graph> <female graph> <in mapping> <score lookup> <out mapping> <out matrix>")
		os.Exit(1)
	}
	// Load graphs
	graphM := createAdjacencyMatrix(os.Args[1])
	log.Println("Loaded in male graph")

	graphF := createAdjacencyMatrix(os.Args[2])
	log.Println("Loaded in female graph")

	// Load benchmark mapping
	benchmark, err := loadBenchmarkMapping(os.Args[3])
	if err != nil {
		log.Fatal("Error loading benchmark mapping:", err)
	}
	log.Println("Loaded in benchmark mapping")

	// Load score lookup
	scoreLookup, swapHeap, err := loadScoreLookup(os.Args[4], heapCapacity)
	if err != nil {
		log.Fatal("Error loading score lookup/creating swap heap: ", err)
	}
	log.Println("Loaded in score lookup and swap heap")

	// Calculate initial score
	initialScore := calculateAlignmentScore(graphM.adjMatrix, graphF.adjMatrix, graphM.forwardEdges, benchmark)
	log.Printf("Initial alignment score: %d\n", initialScore)

	log.Println("Starting optimization...")

	// Optimize mapping
	optimizedMapping := optimizeMapping(graphM, graphF, benchmark, scoreLookup, swapHeap, os.Args[5], os.Args[6])
	optimizedScore := calculateAlignmentScore(graphM.adjMatrix, graphF.adjMatrix, graphM.forwardEdges, optimizedMapping)

	log.Printf("Optimized alignment score: %d\n", optimizedScore)
	log.Printf("Improvement: %f%%\n", (float64(optimizedScore)-float64(initialScore))/float64(initialScore)*100.0)

	// Write optimized mapping to CSV
	writeMapping(os.Args[5], optimizedMapping)
}
