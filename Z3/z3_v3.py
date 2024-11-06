import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from z3 import *

@dataclass
class ConnectomeData:
    node_count: int
    edges: dict[tuple[int, int], int]
    node_to_idx: dict[int, int]


def read_edges(filename: str) -> ConnectomeData:
    """Read edge data from CSV file and convert to indexed representation."""

    edges = {}
    node_to_idx = {}  # Map from node ID to index
    node_count = 0

    with open(filename, encoding='utf-8') as f:
        reader = csv.reader(f)
        assert next(reader) == ['From Node ID', 'To Node Id', 'Weight']  # Verify header
        for row in csv.reader(f):