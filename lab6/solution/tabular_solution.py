'''
Adapted on Feb 2025

@author: ejimenez-ruiz
'''
import sys
#To import libraries in the parent folder
sys.path.append("../")
from rdflib import Graph
from rdflib import URIRef, BNode, Literal
from rdflib import Namespace
from rdflib.namespace import OWL, RDF, RDFS, FOAF, XSD
from rdflib.util import guess_format
import pandas as pd
from isub import isub
from lookup import DBpediaLookup
import csv
import owlrl



class TabularKGSolution(object):
    '''
    Example of a partial solution for Lab 4 
    '''
    def __init__(self, input_file):
   
        #The idea is to cover as much as possible from the original csv file, but for the lab and coursework I'm more interested 
        #in the ideas and proposed implementation than covering all possible cases in all rows (a perfect solution fall more into
        #the score of a PhD project). Also in terms of scalability calling the 
        #look-up services may be expensive so if this is a limitation, a solution tested over a reasonable percentage of the original 
        #file will be of course accepted.        
        self.file = input_file
    
        #Dictionary that keeps the URIs. Specially useful if accessing a remote service to get a candidate URI to avoid repeated calls
        self.stringToURI = dict()
        
        
        #1. GRAPH INITIALIZATION
    
        #Empty graph
        self.g = Graph()
        
        #Note that this is the same namespace used in the ontology "ontology_worldcities.ttl"
        self.wco_ns_str= "http://www.semanticweb.org/ernesto/in3067-inm713/wco/"
        
        #Special namspaces class to create directly URIRefs in python.           
        self.wco = Namespace(self.wco_ns_str)
        
        #Prefixes for the serialization
        self.g.bind("wco", self.wco) #wco is a newly created namespace
        self.g.bind("dbr", "http://dbpedia.org/resource/") 
        
        #Load data in dataframe  
        self.data_frame = pd.read_csv(self.file, sep=',', quotechar='"',escapechar="\\")    
    
        
        #KG
        self.dbpedia = DBpediaLookup()
    
    
    
    def performTask4stars(self):
        self.CovertCSVToRDF(False)
        
    def performTask5stars(self):
        self.CovertCSVToRDF(True)

    
    def SimpleUniqueMapping(self):
        #This mapping creates an several transformations (i.e., triples) in one go.
        #Unlike the modular approach (see ConvertCSVToRDF) this solution is less flexible to adaptations  
        
        #Format:
        #0        1             2    3        4        5        6        7            8         9
        #city     city_ascii    lat  lng    country    iso2    iso3    admin_name    capital    population                        
        for row in self.data_frame.itertuples(index=False):
            #print(row[0])
                                    
            #we avoid NaN values, one could add more safety filters. This case is problematic in this dataset                            
            if (self.is_nan(row[1]) or self.is_nan(row[4])): 
                continue
                
            entity_city_uri = self.wco_ns_str + row[1].lower().replace(" ", "_").replace("(", "").replace(")", "")
            entity_country_uri = self.wco_ns_str + row[4].lower().replace(" ", "_").replace("(", "").replace(")", "")
                                
            #Types triples
            #Using self.wco.City is equivalent to using URIRef(self.wco_ns_str = "City")
            self.g.add((URIRef(entity_city_uri), RDF.type, self.wco.City))     #e.g. wco:london rdf:type wco:City
            self.g.add((URIRef(entity_country_uri), RDF.type, self.wco.Country))  #e.g. wco.united_kingdom rdf:type wco:Country
        
            #City Names triples            
            self.g.add((URIRef(entity_city_uri), self.wco.name_ascii, Literal(row[1], datatype=XSD.string)))
            if (not self.is_nan(row[0])):
                self.g.add((URIRef(entity_city_uri), self.wco.name, Literal(row[0], datatype=XSD.string)))
            if (not self.is_nan(row[7])):
                self.g.add((URIRef(entity_city_uri), self.wco.admin_name, Literal(row[7], datatype=XSD.string)))
                       
                       
            #Lat & long
            if (not self.is_nan(row[2])):
                self.g.add((URIRef(entity_city_uri), self.wco.latitude, Literal(row[2], datatype=XSD.float)))
            if (not self.is_nan(row[3])):
                self.g.add((URIRef(entity_city_uri), self.wco.longitude, Literal(row[3], datatype=XSD.float)))
            
            #population
            if (not self.is_nan(row[9])):
                self.g.add((URIRef(entity_city_uri), self.wco.population, Literal(row[9], datatype=XSD.long)))
                       
            
            #Country name triple            
            self.g.add((URIRef(entity_country_uri), self.wco.name, Literal(row[4], datatype=XSD.string)))
            
        
            #iso codes
            if (not self.is_nan(row[5])):
                self.g.add((URIRef(entity_country_uri), self.wco.iso2code, Literal(row[5], datatype=XSD.string)))
            if (not self.is_nan(row[6])):
                self.g.add((URIRef(entity_country_uri), self.wco.iso3code, Literal(row[6], datatype=XSD.string)))
             
             
            
            #Connection between cities and countries
            
            #Basic connection ignoring column "capital":                        
            #self.g.add((URIRef(entity_city_uri), self.wco.cityIsLocatedIn, URIRef(entity_country_uri)))
            
            
            #Exploiting 'capital' column (it can be empty)            
                
            #(default) if value is empty or not expected
            predicate = self.wco.cityIsLocatedIn
                
            if row[8]=="admin":                      
                predicate = self.wco.isFirstLevelAdminCapitalOf
            elif row[8]=="primary":
                predicate = self.wco.isCapitalOf                        
            elif row[8]=="minor":
                predicate = self.wco.isSecondLevelAdminCapitalOf
                
            
            #Note that the ontology in contains a hierarchy of properties, range and domain axioms and inverses
            #Via reasoning this triple will lead to several entailments
            self.g.add((URIRef(entity_city_uri), predicate, URIRef(entity_country_uri)))
            
        


    def CovertCSVToRDF(self, useExternalURI):
                 
        #In a large ontology one would need to find a more automatic way to use the ontology vocabulary. 
        #E.g.,  via matching. In a similar way as we match entities to a large KG like DBPedia or Wikidata
        #Since we are dealing with very manageable ontologies, we can integrate their vocabulary 
        #within the code. E.g.,: wco.City
        
        
        #We modularize the transformation to RDF. The transformation is tailored to the given table, but 
        #the individual components/mappings are relatively generic (especially type and literal triples).
        
        #Mappings may required one or more columns as input and create 1 or more triples for an entity
        
        
        if 'country' in self.data_frame:
            
            #We give subject column and target type
            self.mappingToCreateTypeTriple('country', self.wco.Country, useExternalURI)
            
            #We give subject and object columns (they could be the same), predicate and datatype 
            self.mappingToCreateLiteralTriple('country', 'country', self.wco.name, XSD.string)
            
            
            if 'iso2' in self.data_frame:
                self.mappingToCreateLiteralTriple('country', 'iso2', self.wco.iso2code, XSD.string)
            
            if 'iso3' in self.data_frame:
                self.mappingToCreateLiteralTriple('country', 'iso3', self.wco.iso3code, XSD.string)
            
            
                
        if 'city_ascii' in self.data_frame:
            self.mappingToCreateTypeTriple('city_ascii', self.wco.City, useExternalURI)
            self.mappingToCreateLiteralTriple('city_ascii', 'city_ascii', self.wco.name_ascii, XSD.string)
        
        
            if 'city' in self.data_frame:
                self.mappingToCreateLiteralTriple('city_ascii', 'city', self.wco.name, XSD.string)

            
            if 'admin_name' in self.data_frame:
               self.mappingToCreateLiteralTriple('city_ascii', 'admin_name', self.wco.admin_name, XSD.string)
        
        
            
            if 'lat' in self.data_frame:
                self.mappingToCreateLiteralTriple('city_ascii', 'lat', self.wco.latitude, XSD.float)
                
            if 'lng' in self.data_frame:
                self.mappingToCreateLiteralTriple('city_ascii', 'lng', self.wco.longitude, XSD.float)
                
            if 'population' in self.data_frame:
                self.mappingToCreateLiteralTriple('city_ascii', 'population', self.wco.population, XSD.long)
        
            
            
            if 'capital' in self.data_frame:
                #Special tailored mapping. We give column for subjects and objects 
                #and the column including the type of capital                
                self.mappingToCreateCapitalTriple('city_ascii', 'country', 'capital')
                
                #Alternative simpler mapping, but it does not consider capital information
                #self.mappingToCreateObjectTriple('city_ascii', 'country', self.wco.cityIsLocatedIn)

        
    
    def processLexicalName(self, name):
        #Remove potential spaces and other characters not allowed in URIs
        
        #This method may need to be extended
        #Other problematic characters: 
        #{", "}", "|", "\", "^", "~", "[", "]", and "`"
        return name.replace(" ", "_").replace("(", "").replace(")", "")
        
        
        
          
    def createURIForEntity(self, name, useExternalURI):
        
        #We create fresh URI (default option)
        self.stringToURI[name] = self.wco_ns_str + self.processLexicalName(name)
        
        if useExternalURI: #We connect to online KG
            uri = self.getExternalKGURI(name)
            if uri!="":
                self.stringToURI[name]=uri
        
        return self.stringToURI[name]
    
    
        
    def getExternalKGURI(self, name):
        '''
        Approximate solution: We get the entity with highest lexical similarity
        The use of context may be necessary in some cases        
        '''
        
        entities = self.dbpedia.getKGEntities(name, 5)
        #print("Entities from DBPedia:")
        current_sim = -1
        current_uri=''
        for ent in entities:           
            isub_score = isub(name, ent.label) 
            if current_sim < isub_score:
                current_uri = ent.ident
                current_sim = isub_score
        
            #print(current_uri)
        return current_uri 
            
    
    '''
    Mapping to create triples like wco:London rdf:type wco:City
    A mapping may create more than one triple
    column: columns where the entity information is stored
    useExternalURI: if URI is fresh or from external KG
    '''
    def mappingToCreateTypeTriple(self, subject_column, class_type, useExternalURI):
        
        for subject in self.data_frame[subject_column]:
                
            #We use the ascii name to create the fresh URI for a city in the dataset
            if subject.lower() in self.stringToURI:
                entity_uri=self.stringToURI[subject.lower()]
            else:
                entity_uri=self.createURIForEntity(subject.lower(), useExternalURI)
            
            #TYPE TRIPLE
            #For the individuals we use URIRef to create an object "URI" out of the string URIs
            #For the concepts we use the ones in the ontology and we are using the NameSpace class
            #Alternatively one could use URIRef(self.wco_ns_str+"City") for example 
            self.g.add((URIRef(entity_uri), RDF.type, class_type))
        

                        
            


    def is_nan(self, x):
        return (x != x)
            
            
    '''
    Mappings to create triples of the form wco:london wco:name "London"
    '''    
    def mappingToCreateLiteralTriple(self, subject_column, object_column, predicate, datatype):
        
        for subject, lit_value in zip(self.data_frame[subject_column], self.data_frame[object_column]):
            
            if self.is_nan(lit_value) or lit_value==None or lit_value=="":
                pass
            
            else:
                #Uri as already created
                entity_uri=self.stringToURI[subject.lower()]
                    
                #Literal
                lit = Literal(lit_value, datatype=datatype)
                
                #New triple
                self.g.add((URIRef(entity_uri), predicate, lit))
            
    '''
    Mappings to create triples of the form wco:london wco:cityIsLocatedIn wco:united_kingdom
    '''
    def mappingToCreateObjectTriple(self, subject_column, object_column, predicate):
        
        for subject, object in zip(self.data_frame[subject_column], self.data_frame[object_column]):
            
            if self.is_nan(object):
                pass
            
            else:
                #Uri as already created
                subject_uri=self.stringToURI[subject.lower()]
                object_uri=self.stringToURI[object.lower()]
                    
                #New triple
                self.g.add((URIRef(subject_uri), predicate, URIRef(object_uri)))
            
    
    
    def mappingToCreateCapitalTriple(self, subject_column, object_column, capital_value_column):
        
        for subject, object, value in zip(self.data_frame[subject_column], self.data_frame[object_column], self.data_frame[capital_value_column]):
            
            #URI as already created
            subject_uri=self.stringToURI[subject.lower()]
            object_uri=self.stringToURI[object.lower()]
            
            
            #(default) if value is empty or not expected
            predicate = self.wco.cityIsLocatedIn
            
            if value=="admin":                      
                predicate = self.wco.isFirstLevelAdminCapitalOf
            elif value=="primary":
                predicate = self.wco.isCapitalOf                        
            elif value=="minor":
                predicate = self.wco.isSecondLevelAdminCapitalOf
            
            
            #New triple
            #Note that the ontology contains a hierarchy of properties, range and domain axioms and inverses
            #Via reasoning this triple will lead to several entailments
            self.g.add((URIRef(subject_uri), predicate, URIRef(object_uri)))
    
    
    
    def performReasoning(self, ontology_file):
        
        #We expand the graph with the inferred triples
        #We use owlrl library with OWL2 RL Semantics (instead of RDFS semantic as we saw in lab 4)
        #More about OWL 2 RL Semantics in lecture/lab 7
        
        print("Data triples from CSV: '" + str(len(self.g)) + "'.")
    
    
        #We should load the ontology first
        #print(guess_format(ontology_file))
        self.g.parse(ontology_file,  format=guess_format(ontology_file)) #e.g., format=ttl
        
        
        print("Triples including ontology: '" + str(len(self.g)) + "'.")
        
        
        #We apply reasoning and expand the graph with new triples 
        owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(self.g)
        
        print("Triples after OWL 2 RL reasoning: '" + str(len(self.g)) + "'.")
    
    
    
    
        
    
    
    def saveGraph(self, file_output):
        
        ##SAVE/SERIALIZE GRAPH
        #print(self.g.serialize(format="turtle").decode("utf-8"))
        self.g.serialize(destination=file_output, format='ttl')
        
        
    
    
    

if __name__ == '__main__':
    
    #Format:
    #city    city_ascii    lat    lng    country    iso2    iso3    admin_name    capital    population
    file = "../data/worldcities-free-100.csv"
    output_file_name = "worldcities-free-100"
    
    solution = TabularKGSolution(file)
    
    task = "task4stars"
    #task = "task5stars"
    task = "Simple_Mapping"
    
    #Create RDF triples
    if task == "task4stars":
        solution.performTask4stars()  #Fresh entity URIs
    elif task == "task5stars":
        solution.performTask5stars()  #Reusing URIs from DBPedia
    else:
        solution.SimpleUniqueMapping()  #Simple and unique mapping/transformation
        
    
    #Graph with only data
    solution.saveGraph("./data/"+output_file_name+"-"+task+".ttl")
    
    #OWL 2 RL reasoning
    solution.performReasoning("../data/ontology_worldcities.ttl") ##ttl format
    
    #Graph with ontology triples and entailed triples       
    solution.saveGraph("./data/"+output_file_name+"-"+task+"-reasoning.ttl")
    
    
    
    
    
    
     



