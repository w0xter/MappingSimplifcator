import os
import json

def parseSparqlQuery(path):
    try:
        os.system("bash bash/sparqlQueryParser.sh %s"%(str(path)))
        result = json.loads(open('tmp/sparql.json', encoding='utf-8').read())
        return result
    except:
        raise Exception('Invalid query!')