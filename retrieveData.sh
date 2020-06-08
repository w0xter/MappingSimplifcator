#!/bin/bash
url="https://raw.githubusercontent.com/oeg-upm/morph-csv/evaluation/swj2020-si-webofdata/resources/gtfs/queries/original/"
path="test/gtfs/"
for i in $(seq 1 18)
do
	mkdir ${path}query$i
	wget ${url}q${i}.rq -O ${path}query${i}/query.rq
done
echo "Finish"
