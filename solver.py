#!/usr/bin/env python3

import subprocess
import sys
from collections import deque
from argparse import ArgumentParser

parser = ArgumentParser()

parser.add_argument(
    "-i",
    "--input",
    default="in.txt",
    type=str,
    help=(
        "The instance file."
    ),
)

parser.add_argument(
    "-o",
    "--output",
    default="formula.cnf",
    type=str,
    help=(
        "Output file for the DIMACS format (i.e. the CNF formula)."
    ),
)

parser.add_argument(
    "-v",
    "--verb",
    default=1,
    type=int,
    choices=range(0,2),
    help=(
        "Verbosity of the SAT solver used."
    ),
)

args = parser.parse_args()

with open(args.input) as in_file:
    lines = in_file.read().splitlines()

vertices_count, edges_count, degree_constraint = lines[0].split()
vertices_count = int(vertices_count)
edges_count = int(edges_count)
degree_constraint = int(degree_constraint)

class VariableCounter:

    def __init__(self):
        self.variables_count = 0
    
    def next_var(self):
        self.variables_count += 1
        return self.variables_count

edges = []
for edge in lines[1:]:
    edge = edge.split()
    if len(edge) != 2:
        continue
    edges.append((int(edge[0]), int(edge[1])))

# edge_vars is a list of propositional variables
# edge_vars[i] := "is the i-th edge in the tree?"
edge_vars = []
vc = VariableCounter()
while len(edge_vars) != len(edges):
    edge_vars.append(vc.next_var())

# generate a list of variables of edges incident to a vertex
# with this list comprehention: [edge_var[i] for i in incident[v]]
incident = [[] for _ in range(vertices_count)]
for i, (u, v) in enumerate(edges):
    incident[u].append(i)
    incident[v].append(i)

edges_incident_to_vertices = [[edge_vars[i] for i in incident[v]] for v in range(vertices_count)]

###########################################
######## VERTEX DEGREE ENFORCEMENT ########
###########################################

# degree_vars is a set of propositional variables for degree constraint enforcement
# we have to order the edges, incident to a vertex v in some way, so 
# current edges is a list of such edges, ordered in some way 
# degree_vars[v][j][i] := "from j first edges adjacent to v, are at least i of them in the ST?"

# one could think about this verification process as a dynamic programming problem
# with the "table" dp and e[i] := "is i-th edge in a ST?"
# dp[j][i] is true when one of the following holds: dp[j - 1][i] is true or
# dp[j - 1][i - 1] and e[j] both hold

# dp[j][i] = dp[j - 1][i] or (dp[j - 1][i - 1] and e[j])
# or
# dp[j][i] <-> dp[j - 1][i] or (dp[j - 1][i - 1] and e[j])
# if dp[deg(n)][k + 1] holds, the degree constraint is not met
# so at the end, we add a clause (not dp[deg(v)][k+1]), 
# so that the whole formula fails, if degree constraint is not met

# now note, that it is sufficient to write a one-way implication 
# dp[j][i] <- dp[j - 1][i] or (dp[j - 1][i - 1] and e[j])
# it will allow some invalid assignments to pass through the
# implications part of the formula, but they will fail
# the (not dp[deg(v)][k+1]) clause, and we get half the number 
# of clauses

# so in a group of clauses, that handles the degree constraint, there 
# will be subgroup, handling each vertex
# each such subgroup will constrain the "dp table" using implications and 
# check if (not dp[deg(v)][k+1]) holds in the end
# if it does, the node satisfies the degree constraint

# use the fact that p -> q ~ (not p) or q

# dp[j][i] <- dp[j - 1][i] or (dp[j - 1][i - 1] and e[j]) ~
# dp[j][i] or ((not dp[j - 1][i]) and (not (dp[j - 1][i - 1]) or (not e[j]))) ~
# (dp[j][i] or (not dp[j - 1][i])) and (dp[j][i] or not (dp[j - 1][i - 1]) or (not e[j])) 
# which gives two clauses per implication, add that for all the related 
# propositional variables, also enforce dp[0][0] to be true and dp[deg(v)][k+1]
# to be false (by adding clause with just the variable for dp[0][0] and
# one with negation of dp[deg(v)][k+1]) one pair for every vertex

def at_most_k(variables, k, vc):
    n = len(variables)
    if n <= k:
        return []

    counter_vars = [[vc.next_var() for _ in range(k + 2)] for _ in range(n + 1)] 

    # counter_vars[n][k + 1] means k+1 or more are true, so force it to be false
    # counter_vars[0][0] means at least zero are selected, which trivially holds
    clauses = [[counter_vars[0][0]], [-counter_vars[n][k + 1]]] 

    for j in range(1, n + 1):
        x = variables[j - 1]
        for i in range(k + 2):
            clauses.append([counter_vars[j][i], -counter_vars[j - 1][i]])
            if i - 1 >= 0:
                clauses.append([counter_vars[j][i], -counter_vars[j - 1][i - 1], -x])
    return clauses

clauses = []

# to avoid writing any cyclicness checks, just do not consider graphs that have over n - 1
# edges, since any connected subgraph of n - 1 edges is a spanning tree
clauses.extend(at_most_k(edge_vars, vertices_count - 1, vc))

for v in range(vertices_count):
    clauses.extend(at_most_k(edges_incident_to_vertices[v], degree_constraint, vc))

##########################################
######## CONNECTIVITY ENFORCEMENT ########
##########################################

# a graph is connected if, and only if there is 
# a path between every two vertices

# in an undirected graph, the condition collapses
# to: every vertex must be reachable from one specific
# vertex (denote as 0), because a path u->v can be
# constructed by concatenating u->0 and 0->v

# procedurally, that would mean inductively checking if every 
# vertex u is adjacent to v, or if u is adjacent to some node,
# that is reachable from v, let us translate it into logical formulas

# a naive dp[i] <-> dp[adj[i][0]] or ... or dp[adj[i][deg(i) - 1]] will fail,
# because dp[i] and dp[j] can just "satisfy each other", if they 
# are connected, without actually being reachable from 0

# solution is basically BFS
# dp[i][s] := "is i reachable from 0 in s or less steps?"
# let adj[i][j] be the j-th vertex of the graph, adjacent to i
# e[i][j] := "is an edge by which j-th neighbour is connected to i in the tree?"
# dp[i][s] <-> dp[i][s - 1] or (dp[adj[i][0]][s - 1] and e[i][0]) or ... or
#              (dp[adj[i][deg(i) - 1]][s - 1] and e[i][deg(i) - 1])

# dp[i][s] -> dp[i][s - 1] or (dp[adj[i][0]][s - 1] and e[i][0]) or ... or
#             (dp[adj[i][deg(i) - 1]][s - 1] and e[i][deg(i) - 1])
# is sufficient, because the invalid states it allows only UNDERcount the connectedness
# (dp[i][s] can be false, while the RHS expression is true, but this is 
# harmless, because it will never say a graph is connected on a disconnected graph,
# unlike the "<-", because it can conclude connectedness on a disconnected graph)

# you can see how simple distribution will make the formula blow up exponentially
# with respect to clauses, if simple distributive law is used to 
# convert into CNF

# introduce a variable c[i][j][s - 1] <-> (dp[adj[i][j]][s - 1] and e[i][j])
# just the "->" is enough

# c[i][j][s - 1] -> (dp[adj[i][j]][s - 1] and e[i][j]) ~
# (not c[i][j][s - 1]) or (dp[adj[i][j]][s - 1] and e[i][j]) ~
# ((not c[i][j][s - 1]) or dp[adj[i][j]][s - 1]) and ((not c[i][j][s - 1]) or e[i][j])

# so (not dp[i][s]) or dp[i][s - 1] or c[i][0][s - 1] or ... or c[i][deg(i) - 1][s - 1]

connected = {}
for i in range(vertices_count):
    for j in range(len(edges_incident_to_vertices[i])):
        for s in range(vertices_count): # longest path has (vertices_count - 1) edges
            connected[(i, j, s)] = vc.next_var()

reachable = {}
for i in range(vertices_count):
    for s in range(vertices_count):
        reachable[(i, s)] = vc.next_var()

for i in range(1, vertices_count):
    clauses.append([-reachable[i, 0]])

for i in range(vertices_count):
    for j in range(len(edges_incident_to_vertices[i])):
        for s in range(vertices_count): 
            u = edges[incident[i][j]][0]
            v = edges[incident[i][j]][1]
            neighbour = v if u == i else u
            clauses.append([-connected[i, j, s], reachable[neighbour, s]])
            clauses.append([-connected[i, j, s], edges_incident_to_vertices[i][j]])

clauses.append([reachable[0, 0]])
for i in range(vertices_count):
    for s in range(1, vertices_count): 
        clause = []
        clause.append(-reachable[i, s])
        clause.append(reachable[i, s - 1])
        for j in range(len(edges_incident_to_vertices[i])):
            clause.append(connected[i, j, s - 1])
        clauses.append(clause)

for i in range(vertices_count):
    clauses.append([reachable[i, vertices_count - 1]])


with open(args.output, "w") as out:
    out.write(f"p cnf {vc.variables_count} {len(clauses)}\n")
    for clause in clauses:
        out.write(" ".join(map(str, clause)) + " 0\n")

result = subprocess.run(["./glucose-simp", "-model", f"-verb={args.verb}", args.output], capture_output=True, text=True)
print()
print("###########################################################################################################")
print("############################################### GLUCOSE OUT ###############################################")
print("###########################################################################################################")
print()
print(result.stdout)

if result.returncode == 20:
    print("No spanning tree with maximum degree", degree_constraint)
    sys.exit(1)

if result.returncode != 10:
    print("Solver error")
    sys.exit(1)

true_vars = set()
for line in result.stdout.splitlines():
    if not line.startswith("v "):
        continue
    for literal in line[2:].split():
        value = int(literal)
        if value > 0:
            true_vars.add(value)

chosen = [edge for index, edge in enumerate(edges) if index + 1 in true_vars]

neighbours = [[] for _ in range(vertices_count)]
for a, b in chosen:
    neighbours[a].append(b)
    neighbours[b].append(a)

visited = [False] * vertices_count
visited[0] = True
queue = deque([0])
while queue:
    current = queue.popleft()
    for neighbour in neighbours[current]:
        if not visited[neighbour]:
            visited[neighbour] = True
            queue.append(neighbour)

if not all(len(x) <= degree_constraint for x in neighbours):
    print("Bad output:")
    for a, b in chosen:
        print(a, b)
    violating = [v for v, nbrs in enumerate(neighbours) if len(nbrs) > degree_constraint]
    print(f"Solver error: the produced graph violates the degree constraint ({degree_constraint}) on the vertices {violating}")
    sys.exit(1)

if len(chosen) != vertices_count - 1:
    print("Bad output:")
    for a, b in chosen:
        print(a, b)
    print(f"Solver error: the produced graph has {len(chosen)} edges, any spanning tree must have {vertices_count - 1}")
    sys.exit(1)

if not all(visited):
    print("Bad output:")
    for a, b in chosen:
        print(a, b)
    unreachable = [i for i, vis in enumerate(visited) if not vis]
    print(f"Solver error: the produced graph is disconnected, the vertices {unreachable} are unreachable from the vertex 0")
    sys.exit(1)

print("###########################################################################################################")
print("########################################### HUMAN-READABLE OUT ############################################")
print("###########################################################################################################")
print()

print(f"{vertices_count} vertices, {edges_count} edges, max degree {degree_constraint}")

print()
print("Edges:")
for line in lines[1:]:
    print(line)
print()

print("A spanning tree of the given graph is a subgraph with the following edges:")
for a, b in chosen:
    print(a, b)
sys.exit(0)
