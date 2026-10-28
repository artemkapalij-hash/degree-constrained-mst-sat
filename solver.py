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

#################################
### VERTEX DEGREE ENFORCEMENT ###
#################################

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
# the (not dp[deg(v)][k+1]) clause

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

clauses.append([1])
clauses.append([2])
clauses.append([3])
clauses.append([4])

with open("formula.cnf", "w") as out:
    out.write(f"p cnf {vc.variables_count} {len(clauses)}\n")
    for clause in clauses:
        out.write(" ".join(map(str, clause)) + " 0\n")








        
