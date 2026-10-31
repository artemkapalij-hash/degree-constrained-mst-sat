import subprocess
import sys
from collections import deque

with open("in.txt") as in_file:
    lines = in_file.read().splitlines()

vertices_count, edges_count, dergree_constraint = lines[0].split()
vertices_count = int(vertices_count)
edges_count = int(edges_count)
degree_constraint = int(dergree_constraint)

class VariableCounter:

    def __init__(self):
        self.variables_count = 0
    
    def next_var(self):
        self.variables_count += 1
        return self.variables_count

edges = []
for edge in lines[1:]:
    edge = edge.split()
    edges.append((int(edge[0]), int(edge[1])))

# edge_vars is a list of propositional variables
# edge_vars[i] := "is the i-th edge in the tree?"
edge_vars = []
vc = VariableCounter();
while (len(edge_vars) != len(edges)):
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

degree_vars = {}
for v in range(vertices_count):
    if len(edges_incident_to_vertices[v]) <= degree_constraint:
        continue
    for j in range(len(edges_incident_to_vertices[v]) + 1):
        for i in range(degree_constraint + 2):
            degree_vars[(v, j, i)] = vc.next_var()

clauses = []
for v in range(vertices_count):
    v_degree = len(edges_incident_to_vertices[v])
    if v_degree <= degree_constraint:
        continue
    clauses.append([degree_vars[v, 0, 0]])
    clauses.append([-degree_vars[v, v_degree, degree_constraint + 1]])
    for j in range(1, v_degree + 1):
        for i in range(degree_constraint + 2):
            clauses.append([degree_vars[v, j, i], -degree_vars[v, j - 1, i]])
            if i - 1 >= 0:
                clauses.append([degree_vars[v, j, i], -degree_vars[v, j - 1, i - 1], -edges_incident_to_vertices[v][j - 1]])

##########################################
######## CONNECTIVITY ENFORCEMENT ########
##########################################

# a graph is connected, if, and only if there is a path
# from some vertex to another one, for every two pairs,
# however, we are dealing with undirected graphs, so checking
# connectivity of just one vertex with every other is sufficient

# procedurally, that would mean inductively checking if every 
# vertex u is adjacent to v, or if u is adjacent to some node,
# that is reachable from v, let us translate it into logical formulas

# a naive dp[i] <-> dp[adj[i][0]] or ... or dp[adj[i][n]] will fail,
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
# is sufficient, because the invalid states it allows undercount the connectedness
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
        if s - 1 >= 0:
            clause.append(-reachable[i, s])
            clause.append(reachable[i, s - 1])
            for j in range(len(edges_incident_to_vertices[i])):
                clause.append(connected[i, j, s - 1])
        clauses.append(clause)

for i in range(vertices_count):
    clauses.append([reachable[i, vertices_count - 1]])


with open("formula.cnf", "w") as out:
    out.write(f"p cnf {vc.variables_count} {len(clauses)}\n")
    for clause in clauses:
        out.write(" ".join(map(str, clause)) + " 0\n")

result = subprocess.run(["./glucose-simp", "-model", "-verb=0", "formula.cnf"], capture_output=True, text=True)

if result.returncode == 20:
    print("No spanning tree with maximum degree", degree_constraint)
    sys.exit()

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
tree = []
while queue:
    current = queue.popleft()
    for neighbour in neighbours[current]:
        if not visited[neighbour]:
            visited[neighbour] = True
            tree.append((current, neighbour))
            queue.append(neighbour)

for a, b in tree:
    print(a, b)
