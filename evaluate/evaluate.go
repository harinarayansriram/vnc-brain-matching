package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"strconv"
)

type Edge struct {
	src int
	dst int
}

func readConnectomeEdges(filename string) map[Edge]int {
	fmt.Println("Reading connectome from", filename)

	edges := make(map[Edge]int)
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

		src, err := strconv.Atoi(record[0])
		if err != nil {
			panic(err)
		}
		dst, err := strconv.Atoi(record[1])
		if err != nil {
			panic(err)
		}
		weight, err := strconv.Atoi(record[2])
		if err != nil {
			panic(err)
		}

		edges[Edge{src, dst}] = weight
	}
	fmt.Println("Read", len(edges), "rows")

	return edges
}

func readMapping(filename string) map[int]int {
	fmt.Println("Reading mapping from", filename)

	mapping := make(map[int]int)
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

		src, err := strconv.Atoi(record[0][1:])
		if err != nil {
			panic(err)
		}
		dst, err := strconv.Atoi(record[1][1:])
		if err != nil {
			panic(err)
		}

		mapping[src] = dst
	}

	fmt.Println("Read", len(mapping), "rows")

	return mapping
}
func main() {

	if len(os.Args) < 2 {
		fmt.Println("Usage: evaluate <male_connectome.csv> <female_connectome.csv> <mapping.csv>")
		fmt.Println("Note: male and female connectomes must be processed to add the singleton nodes + strip prefixes")
		os.Exit(1)
	}

	//Read in the edges
	male_edges := readConnectomeEdges(os.Args[1])
	female_edges := readConnectomeEdges(os.Args[2])

	mapping := readMapping(os.Args[3])

	alignment := 0
	for male_edge, male_weight := range male_edges {
		female_edge := Edge{mapping[male_edge.src], mapping[male_edge.dst]}

		female_weight := 0

		if weight, ok := female_edges[female_edge]; ok {
			female_weight = weight
		}

		alignment += min(male_weight, female_weight)
	}

	fmt.Println("Alignment score:", alignment)
}
