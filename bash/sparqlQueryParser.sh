#!/bin/bash
file=$1
sparqljs $file > tmp/sparql.json
wait
