import argparse
from SparqlUtils import Sparql
from MappingSimplificator import Simplificator

def main():
    directory = "./test/gtfs/"
    mapping = directory + "mapping.rml.ttl"
    for i in range(2, 3):
        queryPath = directory + "query%s/"%(str(i))
        sparql  = Sparql(queryPath + "query.rq" )
        mappingSimplificator = Simplificator(sparql.uris, mapping=mapping)
        mappingSimplificator.writeMinGraph(queryPath+"mapping.ttl")
if(__name__ == '__main__'):
    main()