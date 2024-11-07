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

const nodeCount int = 18524

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

type AdjacencyMetricsEdges struct {
	adjMatrix []int16
	metrics [][]int
	forwardEdges map[int]map[int]int
	reverseEdges map[int]map[int]int
}

func createAdjacencyMatrix(filename string) AdjacencyMetricsEdges{
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

		adjMatrix[from*nodeCount + to] = int16(weight)

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


// Calculates node metrics for all nodes
func calculateNodeMetrics(adjAndMetrics AdjacencyMetricsEdges, filepath string) map[int]NodeMetrics {
	metrics := make(map[int]NodeMetrics)
	ordering := readOrdering(filepath)

	// adjMatrix := adjAndMetrics.adjMatrix
	metricsArr := adjAndMetrics.metrics
	reverseEdges := adjAndMetrics.reverseEdges

	for node := 0; node < nodeCount; node++ {
		var m NodeMetrics

		m.totalWeight = metricsArr[node][0]
		m.outDegree = metricsArr[node][1]
		m.inDegree = metricsArr[node][2]


		if m.outDegree > 0 {
			m.avgOutWeight = float64(m.totalWeight) / float64(m.outDegree)
		}
		if m.inDegree > 0 {
			m.avgInWeight = float64(len(reverseEdges[node])) / float64(m.inDegree)
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
func calculateAlignmentScore(adjMatrixM []int16, adjMatrixF []int16, mapping map[int]int) int {
	var score int

	for srcM := 0; srcM < nodeCount; srcM++ {
		for dstM := range adjMatrixM[srcM] {
			srcF := mapping[srcM]
			dstF := mapping[int(dstM)]
			score += int(min(adjMatrixM[srcM * nodeCount + int(dstM)], adjMatrixF[srcF * nodeCount + dstF]))
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
		mapping[from] = to
	}

	return mapping, nil
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
		
		oldF := min(weightM, graphF.adjMatrix[nodeF1*nodeCount + mapping[node]])
		newF := min(weightM, graphF.adjMatrix[nodeF2*nodeCount + mapping[node]])
		delta += int(newF - oldF)
	}

	for node := range graphM.forwardEdges[nodeM2] {
		if node == nodeM1 {
			continue
		}
		// Outgoing edges from nodeM2
		weightM := graphM.adjMatrix[nodeM2*nodeCount+node]

		oldF := min(weightM, graphF.adjMatrix[nodeF2*nodeCount + mapping[node]])
		newF := min(weightM, graphF.adjMatrix[nodeF1*nodeCount + mapping[node]])
		delta += int(newF - oldF)
	}

	for node := range graphM.reverseEdges[nodeM1] {
		if node == nodeM2 {
			continue
		}
		// Incoming edges to nodeM1
		weightM := graphM.adjMatrix[node*nodeCount+nodeM1]

		oldF := min(weightM, graphF.adjMatrix[mapping[node]*nodeCount + nodeF1])
		newF := min(weightM, graphF.adjMatrix[mapping[node]*nodeCount + nodeF2])
		delta += int(newF - oldF)
	}

	for node := range graphM.reverseEdges[nodeM2] {
		if node == nodeM1 {
			continue
		}
		// Incoming edges to nodeM2
		weightM := graphM.adjMatrix[node*nodeCount+nodeM2]

		oldF := min(weightM, graphF.adjMatrix[mapping[node] * nodeCount+ nodeF2])
		newF := min(weightM, graphF.adjMatrix[mapping[node] * nodeCount+ nodeF1])
		delta += int(newF - oldF)
	}

	// 3. Edges between nodeM1 and nodeM2
	weightM12 := graphM.adjMatrix[nodeM1*nodeCount + nodeM2]
	weightM21 := graphM.adjMatrix[nodeM2*nodeCount + nodeM1]
	if weightM12 > 0 {
		oldF := min(weightM12, graphF.adjMatrix[nodeF1*nodeCount + nodeF2])
		newF := min(weightM12, graphF.adjMatrix[nodeF2*nodeCount + nodeF1])
		delta += int(newF - oldF)
	}
	if weightM21 > 0 {
		oldF := min(weightM21, graphF.adjMatrix[nodeF2*nodeCount + nodeF1])
		newF := min(weightM21, graphF.adjMatrix[nodeF1*nodeCount + nodeF2])
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
		wr.Write([]string{"m" + strconv.Itoa(male_node_id), "f" + strconv.Itoa(female_node_id)})
	}

	wr.Flush()
}

// Optimizes mapping using local search with node similarity heuristics
func optimizeMapping(graphM, graphF AdjacencyMetricsEdges, initialMapping map[int]int, maleOrderingPath, femaleOrderingPath, outPath string) map[int]int {
	currentMapping := make(map[int]int)
	for k, v := range initialMapping {
		currentMapping[k] = v
	}

	metricsM := calculateNodeMetrics(graphM, maleOrderingPath)
	metricsF := calculateNodeMetrics(graphF, femaleOrderingPath)

	currentScore := calculateAlignmentScore(graphF.adjMatrix, graphF.adjMatrix, currentMapping)

	simPredicted := 0
	simCorrect := 0
	outerNodeCount := 0

	// Try swapping pairs of mappings
	for nodeM1 := 0; nodeM1 < nodeCount; nodeM1++ {
		outerNodeCount++
		if outerNodeCount%updateInterval == 0 {
			fmt.Printf("%d nodes processed of %d\n", outerNodeCount, nodeCount)
			fmt.Printf("Predicted: %d, Correct: %d, Accuracy: %.2f\n", simPredicted, simCorrect, float64(simCorrect)/float64(simPredicted))
			// fmt.Println("Current score: ", currentScore, "Actually: ", calculateAlignmentScore(gm, gf, currentMapping))
			fmt.Println("Current score: ", currentScore)

			simPredicted = 0
			simCorrect = 0
		}
		if outerNodeCount%saveInterval == 0 {
			writeMapping(outPath, currentMapping)
		}
		for nodeM2 := 0; nodeM2 < nodeCount; nodeM2++ {
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
				delta := calculateSwapDelta(graphM,	graphF, currentMapping, nodeM1, nodeM2)

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
	graphM := createAdjacencyMatrix(os.Args[1])
	fmt.Println("Loaded in male graph")

	graphF := createAdjacencyMatrix(os.Args[2])
	fmt.Println("Loaded in female graph")

	// Load benchmark mapping
	benchmark, err := loadBenchmarkMapping(os.Args[5])
	if err != nil {
		log.Fatal("Error loading benchmark mapping:", err)
	}
	fmt.Println("Loaded in benchmark mapping")

	// Calculate initial score
	initialScore := calculateAlignmentScore(graphM.adjMatrix, graphF.adjMatrix, benchmark)
	fmt.Printf("Initial alignment score: %d\n", initialScore)

	fmt.Println("Starting optimization...")

	// Optimize mapping
	optimizedMapping := optimizeMapping(graphM, graphF, benchmark, os.Args[3], os.Args[4], os.Args[6])
	optimizedScore := calculateAlignmentScore(graphM.adjMatrix, graphF.adjMatrix, optimizedMapping)

	fmt.Printf("Optimized alignment score: %d\n", optimizedScore)
	fmt.Printf("Improvement: %f%%\n", (float64(optimizedScore)-float64(initialScore))/float64(initialScore)*100.0)

	// Write optimized mapping to CSV
	writeMapping(os.Args[6], optimizedMapping)
}
