#!/bin/bash

nodes=$1
edges=$2
constraint=$3

i=0

while python3 generate_case.py -n $nodes -e $edges -c $constraint > in.txt && ! python3 solver.py -i in.txt -o o; do
    i=$((i+1))
    echo $i:
done
