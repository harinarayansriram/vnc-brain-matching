package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"os"
	"strconv"
)

const nodeCount int = 18524

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

func createScoreLookup(gm, gf *Graph, mapping map[int]int) []int16 {
	fmt.Println("Creating score lookup...")
	lookup := make([]int16, nodeCount*nodeCount)

	for m1 := 0; m1 < nodeCount; m1++ {
		lookup[m1*nodeCount+m1] = 0

		for m2 := 0; m2 < m1; m2++ {
			if (m1*nodeCount+m2)%10000 == 0 {
				fmt.Println("Done with", m1*nodeCount+m2, "pairs out of", nodeCount*(nodeCount-1)/2)
			}
			delta := int16(calculateSwapDelta(gm, gf, mapping, m1, m2))
			lookup[m1*nodeCount+m2] = delta
			lookup[m2*nodeCount+m1] = delta
		}
	}
	fmt.Println("Finished creating score lookup")

	return lookup
}

func saveScoreLookup(lookup []int16, filename string) error {
	fmt.Println("Saving score lookup...")
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	wr := csv.NewWriter(file)
	defer wr.Flush()

	for m1 := 0; m1 < nodeCount; m1++ {
		if m1%1000 == 0 {
			fmt.Println("Done with", m1, "rows out of", nodeCount)
		}
		var row []string
		for m2 := 0; m2 < nodeCount; m2++ {
			row = append(row, strconv.Itoa(int(lookup[m1*nodeCount+m2])))
		}
		wr.Write(row)
	}

	return wr.Error()
}

func main() {
	if len(os.Args) < 5 {
		fmt.Println("Usage: create_score_lookup <male graph> <female graph> <benchmark mapping> <output file>")
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
	benchmark, err := loadBenchmarkMapping(os.Args[3])
	if err != nil {
		log.Fatal("Error loading benchmark mapping:", err)
	}
	fmt.Println("Loaded in benchmark mapping")

	outPath := os.Args[4]
	lookup := createScoreLookup(gm, gf, benchmark)
	err = saveScoreLookup(lookup, outPath)
	if err != nil {
		log.Fatal("Error saving score lookup:", err)
	}
}
