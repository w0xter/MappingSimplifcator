import rdflib
import json
import time
import re
import sys

RDFschema = rdflib.Namespace("http://www.w3.org/2000/01/rdf-schema#")
RML = rdflib.Namespace("http://semweb.mmlab.be/ns/rml#")
RR = rdflib.Namespace("http://www.w3.org/ns/r2rml#")
RDF = rdflib.Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
defaultInitNs = {"rdfschema":RDFschema, "rml":RML, "rr":RR}

class Simplificator:
    def __init__(self,queryUris, mapping="test/gtfs/mapping.ttl"):
        self.g = None
        self.rdf = None
        self.subjectsRegex = []
        self.queryUris = queryUris
        self.minGraph = None
        self.__intializeGraph(mapping)
        self.__createSubjectRegexs()
        self.__findSubjectsTm()
        self.__filterMapping()
        self.__buildMinGraph()
    
    '''
        Initializing the rdflib components 
        and parsing the input mapping.
    '''    
    def __intializeGraph(self, mapping):
        self.g = rdflib.Graph()
        self.minGraph = rdflib.Graph()
        self.g.parse(mapping, format="ttl")

    '''
        Building a collection of REGEXs to identify
        the instantiated subjects of a query.
        1. Select the templates and the TM's URIS of each subject 
        2. Build a regex of the subject's template replacing the referenced column annotation: {ColumnName}
        with the regular expression: ([a-zA-Z0-9\-\_]+)
        Example:
         - Subject template: http://example.com/Subject/{colName}
         - REGEX: http://example.com/Subjet/([a-zA-Z0-9\-\_]+)
    '''
    def __createSubjectRegexs(self):
        subjectTemplates = self.g.query("""
        select ?TM ?subject ?template where {
            ?TM a rr:TriplesMap;
            rr:subjectMap ?subject.
            ?subject rr:template ?template.
        }
        """, initNs=defaultInitNs)
        for tm,s,template in subjectTemplates:
            regex = str(re.sub(r'({[A-Za-z0-9_\-]+})','([a-zA-Z0-9\-\_]+)',str(template)))
            self.subjectsRegex.append({'s':s,'tm':str(tm),'regex':regex})

    '''
        Traveling the given query to link the instantiated 
        subjects with the corresponding TM. 
    '''
    def __findSubjectsTm(self):
        result = self.queryUris.copy()
        for i,subject in enumerate(self.queryUris):
            for j,tpo in enumerate(self.queryUris[subject]['tpos']):
                if(tpo['s']['termType'] == 'NamedNode'):
                    subject = str(tpo['s']['value'])
                    for regex in self.subjectsRegex:
                        if(re.search(regex['regex'],subject)):
                            tm = regex['tm']
                            result[subject]['tpos'][j]['s']['value'] = tm
        self.queryUris = result

    '''
        Combining the TriplesMap identified in __findSubjectsTm()
        and the instantiated predicates of the query we build a query
        to construct a new graph only with the PredicateObjectMaps that
        follows the constraints of the query.    

        TODO:
         1. Identify the instantiated objects of the query's TPOs
           They can be a literal or a NamedNode:
            A. If the termtype is a literal we have to identify the datatype of the literal and filter the predicateObjectMaps 
            selecting only those where the datatype of the objectMap correspond with the datatype of the literal.

            B. If the termtype is a NameNode we have to check if it's a Subject or a IRI applying the __findSubjectsTm() algorithm to the Object.
            If we don't find any match we have to apply the previous algorithm (1.A) looking for those PredicateObjectMap where the datatype is an IRI.
            Else we have to find the PredicateObjectMap where the ObjectMap is a Join and the parentTriplesMap is the founded TM.

    '''
    def __filterMapping(self):
        for i,tm in enumerate(self.queryUris.keys()):
            #Checking if the Subject were instantiated
            TM =  "<" + self.queryUris[tm]['tpos'][0]['s']['value'] + ">" if(self.queryUris[tm]['tpos'][0]['s']['termType'] == 'NamedNode') else "?TM_" + str(i)
            construct = "construct {\n"
            where = "} where {\n"            
            where += """%s a rr:TriplesMap.\n"""%(TM)
            construct += """%s a rr:TriplesMap.\n"""%(TM)
            for j,tpo in enumerate(self.queryUris[tm]["tpos"]):                
                construct += """
                %s rr:predicateObjectMap ?pom_%s.
                ?pom_%s a rr:PredicateObjectMap.
                """%(TM,str(i) + str(j),str(i) + str(j))
                where += """%s rr:predicateObjectMap ?pom_%s.\n"""%(TM,str(i) + str(j))
                if(tpo['p']['termType'] == 'NamedNode'):
                    where += """
                    ?pom_%s rr:predicateMap ?p_%s.
                    ?p_%s rr:constant <%s>.
                    """%(
                    str(i) + str(j), 
                    str(i) + str(j),
                    str(i) + str(j),
                    tpo['p']['value']                                    
                    )
                if(tpo['o']['termType'] == 'NamedNode'):
                    print("TO DO Object Instantiation")
                    if(tpo['p']['value'] == RDF.type):
                        where += """
                        ?pom_%s rr:objectMap ?o_%s.
                        ?o_%s rr:constant <%s>.
                        """%(
                        str(i) + str(j), 
                        str(i) + str(j),
                        str(i) + str(j),
                        tpo['o']['value']                                    
                        )                        

            where += "}"
            query = construct + where
            self.__addQueryResultToGraph(query)

    '''
        Adding the childs of the identified URIs in __filterMapping()
    '''
    def __buildMinGraph(self):
        self.__expandPoms()
        self.__expandTMs()
        self.__expandSubjectMaps()
        self.__expandLogicalSource()
        #for tpo in self.minGraph:
        #    print(tpo)

    def __expandPoms(self):
        for POM,p,o in self.minGraph.triples((None, RDF.type, RR.PredicateObjectMap)): #SameAs: select ?POM ?p ?o where {?POM a rr:PredicateObjectMap; ?p ?o.}
            query = """
            construct {
                <%s> ?p ?o.
                ?o ?o_p ?o_o.
                ?parentTM a rr:TriplesMap.
                ?jc ?jc_p ?jc_o.
            }where{
            <%s> ?p ?o.
            ?o ?o_p ?o_o.
            OPTIONAL{
                ?o rr:parentTriplesMap ?parentTM.
                ?o rr:joinCondition ?jc.
                ?jc ?jc_p ?jc_o.
            }  
            }         
            """%(POM,POM)
            self.__addQueryResultToGraph(query)   

    def __expandTMs(self):
        for TM,p,o in self.minGraph.triples((None, RDF.type, RR.TriplesMap)): #SameAs: select ?TM ?p ?o where {?TM a rr:TriplesMap; ?p ?o.}
            query ="""
                construct {
                <%s> rr:subjectMap ?sbjMap.
                ?sbjMap a rr:SubjectMap.
                <%s> rml:logicalSource ?lgsrc.
                ?lgsrc a rml:LogicalSource.
                }
                where {
                <%s> rr:subjectMap ?sbjMap;
                rml:logicalSource ?lgsrc.
                }
            """%(TM,TM,TM)
            self.__addQueryResultToGraph(query)

    def __expandSubjectMaps(self):
        for s,p,o in self.minGraph.triples((None, RDF.type, RR.SubjectMap)): #SameAs: select ?s ?p ?o where {?s a rr:SubjectMap; ?p ?o.}
            query="""
                construct{
                <%s> ?p ?o.
                }where{
                <%s> ?p ?o.
                }
            """%(s,s)
            self.__addQueryResultToGraph(query)

    def __expandLogicalSource(self):
        for s,p,o in self.minGraph.triples((None, RDF.type, RML.LogicalSource)): #SameAs: select ?s ?p ?o where {?s a rml:LogicalSource; ?p ?o.}
            query="""
                construct{
                <%s> ?p ?o.
                }where{
                <%s> ?p ?o.
                }
            """%(s,s)
            self.__addQueryResultToGraph(query)

    def __expandJoinCondition(self):
        for s,p,o in self.minGraph.triples((None, RR.joinCondition, None)): #SameAs: select ?s ?p ?o where {?s a rr:JoinCondition; ?p ?o.}
            query="""
                construct{
                <%s> ?p ?o.
                }where{
                <%s> ?p ?o.
                }
            """%(o,o)
            self.__addQueryResultToGraph(query)

    
    '''
        Executing a Sparql Query and adding the Sparql Result to the simplified Mapping Graph (minGraph)  
    '''
    def __addQueryResultToGraph(self, query):
        #print(query)
        result = self.g.query(query, initNs=defaultInitNs)
        for tpo in result:
            self.minGraph.add(tpo)
    #Serializing the graph to nt
    def __graph_to_nt(self):
        self.g.serialize(format="nt", destination="tmp/min.mapping.nt")
    #Serializing the graph to ttl
    def writeMinGraph(self, path="tmp/min.mapping.ttl"):
        self.minGraph.serialize(format="ttl", destination=path)


