#include <iostream>
#include <fstream>
#include <vector>
#include <map>
#include <set>
#include <cmath>
#include <algorithm>
#include <random>
#include <string>
#include <sstream>
#include <iterator>

using namespace std;

using int64 = long long;
using Edge = pair<int, int>;
using AdjacencyList = vector<vector<Edge>>;

struct GraphEdge {
    int64 source;
    int64 target;
    int weight;
};

// Global variables
AdjacencyList outAdj;
AdjacencyList inAdj;
vector<GraphEdge> graph;

map<int64, int> nodeToSortedIdx;
vector<int64> sortedIdxToNode;
map<int64, map<int64, int>> outLookup;
map<int64, map<int64, int>> inLookup;

vector<int> state;

void handleErr(bool condition, const string& message) {
    if (condition)
    {
        throw runtime_error(message);
    }
}

int energy(const vector<int>& state) {
    // const int totalWeight = 41912141;
    // int backwards = 0;
    int forwards = 0;
    for (const auto& row : graph)
    {
        int64 source = row.source;
        int64 target = row.target;
        int weight = row.weight;

        if (state[nodeToSortedIdx[source]] < state[nodeToSortedIdx[target]])
        {
            forwards += weight;
        }
    }
    return -forwards;
}

void writeToCSV(const string& file, const vector<int>& state, const vector<int64>& sortedIdxToNode) {
    ofstream f(file);
    handleErr(!f.is_open(), "Failed to create file: " + file);

    f << "Node ID,Order\n";

    for (size_t i = 0; i < sortedIdxToNode.size(); ++i)
    {
        f << sortedIdxToNode[i] << "," << state[i] << "\n";
    }
    f.close();
}
vector<vector<string>> readCSV(const string& file) {
    ifstream f(file);
    handleErr(!f.is_open(), "Failed to open file: " + file);

    vector<vector<string>> records;
    string line;

    while (getline(f, line))
    {
        istringstream ss(line);
        vector<string> record;
        string cell;

        while (getline(ss, cell, ','))
        {
            record.push_back(cell);
        }
        records.push_back(record);
    }
    f.close();
    return records;
}

int main(int argc, char* argv[]) {
    if(argc != 2) {
        cerr << "Usage: " << argv[0] << " <connectome.csv>" << endl;
        return 1;
    }

    auto graphRecords = readCSV(argv[1]);
    set<int64> nodesSet;

    for (size_t i = 1; i < graphRecords.size(); ++i)
    {
        auto& row = graphRecords[i];
        int64 sourceID = stoll(row[0]);
        int64 targetID = stoll(row[1]);
        int edgeWeight = stoi(row[2]);

        graph.push_back({ sourceID, targetID, edgeWeight });
        nodesSet.insert(sourceID);
        nodesSet.insert(targetID);

        outLookup[sourceID][targetID] = edgeWeight;
        inLookup[targetID][sourceID] = edgeWeight;
    }

    sortedIdxToNode.resize(nodesSet.size());
    copy(nodesSet.begin(), nodesSet.end(), sortedIdxToNode.begin());

    sort(sortedIdxToNode.begin(), sortedIdxToNode.end());

    for (size_t i = 0; i < sortedIdxToNode.size(); ++i)
    {
        nodeToSortedIdx[sortedIdxToNode[i]] = i;
    }

    // Initialize outAdj and inAdj based on outLookup and inLookup
    outAdj.resize(sortedIdxToNode.size());
    inAdj.resize(sortedIdxToNode.size());

    for (size_t i = 0; i < sortedIdxToNode.size(); ++i)
    {
        int64 node = sortedIdxToNode[i];
        for (const auto& [target, weight] : outLookup[node])
        {
            outAdj[i].emplace_back(nodeToSortedIdx[target], weight);
        }
        for (const auto& [source, weight] : inLookup[node])
        {
            inAdj[i].emplace_back(nodeToSortedIdx[source], weight);
        }
    }

    // Initialize state with a random permutation
    state.resize(nodesSet.size());
    vector<int> perm(state.size());
    iota(perm.begin(), perm.end(), 0);
    random_device rd;
    mt19937 g(rd());
    shuffle(perm.begin(), perm.end(), g);
    for (size_t i = 0; i < perm.size(); ++i)
    {
        state[i] = perm[i];
    }

    int startEnergy = energy(state);
    cout << "Energy: " << startEnergy << '\n';

    writeToCSV(to_string(-startEnergy) + ".csv", state, sortedIdxToNode);

    return 0;
}