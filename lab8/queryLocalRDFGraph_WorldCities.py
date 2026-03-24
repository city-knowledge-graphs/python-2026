'''
Created on 07 March 2025

@author: ejimenez-ruiz
'''
from rdflib import Graph
from rdflib.util import guess_format
import owlrl


def queryLocalGraph():

    #Example from  https://www.stardog.com/tutorials/data-model/
   
    #Loads KG
    g = Graph()
    g.parse("./data/worldcities-free-100-task4stars.ttl", format="ttl")
  
    
    print("Loaded '" + str(len(g)) + "' triples.")
    
    #for s, p, o in g:
    #    print((s.n3(), p.n3(), o.n3()))
    
        
    print("Cities:")
    
    qres = g.query(
    """SELECT ?city where {
      ?city rdf:type wco:City .      
    }
    LIMIT 10""")
    

    for row in qres:
        #Row is a list of matched RDF terms: URIs, literals or blank nodes
        print("%s is a City" % (str(row.city)))
        
   
    #Solution
    performReasoning(g, "./data/ontology_worldcities.ttl")
    performSPARQLQuery(g, "./data/query_result_world_cities.csv")



#Solution reasoning
def performReasoning(g, ontology_file):
    
    #We expand the graph with the inferred triples
    #We use owlrl library with OWL2 RL Semantics
    
    print("\nPerforming reasoning")
    
    #We should load the ontology first
    g.parse(ontology_file,  format=guess_format(ontology_file)) #e.g., format=ttl
    
    print("Triples including ontology: '" + str(len(g)) + "'.")
    
    
    #We apply reasoning and expand the graph with new triples 
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(g)
    
    print("Triples after OWL 2 RL reasoning: '" + str(len(g)) + "'.")


#Solution query results to CSV
def performSPARQLQuery(g, file_query_out):

    print("\nQuerying for cities with population > 5000000");
    
    qres = g.query(
        """SELECT DISTINCT ?country ?city ?pop WHERE {
            ?city rdf:type wco:City .
            ?city wco:isCapitalOf ?country .
            ?city wco:population ?pop .
            FILTER (xsd:integer(?pop) > 5000000)
    }
    ORDER BY DESC(?pop)
    """)
    
    
    print("%s capitals satisfying the query." % (str(len(qres))))
    print("Saving the following lines in the CSV file '%s'." % file_query_out)

    f_out = open(file_query_out,"w+")
    
    for row in qres:
        #Row is a list of matched RDF terms: URIs, literals or blank nodes
        line_str = '\"%s\",\"%s\",\"%s\"\n' % (row.country, row.city, row.pop)
        print(line_str)
        
        f_out.write(line_str)
    
    f_out.close()

    
queryLocalGraph()
