import re
def isUri(uri):
    return str(uri)[:4] == 'http'

def checkEmptyUris(uris):
    for tm in uris:
        if(len(uris[tm]) > 0):
            return False
    return True
def getUrisFromTM(tm):
    result = [tm['s']]
    for po in tm['po']:
        if(type(po) is list):
            result.extend(po)
        else:
            result.append(po['p'])
    return result

def isPoInUris(po, uris):
    if(type(po) is dict):
        po = [po['p']]
    for item in po:
        if item in uris:
            return True
    return False
def getJoinReferences(join):
    result = {'innerRef': join['condition']['parameters'][0][1], 'outerRef':join['condition']['parameters'][1][1]}
    return result    

def getColPatterns(element):
    colPattern  = "\$\(([^)]+)\)"
    matches = re.findall(colPattern, str(element))
    result = [ '$(' + str(match) + ')' for match in matches]
    return result

def cleanColPattern(columns):
    if type(columns) is dict:
        columns = [columns]
    columns = getColPatterns(columns)
    #print('COLUMNS:' + str(columns))
    result = []
    for col in columns:
        result.append(str(col)[2:-1])
    return result
def getLastElementFromUri(uri):
    result = str(uri).split("/")[-1]
    result = result.replace("#", "")
    return result