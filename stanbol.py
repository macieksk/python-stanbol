'''
Created on 20 Aug 2012
@author: Maciek Sykulski <macieksk@gmail.com>
'''

import sys
import requests
import httplib
import re
import json
from functools import wraps

import rdflib
from rdflib import RDF,RDFS


# Useful constants    

stanbol_default_url = "http://localhost:8080"

stanbol_default_header = {'Content-Type': 'application/json'}

stanbol_default_base_headers = {'Accept': '*/*',
 'Accept-Encoding': 'identity, deflate, compress, gzip',
 'User-Agent': 'python-requests'}

stanbol_default_request_config  = {
    'base_headers': stanbol_default_base_headers,
    'decode_unicode': True,
    'keep_alive': True,
    'max_redirects': 10,
    'max_retries': 0,
    'pool_connections': 300,
    'pool_maxsize': 300,
    'safe_mode': False,
    'verbose': False }#sys.stderr } 
stanbol_default_connect_timeout = 20
stanbol_default_timeout = 30
        
 
### RDF terms used by stanbol
STANBOL_REFS = 'http://stanbol.apache.org/ontology/entityhub/query#references'


class Stanbol(object):    
    stanbol_url = stanbol_default_url
        
    # Defines mapping between query type and content field -- entityhub
    # Range query has to be handled differently
    query_constraint_type = {"reference":"value", "text":"text","value":"value", 
                            "similarity":"context"}   
    
    last_request = None #Warning! Not thread-safe!

    rsession = None
    
    def __init__(self, **d):
        '''
        url - Stanbol url, or default if None.
        Basically a call to:
        requests.Session(self, headers=None, cookies=None, auth=None, timeout=None, proxies=None, hooks=None, params=None, config=None, prefetch=True, verify=True, cert=None)
        with default config and timeout 
        '''
        if d.has_key("url"):
            self.stanbol_url=d["url"]
            del d["url"]
            
        d["config"] = d.get("config", stanbol_default_request_config)
        d["timeout"] = d.get("timeout",stanbol_default_timeout)
        
        self.rsession=requests.Session(**d)

        
    def _get_allowed_fun(self,fstr, 
                    allowed_fun = dict( (f,f) for f in ["get","post","put","delete"]),
                    ):
        ''' Just to throw exception when wrong http method is used '''
        return allowed_fun[fstr.lower()]
    
    def call_stanbol_request(self,fstr,furl,
                data = None, files = None,
                headers = None,
                allow_redirects=True,
                config = None,
                ):
        
        url = self.stanbol_url+"/"+furl            
        if headers is None: headers = stanbol_default_header
    
        #req_f = requests.__dict__[fstr]
        fstr = self._get_allowed_fun(fstr)        
        req_f = self.rsession.__getattribute__(fstr)
        r = req_f(url, 
                  data=data, headers=headers, files=files,
                  allow_redirects=allow_redirects,
                  config = config)
                  #config = self.stanbol_request_config,
                  #timeout = self.stanbol_connect_timeout)
                      
        #was_redirect=len(r.history)>0
        self.last_request = r #Not thread-safe!
        return r
    

    def call_stanbol_pycurl(self,fstr,furl,
                data = None, files = None,
                headers = stanbol_default_header,
                ):
        ''' Implementation of stanbol call with pycurl. 
        Used to be useful because of some problems with requests, now obsolete.
        '''
        import pycurl, urllib, cStringIO
    
        c = pycurl.Curl()
    
        tolist=lambda x: (x if isinstance(x,list) 
                    else x.items() if isinstance(x,dict) else [])
        headers = tolist(headers)                
        headers = [h[0]+":"+h[1] for h in headers]        
    
        fstr = self._get_allowed_fun(fstr)
        fields = tolist(data)
        files  = tolist(files)
    
        url = self.stanbol_url+"/"+furl    
    
        def give_file_from_tuple(f):
            if isinstance(f[1],str):
                return (pycurl.FORM_FILE, f[1])#,pycurl.FORM_CONTENTTYPE,'application/x-www-form-urlencoded') 
            elif isinstance(f[1],tuple): 
                return (pycurl.FORM_CONTENTS, f[1][1])#,pycurl.FORM_CONTENTTYPE,'application/x-www-form-urlencoded')  
            else:
                raise Exception('''call_stanbol_pycurl: files shall be given as either 
                                            1) [(varname,filename),...]
                                            2) [(varname,(filename,contents)),...]\n''')
    
        if fstr ==  "get": 
            url = url + '?' + urllib.urlencode(fields)
        elif fstr == "post":        
            if len(files)>0:
                files = [(f[0], give_file_from_tuple(f)) for f in files] 
                fields = fields + files
            c.setopt(c.HTTPPOST, fields)
        
        c.setopt(c.VERBOSE, 1)        
        c.setopt(c.URL, url)
        c.setopt(c.HTTPHEADER,  headers)
    
        buf = cStringIO.StringIO()
        c.setopt(c.WRITEFUNCTION, buf.write)  
    
        c.setopt(c.CONNECTTIMEOUT, stanbol_default_connect_timeout)
        c.setopt(c.TIMEOUT, stanbol_default_timeout)
    
        c.perform()
        c.close()
    
        val = buf.getvalue()
        #print val
        buf.close()
        return val

    
    call_stanbol = call_stanbol_request
    #call_stanbol = call_stanbol_pycurl
    
    def last_status(self): #Not thread-safe!        
        return self.last_request.status_code if self.last_request is not None else None
        
    def check_status_ok(self,request=None,
                        errorfun=None,
                        okstatus=httplib.OK):
        '''Watch out with this one - Stanbol status HTTP codes may change in the future! '''
        status = (request if request is not None else self.last_request).status_code
        
        if status != okstatus: 
            if errorfun is None: self.errorfun(status,okstatus)
            else: errorfun(status,okstatus)
            return False
        else:
            return True 
    
    def errorfun(self, status, expstat):
        raise httplib.error("Stanbol HTTP status %s != %s"%(str(status),str(expstat)))
        
######## Enhancer Stanbol API    
    
    def enhancer_chain(self,query,chain=None,
            executionmetadata=False,uri=None):
                        
        url = "enhancer/chain/%s"%chain if chain is not None else "enhancer"
        url = url+"?executionmetadata=%s"%str(executionmetadata).lower()
        if uri is not None: url = url+"&uri=%s"%str(uri)
        
        rettype = "application/json"
        r = self.call_stanbol("post", url,
                        data = query,
                        headers = {'Content-Type': 'text/plain',
                                   "Accept": rettype,
                                },
                        )
        self.check_status_ok(r)
        return r.content

##############3 Entityhub
    def entityhub_sites(self):
        # Returns a list of referenced sites
        resturl = "entityhub/sites/referenced"
        r = self.call_stanbol("get", resturl)
        self.check_status_ok(r)
        sites = self.response_to_json(r.content)
        if sites is None:
            return None
        
        return [re.sub("^.*/([^/]*)/$","\\1",s) for s in sites]
        

    def entityhub_entity(self, id, site=None):        
        resturl = "entityhub/site/%s/entity"%site if site is not None else "entityhub/sites/entity"
        
        resturl = resturl+"?id="+id        
        
        r = self.call_stanbol("get", resturl,
                headers = {'Content-Type': 'application/json',},
                )
        
        if self.check_status_ok(r, lambda *a:None):
            return r.content
        else:
            return None


    def entityhub_find(self, query, field=RDFS.term("label"), site=None):        
        resturl = "entityhub/site/%s/find"%site if site is not None else "entityhub/sites/find"
        r = self.call_stanbol("post", resturl,
            data = { 'name' : query,
                     'field': field,
             })
        self.check_status_ok(r)     
        return r.content

             
    def entityhub_query(self, json_query, 
                          site=None): #site=None : query all sites        
        resturl = "entityhub/site/%s/query"%site if site is not None else "entityhub/sites/query"
            
        jsquery = json.dumps(json_query,ensure_ascii=True,indent=4)
        files = {'file': ("fieldQuery.json", jsquery)}    
    
        orig_method = requests.Request._encode_files    
        setattr(requests.Request, "_encode_files", self.__query_request_wrapper(orig_method))                    
        r = self.call_stanbol_request("post", resturl,
                headers = {'Content-Type': 'application/json',},
                files = files,
                )
        setattr(requests.Request,"_encode_files",orig_method)
        
        self.check_status_ok(r)
        return r.content

    def __query_request_wrapper(self,f):
        ''' Some hacking to force requests lib to send data in a way that Stanbol accepts it
        (that is plain ascii with application/x-www-form-urlencoded; just like curl --data ...        
        Wrapper to Request._encode_files
        '''
        @wraps(f)
        def wrapped(*a):
            ret = f(*a)
            # Removing unnecessary headers
            r0 = re.sub("--.*?\n",'', ret[0])
            r0 = re.sub("Content-.*?\n", '', r0)
            return (r0, 'application/x-www-form-urlencoded;')
        return wrapped
    
        
#############################################
    def contenthub_retrieve(self,cont_id, 
                       media_type="rdf",
                       subresource="raw"):
        ''' Content hub api according to 
        http://localhost:8080/contenthub/contenthub/store#
        '''
        mediadict = {"rdf":"text/rdf",
                     "html":"text/html"}
        accept_media=mediadict[media_type]
    
        index_name="contenthub"
        url="contenthub/%s/store"%index_name + "/%s/%s"%(subresource,str(cont_id))
    
        r = self.call_stanbol("get", url,
                   headers={'Accept': accept_media} )
        self.check_status_ok(r)            
        return r.content        

    
    def contenthub_create_with_uri(self,uri,data,
                        index_name="contenthub"):
        ''' Unfortunately Stanbol api does not allow for creation of content with tags this way... 
        '''
        rest_url="contenthub/%s/store/%s"%(index_name,uri)
        r = self.call_stanbol("post", rest_url,
                    data = data,
                    headers={"Content-Type":"text/plain"},
                    allow_redirects=False)
        self.check_status_ok(r,okstatus=httplib.CREATED)
        #newid=re.sub("^.*/([^/]*)$","\\1",r.url)
        newid=re.sub("^.*/([^/]*)$","\\1",r.headers["location"])                    
        return newid 
        
    
    def contenthub_create(self,content, title,
                        constraints={},
                        url=None,  # Url where content resides                   
                        uri=None, # URI under which content shall be saved/updated -- create doesn't work as expected as update replaces content under another uri                        
                        update=False,
                        index_name="contenthub"):
        ''' url - Url where content resides to be downloaded                  
        uri - URI under which content shall be saved/updated -- create doesn't work as expected as update replaces content under another uri                        
        update - create or update
        '''                
        # Prepare arguments to stanbol api                    
        data={"content": content,
            "title": title,          
            "constraints":json.dumps(constraints),  
            }
            
        if uri is not None:
            if not update: #First create content instance, then update it
                self.contenthub_create_with_uri(uri,"")
                update=True            
            data["uri"]=uri
            
        if url is not None: data["url"]=str(url)
        
        if update: 
            data["jsonCons"]=data["constraints"] #because of inconsistency of store/update Stanbol apis        
        
        rest_url="contenthub/%s/store"%index_name + ("/update" if update else "")
                
        r = self.call_stanbol("post", rest_url,
                    data = data,
                    headers={"Content-Type":"application/x-www-form-urlencoded"},
                    allow_redirects=False)
                    
        self.check_status_ok(r,okstatus=httplib.SEE_OTHER) 
        #Recover newid from redirect header
        newid=re.sub("^.*/([^/]*)$","\\1",r.headers["location"])                    
        return newid 
        
        
    def contenthub_delete(self, uri, index_name="contenthub"):
        
        rest_url="contenthub/%s/store/%s"%(index_name,uri)        
        r = self.call_stanbol("delete", rest_url,                    
                    headers={"Content-Type":"text/plain"},
                    allow_redirects=False)       
        return self.check_status_ok(r,lambda *a:None)
        
        
############# Ontonet        
    def ontonet_get_ontology(self,uri):
        ''' uri of previously loaded to Stanbol ontology http://purl.uniprot.org/core/'''
        rest_url="ontonet/"+uri
        r = self.call_stanbol("get", rest_url,                    
                    #?headers={'Content-Type': 'application/json'},
                    headers={"Content-Type":"text/plain"},
                    allow_redirects=False)       
        self.check_status_ok(r)
        return json.loads(r.content)
        
    def ontonet_get_ontology_terms(self,uri):
        js = self.ontonet_get_ontology(uri)
        return filter(lambda s:s["@subject"].startswith(uri),js["@subject"])

        
############# Utils
    def response_to_json(self, content=None):
        if content is None: 
            if self.check_status_ok(self.last_request,lambda *a:None):
                content = self.last_request.content
            else:
                return None         
        return json.loads(content)

############3 Tests

    def findTest(self):      
        import rdflib
        r=self.entityhub_find('Paris*',
                field=rdflib.RDFS.term("label"),
                site="dbpedia")      
                                         
        return r
    

    def queryTest(self):    
        jsonQuery = {
            "constraints": [{
                "field": STANBOL_REFS, 
                "type": "reference", 
                "mode": "any", 
                "value": [
                    "http://purl.uniprot.org/geneid/2947775",                
                    "http://dbpedia.org/resource/Category:Host_cities_of_the_Summer_Olympic_Games", 
                ]
            }]
            }    
        return self.enityhub_query(jsonQuery)        
    
############ Default connection
default_stanbol_connection = Stanbol()    


#############################################    
#Utilities                

def parse_rdf(s):
    from cStringIO import StringIO
    import rdflib    
    g = rdflib.Graph()
    res = g.parse(StringIO(s))
    return res

def rdf_to_jsonstr(s):
    return parse_rdf(s).serialize(format="rdf-json")

def rdf_to_json(s):
    return json.loads(rdf_to_jsonstr(s))    
        
                
