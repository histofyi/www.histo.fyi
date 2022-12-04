from providers.algolia import algoliaProvider
from providers.plausible import plausibleProvider

from functions.forms import request_variables

from actions.search import parse_query

from models.sets import StructureSetMembers
from models.sets import StructureSet

from functions.app import app_context





def search_handler(api=False):    
    empty_search = True
    variables = request_variables(None, params=['query','page_number','fulltext'])
    if not variables['page_number']:
        current_page = 1
    else:
        current_page = int(variables['page_number'])
    if api:
        depth='core'
    else:
        depth='listings'
    hits = 0
    pages = 0
    itemset = {'pagination':{}}
    querytype = 'fulltext'
    if variables['query'] is not None:
        query = variables['query']
    else:
        query = ''

    if len(query) > 0:
        # first of all, if a user has overridden a search and wants a fulltext one, the fulltext variable will be true
        if variables['fulltext'] != 'true':
            # attempt to parse the query for alleles, allele groups, loci and peptides
            query_info = parse_query(query)
            querytype = query_info['querytype']
            if query_info['query'] is not None:
                query = query_info['query']
            # if none of those can be found, or there are spaces in the query the parse_query function will set the querytype variable to fulltext
            if querytype == 'fulltext':
                fulltext = True
            else:
                fulltext = False
        else:
            fulltext = True

        if not fulltext:
            try:
                itemset = StructureSet(query_info['querytype'], query_info['slug']).hydrate(page=current_page, page_size=25, depth=depth)
                processed_search_results = itemset['members']
                empty_search = False
                fulltext = False
            except:
                print ('BREAKING')
                fulltext = True
                querytype = 'fulltext'

        if fulltext:
            print ('FULLTEXT')
            query = variables['query']
            algolia = algoliaProvider(app_context.config['ALGOLIA_APPLICATION_ID'], app_context.config['ALGOLIA_KEY'])
            search_results, success, errors = algolia.search('core', query, current_page)
            if 'nbHits' in search_results:
                if search_results['nbHits'] == 0:
                    plausible = plausibleProvider('histo.fyi')
                    plausible.empty_search(variables['query'])
                    processed_search_results = []
                    success = False
                    errors = ['no_matching results']
                    itemset['pagination'] = {
                        'total':0,
                        'current_page':0,
                        'page_count':0,
                        'page_size':25
                    }
                else:
                    itemset['pagination'] = {
                        'total':search_results['nbHits'],
                        'current_page':current_page,
                        'page_count':search_results['nbPages'],
                        'page_size':25,
                        'pages':[page for page in range(1,search_results['nbPages'] + 1)]
                    }
                    processed_search_results = StructureSetMembers.hydrate([result['pdb_code'] for result in search_results['hits']], depth=depth)
                    empty_search = False
    else:
        processed_search_results = []

    return {'search_results':processed_search_results, 'variables':variables, 'query':query, 'querytype':querytype, 'page_number':variables['page_number'], 'empty_search':empty_search, 'set':itemset}
