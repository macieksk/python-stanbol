'''
Created on 28 Aug 2012
@author: Maciek Sykulski <macieksk@gmail.com>
'''

import applications.welcome.modules.imidlog as imidlog
#import applications.welcome.modules.commonForms as commonForms

import applications.welcome.modules.stanbol as stanbolmod
from applications.welcome.modules.stanbol import default_stanbol_connection as stanbol

import json
import re
import rdflib
from rdflib import RDF,RDFS

import applications.welcome.modules.stanbol_enhancers 
from applications.welcome.modules.stanbol_enhancers import format_enhancement_short


    
query_enhancer = {
    'id' : 'query_enhance',
    'name' : "Query a site",
    'controller' :"/welcome/stanbol_enhancers/query_enhancer_controller",
    'view' :"/welcome/stanbol_enhancers/query_enhancer_view",
}


entity_enhancer = {
    'id' : 'entity_details',
    'name' : "Fetch details for this entity url",
    'controller' :"/welcome/stanbol_enhancers/entity_data_enhancer_controller",
    'view' :"/welcome/stanbol_enhancers/entity_data_enhancer_view",
}


citation_enhancer = {
    'id' : 'citation_enhancer',
    'name' : "Search publications",
    'controller' :"/welcome/stanbol_enhancers/query_enhancer_controller",
    'view' :"/welcome/stanbol_enhancers/citation_enhancer_view",
}

uniprot_ref_enhancer = {
    'id' : 'uniprot_reference',
    'name' : "Search UNIPROT References",
    'controller' :"/welcome/stanbol_enhancers/uniprot_reference_controller",
    'view' :"/welcome/stanbol_enhancers/uniprot_reference_view",
}

gene_enhancer = {
    'id' : 'gene_enhancer',
    'name' : "UNIPROT Gene Information",
    'controller' :"/welcome/stanbol_enhancers/gene_enhancer_controller",
    'view' :"/welcome/stanbol_enhancers/gene_enhancer_view",
}

personal_note_enhancer = {
    'id' : 'personal_note',
    'name' : "Save a note",
    'controller' :"/welcome/stanbol_enhancers/personal_note_enhancer_controller",
    'view' :"/welcome/stanbol_enhancers/personal_note_enhancer_view",
}

stanbol_enhancements = {
    'id' : 'stanbol_enhancements',
    'name' : "Review automatic enhacements",
    'controller' :"/welcome/stanbol_enhancers/stanbol_enhancements_controller",
    'view' :"/welcome/stanbol_enhancers/stanbol_enhancements_view",
}

vie_autosearch = {
    'id' : 'vie_autosearch',
    'name' : "Search all databases (VIE autocomplete)",
    'controller' :"/welcome/stanbol_enhancers/vie_autosearch_controller",
    'view' :"/welcome/stanbol_enhancers/vie_autosearch_view",
}


all_enhancers = [vie_autosearch,gene_enhancer,citation_enhancer,entity_enhancer,uniprot_ref_enhancer,personal_note_enhancer,query_enhancer]
test_enhancers = [stanbol_enhancements]

#################################3333
# General enhancer utilities

def provide_enhancers():    
    return json.dumps({ 'parent_id' : request.vars.parent_id , 'enhancers' : all_enhancers})    


def enhancer_view_init():                
    response.view = 'stanbol_enhancers/enhancer_view.html'        
    enhancer_id = request.vars.engine
    enhancer_setup = [e for e in (all_enhancers+test_enhancers) if e["id"]==enhancer_id][0]
    parent_id = str(request.vars.parent_id)
    form_id = enhancer_id+'_form'    
    
    return dict(enhancer_id = enhancer_id,
        enhancer_setup = enhancer_setup,        
        parent_id = parent_id, form_id = form_id,
        parent_field = Field('parent_id', 'string',length=3000, default=parent_id),
    )

def form_hide_row(form,form_id,field_name):
    form.element(_id="%s_%s__row"%(form_id,field_name)).attributes["_style"]="visibility:hidden;position:absolute;"      
    

def enhancer_finalize_form(form, enhancer_id = None, enhancer_setup = None, 
                             parent_id = None, form_id=None, parent_field=None):                   
    form_hide_row(form,form_id,"parent_id")        
    form.attributes["_id"] = enhancer_id
    form.attributes["_action"] = enhancer_setup["controller"]
    return form

## Cached versions of some stanbol calls    
    
def stanbol_contenthub_retrieve(parent_id, media_type="rdf", subresource="edit"):
    return cache.memcache('stanbol_contenthub_retrieve_%s_%s_%s'%(str(parent_id),media_type,subresource),
               lambda : stanbol.contenthub_retrieve(parent_id, media_type=media_type, subresource=subresource),
               time_expire=30)
    

def stanbol_entityhub_sites():
    return cache.memcache('stanbol_entityhub_sites',lambda: stanbol.entityhub_sites(),time_expire=3600)
    
    
def __get_ontology_terms_validator(uri="http://purl.uniprot.org/core/",multiple=False,zero=None):
    purl_terms=stanbol.ontonet_get_ontology_terms(uri)
    purl_terms=filter(lambda t:t["@type"]=="Class",purl_terms)
    pt_labels=[t.get("label",t["@subject"]) for t in purl_terms]
    pt_terms=[t["@subject"] for t in purl_terms]
    return IS_IN_SET(pt_terms,labels=pt_labels, zero=zero,multiple=multiple)
    
def get_ontology_terms_validator(uri="http://purl.uniprot.org/core/",multiple=False,zero=None):
    return cache.memcache('onto_terms_%s_%s_'%(str(multiple),str(zero))+uri,lambda:__get_ontology_terms_validator(uri,multiple,zero),time_expire=36000)

    
####################### Enhancers      
        

########## Entity data enhancer

def entity_data_enhancer_view():
    params=enhancer_view_init()
    form=entity_data_enhancer_view_core( **params )
    form=enhancer_finalize_form(form, **params)
    return dict(form=form)

def remove_first_line(s):
    return re.sub("^.*?\n","",s)

def entity_data_enhancer_view_core(enhancer_id = None, enhancer_setup = None, 
                             parent_id = None, form_id=None, parent_field=None): 
        
    content = stanbol_contenthub_retrieve(parent_id, media_type="rdf", subresource="edit")        
    try: 
        js=json.loads(content)
        #Try url content property and the content itself
        url=js.get("url_t",[None])[0]        
        if url is None or url[:4]!="http":
            url=js.get("content",None)
            url=remove_first_line(url)
    except:
        url=None
        
    all_sites = stanbol_entityhub_sites()
    
    form = SQLFORM(SQLDB(None).define_table(form_id,   
                    Field("url","string",length=3000,default=url),
                    parent_field
                    ),
                    submit_button='Entity details')

    form.element(_id="%s_url"%form_id).attributes["_size"]=150
    #if url is None:
        #form.element(_id="submit_record__row").attributes["_style"]="visibility:hidden;position:absolute;"
        #form.element(_id="submit_record__row").components=["No details available for this entity"]
        
    return form 
    

def entity_data_enhancer_controller():    
    response.view = 'tree/provide_enhancements.html'        
        
    enh = []                        
    try:
        r = stanbol.entityhub_entity(request.vars.url) #,site=request.vars.site if request.vars.site is not "" else None)
        if r is not None:                
            res = json.loads(r)   
            del res["representation"]["id"]
            for (relation,values) in res["representation"].items():
                for (i,v) in enumerate(values):                                   
                    enh.append( dict(id = v["type"],
                                title = relation,
                                description = str(v["value"]) ) )
    except Exception as e:
        enh.append( dict(id = request.vars.url, title="There was an error:", description=str(e))  )
        
        
    return dict(parent_id=request.vars.parent_id,
                enhancements=enh, 
                format_enhancement_short=format_enhancement_short)
     

########## Query enhancer    
    
def query_enhancer_view():
    params=enhancer_view_init()
    form=query_enhancer_view_core( **params )
    form=enhancer_finalize_form(form, **params)
    return dict(form=form)
    
#def query_enhancer_controller():
#    form=query_enhancer_controller_core( **enhancer_view_init() )
#    return dict(parent_id=request.vars.parent_id,
#                enhancements=enh, 
#                format_enhancement_short=format_enhancement_short)
    
def define_table_query_form(form_id,parent_field):
    stanbol_query_types = stanbol.query_constraint_type.keys() 
    return SQLDB(None).define_table(form_id,      
                    Field("query","text",length=3000,default=""),
                    Field('mode',"string",requires=IS_IN_SET(["any","all"]),default="any"),                   
                    Field('site',"string",requires=IS_IN_SET(["dbpedia","uniprot"]),default="uniprot"),
                    Field('field',"string",default = stanbolmod.STANBOL_REFS),
                    Field('type',"string",requires=IS_IN_SET(stanbol_query_types),default="similarity"),                                                                
                    Field('result_limit','integer', requires = [IS_NOT_EMPTY(),
                            IS_INT_IN_RANGE(1,3000,error_message="1<=Required result limit <=3000")], 
                            default = 100),
                    Field("additional_constraints","string",length=300,default="[]"),
                    parent_field
                    )
    
def query_enhancer_view_core(enhancer_id = None, enhancer_setup = None, 
                             parent_id = None, form_id=None, parent_field=None):           
                             
    content = stanbol_contenthub_retrieve(parent_id, media_type="rdf", subresource="raw")    
    all_sites = stanbol_entityhub_sites()
    
    stanbol_important_fields = [stanbolmod.STANBOL_REFS,
        RDFS.term("label"),"http://purl.uniprot.org/core/title","http://purl.org/dc/terms/title",
        RDFS.term("comment"),RDFS.term("seeAlso")]
            
    formtable = define_table_query_form(form_id,parent_field)
    
    formtable.query.default = remove_first_line(content)
    formtable.site.requires = IS_IN_SET(all_sites)
    formtable.site.default = "uniprot"
    formtable.field.requires = IS_IN_SET(stanbol_important_fields)
    formtable.field.default = stanbolmod.STANBOL_REFS
    
    form= SQLFORM(formtable,submit_button='Search')
    
    form.element(_id="%s_query"%form_id).attributes["_rows"]="5"                                                                 
    form.element(_id="%s_query"%form_id).attributes["_cols"]="120"
                          
    return form
        
    
    
        
def query_enhancer_controller():    
    response.view = 'tree/provide_enhancements.html'        
   
    if request.vars.has_key("additional_constraints"):
        additional_constraints=json.loads(request.vars.additional_constraints)
    else:
        additional_constraints=[]
        
    jsonquery={
        #"selected" :selectedFields.values(),
        "limit": request.vars.result_limit,
        "constraints": [{
            "field": request.vars.field,
            "type": request.vars.type,
            "mode": request.vars.mode,
        }] + additional_constraints,
    }
    #Add proper value field 
    #"value": request.vars.query,
    #"text": request.vars.query,
    #"context":request.vars.query,        
    jsonquery["constraints"][0][stanbol.query_constraint_type[request.vars.type]] = request.vars.query

    site = request.vars.site if request.vars.site is not "" else None
    
    enh = get_formated_enhancements_jsonquery(jsonquery,site)
    
    return dict(parent_id=request.vars.parent_id,
                enhancements=enh, 
                format_enhancement_short=format_enhancement_short)

    
def get_formated_enhancements_jsonquery(jsonquery,site=None):
    #Useful information for enhancements
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
    
    def __getField(r,fieldList,default="id"):        
        for f in fieldList:
            try: 
                return r[selectedFields[f]][0]["value"]
            except:
                pass        
        return r[default]
                        
    enh = []                
    try:                
        res = json.loads(qry)
        for r in res["results"]:
            enh.append( dict(id =r["id"],
                                title =  __getField(r,["title","titlep","label","mnemonic","type"]),
                                description=__getField(r,["comment","type"]) ) )
    except Exception as e:        
        enh.append( dict(id=qry, title="There was an error:", description=str(e))  )
                    
    return enh
                              

##################################### Citation enhancer

def citation_enhancer_view():
    params=enhancer_view_init()
    form=citation_enhancer_view_core( **params )    
    form=enhancer_finalize_form(form, **params)
    return dict(form=form)
    
                
                
def citation_enhancer_view_core(enhancer_id = None, enhancer_setup = None, 
                             parent_id = None, form_id=None, parent_field=None):           
                             
    content = stanbol_contenthub_retrieve(parent_id, media_type="rdf", subresource="raw")
    
    additional_constraints = [{ 
        "type": "reference", 
        "field": str(RDF.term("type")),
        "value":  "http://purl.uniprot.org/core/Journal_Citation"
    }]
    
    formtable = define_table_query_form(form_id,parent_field)
    
    formtable.query.default = remove_first_line(content)
    formtable.type.default = "similarity"
    formtable.site.default = "uniprot"    
    formtable.field.requires = None
    formtable.field.default = str(RDFS.term("comment"))
    formtable.result_limit.default = 500
    formtable.additional_constraints.default = json.dumps(additional_constraints)
    
    form = SQLFORM(formtable, submit_button='Search')
                                                  
    form.element(_id="%s_query"%form_id).attributes["_rows"]="5"                                                                 
    form.element(_id="%s_query"%form_id).attributes["_cols"]="120"
    
    form_hide_row(form,form_id,"additional_constraints")
    form_hide_row(form,form_id,"site")    
    form_hide_row(form,form_id,"field")
    form_hide_row(form,form_id,"type")
    form_hide_row(form,form_id,"result_limit")
    form_hide_row(form,form_id,"mode")
    
    return form
     
             
def uniprot_reference_view():
    params=enhancer_view_init()
    form=uniprot_reference_view_core( **params )    
    form=enhancer_finalize_form(form, **params)
    return dict(form=form)

def uniprot_reference_controller():    
    response.view = 'tree/provide_enhancements.html'        
    
    jsonquery={
        #"selected" :selectedFields.values(),
        "limit": 500,
        "constraints": [{ 
            "value": request.vars.url,
            "type": "reference", 
            "field": stanbolmod.STANBOL_REFS,
            "mode" : "any",
            }]
        }
    #imidlog.log("ref search "+str(request.vars.searched_type))
    if request.vars.searched_type is not None and request.vars.searched_type != '':
        jsonquery["constraints"].append({
            "value": request.vars.searched_type,
            "type" : "reference",
            "field": str(RDF.term("type")),
            "mode": "any",
            })    
    
    site = "uniprot"    
    enh = get_formated_enhancements_jsonquery(jsonquery,site)
    
    return dict(parent_id=request.vars.parent_id,
                enhancements=enh, 
                format_enhancement_short=format_enhancement_short)
    
    
def uniprot_reference_view_core(enhancer_id = None, enhancer_setup = None, 
                             parent_id = None, form_id=None, parent_field=None):         
    
    content = stanbol_contenthub_retrieve(parent_id, media_type="rdf", subresource="edit")        
    try: 
        js=json.loads(content)
        #Try url content property and the content itself
        url=js.get("url_t",[None])[0]        
        if url is None or url[:4]!="http":
            url=js.get("content",None)
            url=remove_first_line(url)
    except:
        url=None  
           
    terms_validator = get_ontology_terms_validator("http://purl.uniprot.org/core/",multiple=True,zero='')
    
    form = SQLFORM(SQLDB(None).define_table(form_id,   
                    Field("url","string",default=url),
                    Field("searched_type","list:string", requires=terms_validator, default=None),#"http://purl.uniprot.org/core/Protein"),
                    parent_field
                    ),
                    submit_button='Search')
                    
    form.element(_id="%s_url"%form_id).attributes["_size"]=150
                    
    return form

        
    
######################################## Gene names, or ids enhancer

def gene_enhancer_view():
    params=enhancer_view_init()
    form=gene_enhancer_view_core( **params )    
    form=enhancer_finalize_form(form, **params)
    return dict(form=form)
    
    
def gene_enhancer_controller():    
    response.view = 'tree/provide_enhancements.html'        
   
    genes_names=request.vars.genes_names if isinstance(request.vars.genes_names,list) else [request.vars.genes_names];
    
    genelistUP=tuple(gn.strip().upper() for gn in genes_names if len(gn.strip())>0)
    genelist_low=tuple(gn.strip().lower() for gn in genes_names if len(gn.strip())>0)
    
    #imidlog.log("Gene Enhancer: "+str(genelistUP))
    
    geneids=db.executesql(db(db.hgnc.approved_symbol.belongs(genelistUP))._select(db.hgnc.gene_id))
    geneids=geneids+db.executesql(db(db.hgnc.ucsc_id.belongs(genelist_low))._select(db.hgnc.gene_id))

    imidlog.log("Gene Enhancer: "+str(geneids))
    
    genevalues=["http://purl.uniprot.org/geneid/%s"%str(gid[0]) for gid in geneids if gid[0]!='']
    
    jsonquery={
        #"selected" :selectedFields.values(),
        "limit": 500,
        "constraints": [{ 
            "value": genevalues,
            "type": "reference", 
            "field": stanbolmod.STANBOL_REFS,
            "mode" : "any",
            }],
    }
    
    if request.vars.searched_type != '':
        jsonquery["constraints"].append({
            "value": request.vars.searched_type,
            "type" : "reference",
            "field": str(RDF.term("type")),
            "mode": "any",
            })
    
    imidlog.log("Gene Enhancer: "+str(jsonquery))    
    
    site = "uniprot"    
    enh = get_formated_enhancements_jsonquery(jsonquery,site) if len(genevalues)>0 else []
    
    return dict(parent_id=request.vars.parent_id,
                enhancements=enh, 
                format_enhancement_short=format_enhancement_short)
    
    
def gene_enhancer_view_core(enhancer_id = None, enhancer_setup = None, 
                             parent_id = None, form_id=None, parent_field=None):         
    
    content = stanbol_contenthub_retrieve(parent_id, media_type="rdf", subresource="edit")        
    try: 
        js=json.loads(content)
        genelist=remove_first_line(js.get("content",''))
        genelist=[gn.strip().upper() for gn in genelist.split(',')]        
    except:
        url=None  
           
    terms_validator = get_ontology_terms_validator("http://purl.uniprot.org/core/",multiple=False,zero='')
    
    form = SQLFORM(SQLDB(None).define_table(form_id,   
                    Field("genes_names","list:string",#requires=IS_IN_SET(genelist,multiple=True,zero=None),
                                                      default=genelist),
                    Field("searched_type","string", requires=terms_validator, default="http://purl.uniprot.org/core/Protein"),
                    parent_field
                    ),
                    submit_button='Search')
                    
    return form    
    
######################################## Personal note

def personal_note_enhancer_view():
    params=enhancer_view_init()
    form=personal_note_enhancer_view_core( **params )    
    form=enhancer_finalize_form(form, **params)
    return dict(form=form)
    
    
def personal_note_enhancer_controller():    
    response.view = 'tree/provide_enhancements.html'        
    
    desc=request.vars.description+"\n\n---note regarding content:%s"%str(request.vars.parent_id)
    
    enh = [dict(id=request.vars.url,
                title = request.vars.title,
                description=desc)]
    
    return dict(parent_id=request.vars.parent_id,
                enhancements=enh, 
                format_enhancement_short=format_enhancement_short)
    
    
def personal_note_enhancer_view_core(enhancer_id = None, enhancer_setup = None, 
                             parent_id = None, form_id=None, parent_field=None):         
    
    form = SQLFORM(SQLDB(None).define_table(form_id,   
                    Field("url","string",default='http://purl.uniprot.org/'),
                    Field("title","string",default="My Note"),
                    Field("description","text",default="..."),                    
                    parent_field
                    ),
                    submit_button='Note it')
    form.element(_id="%s_url"%form_id).attributes["_size"]=150
    form.element(_id="%s_title"%form_id).attributes["_size"]=150
    
    return form    

    
################################ Retrieve Apache Stanbol enhacements added automatically
def stanbol_enhancements_view():
    params=enhancer_view_init()
    form=stanbol_enhancements_view_core( **params )    
    #form=enhancer_finalize_form(form, **params)
    return dict(form=form)

def stanbol_enhancements_view_core(enhancer_id = None, enhancer_setup = None, 
                             parent_id = None, form_id=None, parent_field=None):             
    meta=stanbol.contenthub_retrieve(parent_id, media_type="rdf", subresource="metadata")
    
    js=stanbolmod.rdf_to_json(meta)
    
    selectedFields = dict(
                    titlep = "http://purl.uniprot.org/core/title",
                    title = "http://purl.org/dc/terms/title",
                    comment = str(RDFS.term("comment")),
                    label = str(RDFS.term("label")),
                    mnemonic = "http://purl.uniprot.org/core/mnemonic",
                    type = str(RDF.term("type")), 
                    )                          
                    
    def __getField(r,fieldList,default="id"):        
        for f in fieldList:
            try: 
                return r[selectedFields[f]][0]["value"]
            except:
                pass        
        return r[default]
    
    
    enh = []                
    try:                
        res = json.loads(qry)
        for r in res["results"]:
            enh.append( dict(id =r["id"],
                                title =  __getField(r,["title","titlep","label","mnemonic","type"]),
                                description=__getField(r,["comment","type"]) ) )
    except Exception as e:        
        enh.append( dict(id=qry, title="There was an error:", description=str(e))  )
                    
    #[ 
    # for (k,v) in js.iteritems() if not k.startswith("urn:enhancement")]
        
    #fields = [Field("E%d"%i,"string",default=url,writable=False) for (i,url) in enumerate(md)]
    
    #def_tab_args=[form_id]+fields+[parent_field]    
    #form = SQLFORM(SQLDB(None).define_table(*def_tab_args),
    #                submit_button='Review&Accept')
    return form

def stanbol_enhancements_controller():   
    response.view = 'tree/provide_enhancements.html'        
        
    enh = [dict(id=request.vars.url,
                title = request.vars.title,
                description=desc)]
    
    return dict(parent_id=request.vars.parent_id,
                enhancements=enh, 
                format_enhancement_short=format_enhancement_short)
                
                
######################################## VIE autosearch

def vie_autosearch_view():
    params=enhancer_view_init()
    response.view = 'stanbol_enhancers/enhancer_view.html'        
    form=vie_autosearch_view_core( **params )    
    form=enhancer_finalize_form(form, **params)          
    #script=SCRIPT(script_body,_type="text/javascript")    
    return dict(form=form) 
    
    
def vie_autosearch_controller():    
    response.view = 'tree/provide_enhancements.html'                
    
    enh = [dict(id=request.vars.selected_entity,
                title = request.vars.search_text,
                description=request.vars.search_text)]
    
    return dict(parent_id=request.vars.parent_id,
                enhancements=enh, 
                format_enhancement_short=format_enhancement_short)
    
    
def vie_autosearch_view_core(enhancer_id = None, enhancer_setup = None, 
                             parent_id = None, form_id=None, parent_field=None):         
    
    form = SQLFORM(SQLDB(None).define_table(form_id,   
                    Field("search_text","string"),
                    Field("selected_entity","string"),                    
                    #Field("you_have_selected","string",writable=False),
                    parent_field
                    ),
                    submit_button='Check it')
    form.element(_id="%s_search_text"%form_id).attributes["_size"]=80
    form.element(_id="%s_selected_entity"%form_id).attributes["_size"]=80
    
    return form   
    