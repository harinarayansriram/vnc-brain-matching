package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"math"
	"os"
	"strconv"
)

const saveInterval int = 25
const updateInterval int = 20

// Graph represents a weighted directed graph
type Graph struct {
	edges        map[int]map[int]int
	reverseEdges map[int]map[int]int
	nodes        map[int]struct{}
}

func readOrdering(filename string) map[int]int {
	fmt.Println("Reading ordering from", filename)

	ordering := make(map[int]int)
	file, err := os.Open(filename)
	if err != nil {
		panic(err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.Read()
	for {
		record, err := reader.Read()
		if err != nil {
			break
		}

		node_id, err := strconv.Atoi(record[0])
		if err != nil {
			panic(err)
		}
		order, err := strconv.Atoi(record[1])
		if err != nil {
			panic(err)
		}

		ordering[node_id] = order
	}

	return ordering
}

// NodeMetrics stores various metrics for each node
type NodeMetrics struct {
	inDegree     int
	outDegree    int
	totalWeight  int
	avgInWeight  float64
	avgOutWeight float64
	orderingRank int
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

// Calculates node metrics for all nodes
func (g *Graph) CalculateNodeMetrics(filepath string) map[int]NodeMetrics {
	metrics := make(map[int]NodeMetrics)
	ordering := readOrdering(filepath)

	for node := range g.nodes {
		var m NodeMetrics
		inEdges := make(map[int]int)

		// Calculate outgoing edges
		for _, weight := range g.edges[node] {
			m.outDegree++
			m.totalWeight += weight
		}

		// Calculate incoming edges
		for src, weight := range g.reverseEdges[node] {
			m.inDegree++
			m.totalWeight += weight
			inEdges[src] = weight
		}

		if m.outDegree > 0 {
			m.avgOutWeight = float64(m.totalWeight) / float64(m.outDegree)
		}
		if m.inDegree > 0 {
			m.avgInWeight = float64(len(inEdges)) / float64(m.inDegree)
		}

		m.orderingRank = ordering[node]

		metrics[node] = m
	}

	return metrics
}

func calculateNodeSimilarity(m1, m2 NodeMetrics) float64 {
	score := 5*math.Abs(float64(m1.inDegree-m2.inDegree)) + 5*math.Abs(float64(m1.outDegree-m2.outDegree)) + math.Abs(m1.avgInWeight-m2.avgInWeight) + math.Abs(m1.avgOutWeight-m2.avgOutWeight)
	orderingSim := math.Abs(float64(m1.orderingRank - m2.orderingRank))
	score = 0.7*score + 0.3*orderingSim

	return -score
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
		mapping[from] = to
	}

	return mapping, nil
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

// Optimizes mapping using local search with node similarity heuristics
func optimizeMapping(gm, gf *Graph, initialMapping map[int]int, maleOrderingPath, femaleOrderingPath, outPath string) map[int]int {
	currentMapping := make(map[int]int)
	for k, v := range initialMapping {
		currentMapping[k] = v
	}

	metricsM := gm.CalculateNodeMetrics(maleOrderingPath)
	metricsF := gf.CalculateNodeMetrics(femaleOrderingPath)

	currentScore := calculateAlignmentScore(gm, gf, currentMapping)

	simPredicted := 0
	simCorrect := 0
	outerNodeCount := 0

	// Try swapping pairs of mappings
	for nodeM1 := range gm.nodes {
		outerNodeCount++
		if outerNodeCount%updateInterval == 0 {
			fmt.Printf("%d nodes processed of %d\n", outerNodeCount, len(gm.nodes))
			fmt.Printf("Predicted: %d, Correct: %d, Accuracy: %.2f\n", simPredicted, simCorrect, float64(simCorrect)/float64(simPredicted))
			// fmt.Println("Current score: ", currentScore, "Actually: ", calculateAlignmentScore(gm, gf, currentMapping))
			fmt.Println("Current score: ", currentScore)

			simPredicted = 0
			simCorrect = 0
		}
		if outerNodeCount%saveInterval == 0 {
			writeMapping(outPath, currentMapping)
		}
		for nodeM2 := range gm.nodes {
			if nodeM1 == nodeM2 {
				continue
			}

			// Calculate similarity scores for current and swapped mappings
			nodeF1 := currentMapping[nodeM1]
			nodeF2 := currentMapping[nodeM2]

			currentSim := calculateNodeSimilarity(metricsM[nodeM1], metricsF[nodeF1]) +
				calculateNodeSimilarity(metricsM[nodeM2], metricsF[nodeF2])

			swappedSim := calculateNodeSimilarity(metricsM[nodeM1], metricsF[nodeF2]) +
				calculateNodeSimilarity(metricsM[nodeM2], metricsF[nodeF1])

			if swappedSim > currentSim {
				simPredicted++
				// Try the swap
				delta := calculateSwapDelta(gm, gf, currentMapping, nodeM1, nodeM2)

				if delta > 0 {
					simCorrect++
					//Apply the swap
					currentMapping[nodeM1], currentMapping[nodeM2] = nodeF2, nodeF1
					currentScore += delta
				}
			}
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
