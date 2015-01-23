python-stanbol
==============

A connection module  in python to some of Apache Stanbol's components RESTful API. Uses lib "requests".

---

* stanbol.py - the module itself, should work out of the box.

--- 
An example of usage:
* stanbol_enhancers.py  - this is an example of a controller taken out from a site build on http://web2py.com.
This one will not work by itself, as it needs to be put inside a web2py site.
However this may help you figure out how to use stanbol.py.

The module itself is imported as:

    import applications.welcome.modules.stanbol as stanbolmod
    from applications.welcome.modules.stanbol import default_stanbol_connection as stanbol

and then Apache Stanbol RESTful API is called:

    content = stanbol_contenthub_retrieve(parent_id, media_type="rdf", subresource="edit")  

or, a more advanced query is formated and executed:
    
    def get_formated_enhancements_jsonquery(jsonquery,site=None):
        #Retrieve useful information for enhancements
        
        selectedFields = dict(
            titlep = "http://purl.uniprot.org/core/title",
            title = "http://purl.org/dc/terms/title",
            comment = str(RDFS.term("comment")),
            label = str(RDFS.term("label")),
            mnemonic = "http://purl.uniprot.org/core/mnemonic",
            type = str(RDF.term("type")), 
            )
            
        jsonquery["selected"]=selectedFields.values()
        try:
            qry = stanbol.entityhub_query(jsonquery,site)
        except Exception as e:
            qry = str(e)
