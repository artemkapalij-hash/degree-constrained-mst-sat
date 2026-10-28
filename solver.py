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

# edge_vars is a list of propositional variables
# edge_vars[i] := "is the i-th edge in the tree?"
edge_vars = []
vc = VariableCounter();

#################################
### VERTEX DEGREE ENFORCEMENT ###
#################################

# degree_vars is a set of propositional variables for degree constraint enforcement
# we have to order the edges, incident to a vertex v in some way, so 
# current edges is a list of such edges, ordered in some way 
# degree_vars[v][j][i] := "from j first edges adjacent to v, are at least i of them in the ST?"
current_edges = []
degree_vars = []

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


