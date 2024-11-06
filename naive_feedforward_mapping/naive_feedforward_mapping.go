package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"strconv"
)

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

		ordering[order] = node_id
	}

	return ordering
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
		wr.Write([]string{"m"+strconv.Itoa(male_node_id), "f"+strconv.Itoa(female_node_id)})
	}

	wr.Flush()
}

func main() {
	if len(os.Args) != 4 {
		fmt.Println("Usage: go run naive_feedforward_mapping.go male_ordering.csv female_ordering.csv mapping.csv")
		os.Exit(1)
	}
	
	male_ordering_file := os.Args[1]
	female_ordering_file := os.Args[2]

	male_ordering := readOrdering(male_ordering_file)
	female_ordering := readOrdering(female_ordering_file)

	mapping := make(map[int]int)
	for i := 0; i < len(male_ordering); i++ {
		mapping[male_ordering[i]] = female_ordering[i]
	}

	writeMapping(os.Args[3], mapping)
}