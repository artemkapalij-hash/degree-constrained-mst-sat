#!/usr/bin/env python3

import random
import argparse

parser = argparse.ArgumentParser()

parser.add_argument("-n", "--nodes", type=int)
parser.add_argument("-e", "--edges", type=int)
parser.add_argument("-c", "--constraint", type=int)

args = parser.parse_args()

nodes = args.nodes; edges = args.edges; constraint = args.constraint;

print(nodes, edges, constraint)
for _ in range(edges):
    a, b = random.sample(range(nodes), 2)
    print(a, b)

