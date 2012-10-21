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

In this example, the module itself is imported as:
>  import applications.welcome.modules.stanbol as stanbolmod
>  from applications.welcome.modules.stanbol import default_stanbol_connection as stanbol

And then Apache Stanbol RESTful API is called:
> content = stanbol_contenthub_retrieve(parent_id, media_type="rdf", subresource="edit")  

or, a more advanced query is formated and executed:
    
> 294 def get_formated_enhancements_jsonquery(jsonquery,site=None):

> 295	  #Useful information for enhancements

> 296	  selectedFields = dict(

> 297	                    titlep = "http://purl.uniprot.org/core/title",

> 298	                    title = "http://purl.org/dc/terms/title",

> 299	                    comment = str(RDFS.term("comment")),

> 300	                    label = str(RDFS.term("label")),

> 301	                    mnemonic = "http://purl.uniprot.org/core/mnemonic",

> 302	                    type = str(RDF.term("type")), 

> 303	                    )

> 304	                    

> 305	    jsonquery["selected"]=selectedFields.values()

> 306	    

> 307	    try:

> 308	        qry = stanbol.entityhub_query(jsonquery,site)

> 309	    except Exception as e:

> 310	        qry = str(e)




