# Documentation

## Problem description

Degree-constrained spanning tree is a spanning tree where the maximum vertex degree is limited to a certain constant k. This project finds such a tree for a given graph, or reports it is impossible to construct, 
an example input is:

```
4 4 4 
0 1
1 2
2 0
3 0
```

The first line represents the number of nodes, edges and the degree constraint accordingly, every next line represents an edge of a given graph.

## Encoding

It is divided into two parts, degree and connectivity enforcement

### Vertex Degree Enforcement

The process skips vertices with the degree less or equal to k for obvious reasons

`degree_vars` is a set of propositional variables for degree constraint enforcement. We have to order the edges, incident to a vertex v in some way, so current edges is a list of such edges, ordered in some way. `degree_vars[v][j][i] := "from j first edges adjacent to v, are at least i of them in the ST?"`

One could think about this verification process as a dynamic programming problem. With the "table" dp (same meaning as degree_vars has) and `e[j] := "is j-th edge, incident to v in the ST?"`. `dp[j][i]` is true when one of the following holds: dp[j - 1][i] is true or dp[j - 1][i - 1] and e[j] both hold

`dp[0][0]` holds, so we add a unit clause with just the variable for it.
`dp[j][i] = dp[j - 1][i] or (dp[j - 1][i - 1] and e[j])`. Logically: `dp[j][i] <-> dp[j - 1][i] or (dp[j - 1][i - 1] and e[j])`. If `dp[deg(v)][k + 1]` holds, the degree constraint is not met. So at the end, we add a clause `(not dp[deg(v)][k+1])`, so that the whole formula fails, if degree constraint is not met

Now note, that it is sufficient to write a one-way implication: `dp[j][i] <- dp[j - 1][i] or (dp[j - 1][i - 1] and e[j])`. It will allow some invalid assignments to pass through the implications part of the formula (it can overcount the degree of the vertex, claim there is at least i edges, when there is fewer), but they will fail the `(not dp[deg(v)][k+1])` clause. This also cannot undercount, (count i, when there is more), because if the RHS of the implication is true, LHS is necessarily true. With "<-" instead of "<->" we get half the number of clauses

So in a group of clauses, that handles the degree constraint, there will be subgroup, handling each vertex. Each such subgroup will constrain the "dp table" using implications and check if `(not dp[deg(v)][k+1])` holds in the end. If it does, the node satisfies the degree constraint

Use the fact that `p -> q ~ (not p) or q`

```
dp[j][i] <- dp[j - 1][i] or (dp[j - 1][i - 1] and e[j]) ~ 
dp[j][i] or ((not dp[j - 1][i]) and (not (dp[j - 1][i - 1]) or (not e[j]))) ~ 
(dp[j][i] or (not dp[j - 1][i])) and (dp[j][i] or not (dp[j - 1][i - 1]) or (not e[j]))
```

Which gives two clauses per implication, so the number of clauses is in 
`O(k|E|)` (where k is the degree constraint).

### Connectivity enforcement

A graph is connected if, and only if there is a path between every two vertices

In an undirected graph, the condition collapses to: every vertex must be reachable from one specific vertex (denote the root as `0`), because a path `u->v` can be constructed by concatenating `u->0` and `0->v`

Procedurally, that would mean inductively checking if every vertex `u` is adjacent to `0`, or if u is adjacent to some node, that is reachable from `0`, let us translate it into logical formulas

A naive `dp[i] <-> dp[adj[i][0]] or ... or dp[adj[i][deg(i) - 1]]` will fail, because `dp[i]` and `dp[j]` can just "satisfy each other", if they are connected, without actually being reachable from `0`

A solution is basically BFS

`dp[i][s] := "is i reachable from 0 in s or less steps?"`

`dp[0][0]` holds

For all `i != 0` `not dp[i][0]` holds

`dp[i][n - 1]` holds for all `i`

So we add these statements we want to hold as unit clauses

Let `adj[i][j]` be the j-th vertex of the graph, adjacent to i

`e[i][j] := "is the edge {i, adj[i][j]} in the tree?"`

`dp[i][s] <-> dp[i][s - 1] or (dp[adj[i][0]][s - 1] and e[i][0]) or ... or
(dp[adj[i][deg(i) - 1]][s - 1] and e[i][deg(i) - 1])`

`dp[i][s] -> dp[i][s - 1] or (dp[adj[i][0]][s - 1] and e[i][0]) or ... or
(dp[adj[i][deg(i) - 1]][s - 1] and e[i][deg(i) - 1])` where `(1 <= s <= n - 1)`
is sufficient, because the invalid states it allows only UNDERcount the connectedness

(`dp[i][s]` can be false, while the RHS expression is true, but this is harmless, because it will never say a graph is connected on a disconnected graph, unlike the "<-", since it can conclude connectedness on a disconnected graph)

You can see how simple distribution will make the formula blow up exponentially with respect to clauses, if simple distributive law is used to convert into CNF

Introduce a variable `c[i][j][s - 1] <-> (dp[adj[i][j]][s - 1] and e[i][j])`

Just the "`->`" is enough, because it allows UNDERcounting of the connected vertices, but importantly, not OVERcounting

```
c[i][j][s - 1] -> (dp[adj[i][j]][s - 1] and e[i][j]) ~
(not c[i][j][s - 1]) or (dp[adj[i][j]][s - 1] and e[i][j]) ~
((not c[i][j][s - 1]) or dp[adj[i][j]][s - 1]) and ((not c[i][j][s - 1]) or e[i][j])
```

So: 

`(not dp[i][s]) or dp[i][s - 1] or c[i][0][s - 1] or ... or c[i][deg(i) - 1][s - 1]`

