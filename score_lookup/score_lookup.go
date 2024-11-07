package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"container/heap"
)

type Swap struct{
	male_node_id int
	female_node_id int
	delta int
}

type BoundedHeap struct {
	elements []Swap
	capacity int
}
//Max heap

func (h *BoundedHeap) Len() int {
	return len(h.elements)
}
func (h *BoundedHeap) Less(i, j int) bool {
	return h.elements[i].delta > h.elements[j].delta
}
func (h *BoundedHeap) Swap(i, j int) {
	h.elements[i], h.elements[j] = h.elements[j], h.elements[i]
}
func (h *BoundedHeap) Push(x interface{}) {
	if len(h.elements) < h.capacity {
		heap.Push(h, x)
	}else if(x.(int) > h.elements[0].delta){
		heap.Pop(h)
		heap.Push(h, x)
	}
}

func (h *BoundedHeap) Pop() interface{} {
	x := heap.Pop(h)
	return x
}

func newBoundedHeap(capacity int) *BoundedHeap {
	return &BoundedHeap{
		elements: make([]int, 0, capacity),
		capacity: capacity,
	}
}

const saveInterval int = 25
const updateInterval int = 20

const nodeCount int = 18524

// Graph represents a weighted directed graph
type Graph struct {
	edges        map[int]map[int]int
	reverseEdges map[int]map[int]int
	nodes        map[int]struct{}
}


// Creates a new graph
func NewGraph() *Graph {
	return &Graph{
		edges: make(map[int]map[int]int),
		nodes: make(map[int]struct{}),

		reverseEdges: make(map[int]map[int]int),
	}
}

// Adds an edge to the graph
func (g *Graph) AddEdge(from, to int, weight int) {
	if g.edges[from] == nil {
		g.edges[from] = make(map[int]int)
	}
	g.edges[from][to] = weight

	if g.reverseEdges[to] == nil {
		g.reverseEdges[to] = make(map[int]int)
	}
	g.reverseEdges[to][from] = weight
	g.nodes[from] = struct{}{}
	g.nodes[to] = struct{}{}
}

// Gets edge weight between nodes (0 if no edge exists)
func (g *Graph) GetWeight(from, to int) int {
	if edges, ok := g.edges[from]; ok {
		return edges[to]
	}
	return 0
}

// Calculates alignment score for current mapping
func calculateAlignmentScore(gm, gf *Graph, mapping map[int]int) int {
	var score int

	for srcM := range gm.nodes {
		for dstM := range gm.edges[srcM] {
			srcF := mapping[srcM]
			dstF := mapping[dstM]
			score += min(gm.edges[srcM][dstM], gf.GetWeight(srcF, dstF))
		}
	}
	return score
}

// Loads graph from CSV file
func loadGraphFromCSV(filename string) (*Graph, error) {
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

	graph := NewGraph()

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
		to, err := strconv.Atoi(record[1])
		if err != nil {
			panic(err)
		}

		graph.AddEdge(from, to, weight)
	}

	return graph, nil
}



// Calculate change in alignment score for swapping two nodes
func calculateSwapDelta(gm, gf *Graph, mapping map[int]int, nodeM1, nodeM2 int) int {
	nodeF1 := mapping[nodeM1]
	nodeF2 := mapping[nodeM2]
	var delta int

	// Remove old contributions

	for node := range gm.edges[nodeM1] {
		if node == nodeM2 {
			continue
		}
		// Outgoing edges from nodeM1
		weightM := gm.GetWeight(nodeM1, node)

		oldF := min(weightM, gf.GetWeight(nodeF1, mapping[node]))
		newF := min(weightM, gf.GetWeight(nodeF2, mapping[node]))
		delta += newF - oldF
	}

	for node := range gm.edges[nodeM2] {
		if node == nodeM1 {
			continue
		}
		// Outgoing edges from nodeM2
		weightM := gm.GetWeight(nodeM2, node)

		oldF := min(weightM, gf.GetWeight(nodeF2, mapping[node]))
		newF := min(weightM, gf.GetWeight(nodeF1, mapping[node]))
		delta += newF - oldF
	}

	for node := range gm.reverseEdges[nodeM1] {
		if node == nodeM2 {
			continue
		}
		// Incoming edges to nodeM1
		weightM := gm.GetWeight(node, nodeM1)

		oldF := min(weightM, gf.GetWeight(mapping[node], nodeF1))
		newF := min(weightM, gf.GetWeight(mapping[node], nodeF2))
		delta += newF - oldF
	}

	for node := range gm.reverseEdges[nodeM2] {
		if node == nodeM1 {
			continue
		}
		// Incoming edges to nodeM2
		weightM := gm.GetWeight(node, nodeM2)

		oldF := min(weightM, gf.GetWeight(mapping[node], nodeF2))
		newF := min(weightM, gf.GetWeight(mapping[node], nodeF1))
		delta += newF - oldF
	}

	// 3. Edges between nodeM1 and nodeM2
	weightM12 := gm.GetWeight(nodeM1, nodeM2)
	weightM21 := gm.GetWeight(nodeM2, nodeM1)
	if weightM12 > 0 {
		oldF := min(weightM12, gf.GetWeight(nodeF1, nodeF2))
		newF := min(weightM12, gf.GetWeight(nodeF2, nodeF1))
		delta += newF - oldF
	}
	if weightM21 > 0 {
		oldF := min(weightM21, gf.GetWeight(nodeF2, nodeF1))
		newF := min(weightM21, gf.GetWeight(nodeF1, nodeF2))
		delta += newF - oldF
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
		wr.Write([]string{"m" + strconv.Itoa(male_node_id), "f" + strconv.Itoa(female_node_id)})
	}

	wr.Flush()
}

func loadScoreAdjacency(filename string) []int16 {
	adjacency := make([]int16, nodeCount*nodeCount)
	file, err := os.Open(filename)
	if err != nil {
		panic(err)
	}

	defer file.Close()

	scanner := bufio.NewScanner(file)
	scanner.Split(bufio.ScanLines)
	for i := 0; i < nodeCount; i++ {
		scanner.Scan()
		line := scanner.Text()
		if len(line) == 0 {
			break
		}
		tokens := strings.Split(line, ",")
		for j := 0; j < nodeCount; j++ {
			delta, err := strconv.Atoi(tokens[j])
			if err != nil {
				panic(err)
			}
			adjacency[i*nodeCount+j] = int16(delta)
		}
	}

	return adjacency
}

// Optimizes mapping using local search with node similarity heuristics
func optimizeMapping(gm, gf *Graph, initialMapping map[int]int, maleOrderingPath, femaleOrderingPath, outPath string) map[int]int {
	currentMapping := make(map[int]int)
	for k, v := range initialMapping {
		currentMapping[k] = v
	}

	currentScore := calculateAlignmentScore(gm, gf, currentMapping)

	outerNodeCount := 0
	simPredicted := 0
	simCorrect := 0

	// Try swapping pairs of mappings
	for nodeM1 := range gm.nodes {
		outerNodeCount++
		if outerNodeCount%updateInterval == 0 {
			fmt.Printf("%d nodes processed of %d\n", outerNodeCount, len(gm.nodes))
			fmt.Printf("Predicted: %d, Correct: %d, Accuracy: %.2f\n", simPredicted, simCorrect, float64(simCorrect)/float64(simPredicted))
			// fmt.Println("Current score: ", currentScore, "Actually: ", calculateAlignmentScore(gm, gf, currentMapping))
			fmt.Println("Current score: ", currentScore)

		}
		if outerNodeCount%saveInterval == 0 {
			writeMapping(outPath, currentMapping)
		}
		for nodeM2 := range gm.nodes {
			if nodeM1 == nodeM2 {
				continue
			}

			// Calculate similarity scores for current and swapped mappings
			// nodeF1 := currentMapping[nodeM1]
			// nodeF2 := currentMapping[nodeM2]

		
			// if swappedSim > currentSim {
			// 	simPredicted++
			// 	// Try the swap
			// 	delta := calculateSwapDelta(gm, gf, currentMapping, nodeM1, nodeM2)

			// 	if delta > 0 {
			// 		simCorrect++
			// 		//Apply the swap
			// 		currentMapping[nodeM1], currentMapping[nodeM2] = nodeF2, nodeF1
			// 		currentScore += delta
			// 	}
			// }
		}
	}

	return currentMapping
}

func main() {
	if len(os.Args) < 7 {
		fmt.Println("Usage: basic_metrics <male graph> <female graph> <male ordering> <female ordering> <in mapping> <out mapping>")
		os.Exit(1)
	}
	// Load graphs
	gm, err := loadGraphFromCSV(os.Args[1])
	if err != nil {
		log.Fatal("Error loading male graph:", err)
	}
	fmt.Println("Loaded in male graph")

	gf, err := loadGraphFromCSV(os.Args[2])
	if err != nil {
		log.Fatal("Error loading female graph:", err)
	}
	fmt.Println("Loaded in female graph")

	// Load benchmark mapping
	benchmark, err := loadBenchmarkMapping(os.Args[5])
	if err != nil {
		log.Fatal("Error loading benchmark mapping:", err)
	}
	fmt.Println("Loaded in benchmark mapping")

	// Calculate initial score
	initialScore := calculateAlignmentScore(gm, gf, benchmark)
	fmt.Printf("Initial alignment score: %d\n", initialScore)

	fmt.Println("Starting optimization...")

	// Optimize mapping
	optimizedMapping := optimizeMapping(gm, gf, benchmark, os.Args[3], os.Args[4], os.Args[6])
	optimizedScore := calculateAlignmentScore(gm, gf, optimizedMapping)

	fmt.Printf("Optimized alignment score: %d\n", optimizedScore)
	fmt.Printf("Improvement: %f%%\n", (float64(optimizedScore)-float64(initialScore))/float64(initialScore)*100.0)

	// Write optimized mapping to CSV
	writeMapping(os.Args[6], optimizedMapping)
}
