import sys
import BashUtils as bash 
import GeneralUtils as utils
class Sparql:
    def __init__(self, path):
        self.path = path
        self.rawQuery = ""
        self.parsedQuery = {}
        self.uris = {}
        self.splitedQuery = {"tpos":{}, "filter":[]}
        self.filters = []
        self.__readQuery()
        self.__readParseQuery()
        self.__getUrisFromQuery()
        self.__splitQueryIntoTpos(self.parsedQuery["where"])

    def __readQuery(self):
        f = open(self.path, 'r', encoding='utf-8')
        self.rawQuery = f
        f.close()
        
    def __readParseQuery(self):
        parsedQuery = bash.parseSparqlQuery(self.path)
        self.parsedQuery = parsedQuery

    def __getUrisFromQuery(self):
        result = {}
        for el in self.parsedQuery['where']:
            if 'patterns' in el.keys():
                for tp in el['patterns']:
                    if('patterns' in tp.keys()):
                        for tp1 in tp['patterns']:
                            result.update(self.__extractTriplePatternUris(result, tp1))
                    else:
                        result.update(self.__extractTriplePatternUris(result, tp))
            else:
                result.update(self.__extractTriplePatternUris(result, el))
        self.uris = result
        

    def ___extractTriplePatternUris(self, result, el):
        if('triples' in el.keys()):
            for tm in el['triples']:
                subject = tm['subject']['value']
                uri = tm['predicate']['value']
                if(subject not in result.keys()):
                    result[subject] = {'uris':[], 'fullTM':False}
    #                TMOfJoin = getSubjectInsideTPO(s,query)
    #                if(TMOfJoin != '')):
    #                    findSubjectOfJoin(TMOfJoin, mapping)
    #            if(isUri(subject)):
    #               subjectUri = findSubjectInMapping(subject, mapping) TODO
    #                result[subject]['uris'].append(subject)
                if(utils.isUri(uri)):
                    if(uri == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'):
                        uri = tm['object']['value']
                        if not  'http://www.w3.org/1999/02/22-rdf-syntax-ns#type' in result[subject]['uris']:
                            result[subject]['uris'].append('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')
                    if(not uri in result[subject]['uris']):
                        result[subject]['uris'].append(uri)
                else:
                    result[subject]['fullTM'] = True
        return result
    def __extractTriplePatternUris(self, result, el):
        if('triples' in el.keys()):
            for tm in el['triples']:
                subject = tm['subject']
                predicate = tm['predicate']
                _object = tm['object']
                if(subject["value"] not in result.keys()):
                    result[subject["value"]] = {'tpos':[],'includeInstantiation':False, 'fullTM':False}
                result[subject["value"]]['tpos'].append({'s':subject, 'p':predicate, 'o':_object})
        return result        

    def __splitQueryIntoTpos(self, tpos, tpoType="mandatory"):
        createSbuject = lambda subject: {"subjectVar":subject, "mandatory":{"predicates":[], "objects":[]}, "optional":{"predicates":[], "objects":[]}, "filter":[]}
        for tpo in tpos:
            if(tpo["type"] == "bgp"):
                for tp in tpo["triples"]:
                    subject = tp["subject"]["value"]
                    if(subject not in self.splitedQuery.keys()):
                        self.splitedQuery["tpos"][subject] = createSbuject(subject)
                    self.splitedQuery["tpos"][subject][tpoType]["predicates"].append(tp["predicate"]["value"])
                    self.splitedQuery["tpos"][subject][tpoType]["objects"].append(tp["object"]["value"])
            elif(tpo["type"] == "optional"):
               self.__splitQueryIntoTpos(tpo["patterns"], tpoType="optional")
            elif(tpo["type"] == "filter"):
                objects = self.__findObjectsOfFilterArgs(tpo["expression"]["args"])
                for obj in objects:
                    subject = self.__findSubjectOfObject(obj, self.parsedQuery["where"])
                    print(subject)
                    if(subject == ""):
                        print("Review SparqlUtils __splitQueryIntoTpos:L90")
                        sys.exit()
                    if( subject not in self.splitedQuery.keys()):
                        self.splitedQuery[subject] = createSbuject(subject)
                    self.splitedQuery[subject]["filter"].append(tpo["expression"])
            else:
                print(tpo)
                print("Review SparqlUtils __splitQueryIntoTpos:L96")
                sys.exit()

    def __findSubjectOfObject(self, obj, tpos):
        for tpo in tpos:
            if(tpo["type"] == "bgp"):
                for tp in tpo["triples"]:
                    subject = tp["subject"]["value"]
                    if(tp["object"]["value"] == obj):
                        return subject
            elif(tpo["type"] == "optional"):
                subject = self.__findSubjectOfObject(obj, tpo["patterns"])
                if subject != "":
                    return subject
        return ""
    def __findObjectsOfFilterArgs(self, args):
        result= []
        for arg in args:
            if("termType" in arg.keys() and arg["termType"] == "Variable"):
                result.append(arg["value"])
            elif "type" in arg.keys():
                objects =  self.__findObjectsOfFilterArgs(arg["args"])
                if len(objects) > 0:
                    result.extend(objects)
        return result

