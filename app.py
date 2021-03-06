from inspect import cleandoc
import re
from common.providers.slack import slackProvider
from flask import Flask, request, make_response, Response
from typing import Dict, List
from cache import cache
import json

import doi

from common.decorators import templated
from common.providers import s3Provider, awsKeyProvider, algoliaProvider, steinProvider, plausibleProvider, slackProvider, httpProvider

import common.functions as functions
import common.views as views
import common.filters as filters

from common.forms import request_variables
from common.helpers import fetch_constants, fetch_core, fetch_facet, slugify

from sitespecific import get_collection_colours, get_collection_sets

from common.models import itemSet, Core

import toml
import datetime
import itertools


import logging



config = {
    "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 300, # Flask-Caching related configs
    "TEMPLATE_DIRS": "templates" # Default template directory
}


def create_app():
    """
    Creates an instance of the Flask app, and associated configuration and blueprints registration for specific routes. 

    Configuration includes

    - Relevant secrets stored in the config.toml file
    - Storing in configuration a set of credentials for AWS (decided upon by the environment of the application e.g. development, live)
    
    Returns:
            A configured instance of the Flask app

    """
    app = Flask(__name__)
    app.config.from_file('config.toml', toml.load)
    app.secret_key = app.config['SECRET_KEY']

    # configuration of the cache from config
    app.config.from_mapping(config)
    cache.init_app(app)


    # removing whitespace from templated returns    
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    if app.config['USE_LOCAL_S3'] == True:
            app.config['AWS_CONFIG'] = {
                'aws_access_key_id':app.config['LOCAL_ACCESS_KEY_ID'],
                'aws_access_secret':app.config['LOCAL_ACCESS_SECRET'],
                'aws_region':app.config['AWS_REGION'],
                's3_url':app.config['LOCAL_S3_URL'],
                'local':True,
                's3_bucket':app.config['LOCAL_S3_BUCKET'] 
            }
    else:
        app.config['AWS_CONFIG'] = {
            'aws_access_key_id':app.config['AWS_ACCESS_KEY_ID'],
            'aws_access_secret':app.config['AWS_ACCESS_SECRET'],
            'aws_region':app.config['AWS_REGION'],
            'local':False,
            's3_bucket':app.config['S3_BUCKET'] 
    }

    # removing whitespace from templated returns    
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    return app

app = create_app()


@app.template_filter()
def collection_title(title):
    if 'Class' in title:
        if len(title.split('Class')[1]) < 4:
            title = title.split('Class')[0]
    elif 'structure' in title:
        if len(title.split('structure')[1]) < 4:
            title = title.split('structure')[0]
    elif 'Deposited in' in title:
        print (len(title.split('Deposited in')[1]))
        if len(title.split('Deposited in')[1]) >= 4:
            title = title.split('Deposited in')[1]
    return title


@app.template_filter()
def timesince(start_time):
    return functions.timesince(start_time)


@app.template_filter()
def short_structure_title(structure, url):
    return filters.structure_title(structure, url, short=True)


@app.template_filter()
def full_structure_title(structure, url):
    return filters.structure_title(structure, url)


@app.template_filter()
def slugify_this(text):
    return slugify(text)


@app.template_filter()
def year_from_rcsb_date(text):
    return text[0:4]


@app.template_filter()
def html_stripped(text):
    html_tags = ['strong']
    for tag in html_tags:
        text = text.replace(f'<{tag}>','').replace(f'</{tag}>','').replace(f'<{tag}/>','')
    return text

@app.template_filter()
def imgt_ipd_hla_parser(id):
    stem = None
    accession_id = None
    if id:
        if ':' in id:
            split_id = id.split(':')
            stem = f'imgt/{split_id[0].lower()}/alleles/'
            accession_id = split_id[1]
            resource = 'IPD-IMGT/HLA'
        elif 'H2-' in id or 'mouse' in id.lower() or id.lower().index('sp') == 0:
            stem = None
            accession_id = None
        else:
            stem = 'mhc'
            accession_id = id
            resource = 'IPD-MHC'
    if stem and accession_id:
        url = f'https://www.ebi.ac.uk/ipd/{stem}allele/?accession={accession_id}'
        return f'<strong>{resource}</strong><br />[<a href="{url}" target="_new">{id}</a>]'
    else:
        return ''


@app.template_filter()
def chunked_sequence(sequence):
    line_length = 60
    sequence_length = len(sequence)
    sequence_chunks = []
    i = 0
    if len(sequence) < line_length:
        i = 1
        chunked_sequence = sequence
    else:
        remainder = sequence
        while len(remainder) > line_length:
            i += 1
            sequence_chunks.append(remainder[:line_length])
            remainder = remainder[line_length:]
        if len(remainder) > 0: 
            sequence_chunks.append(remainder)
            i += 1
    j = 0
    numbers = range(10, line_length + 10, 10)
    row_labels = []
    if sequence_length > 30:
        while j < i:
            row_label = ''
            for number in numbers:
                this_number = j * line_length + number
                this_spacecount = 10 - len(str(this_number))
                if this_number < sequence_length:
                    row_label = row_label + '&nbsp;' * this_spacecount + str(this_number)
            row_labels.append(row_label)
            j += 1
    if len(row_labels) == 0:
        chunked_sequence = sequence
    else:
        labelled_chunks = [chunk for chunk in list(itertools.chain(*zip(row_labels, sequence_chunks)))]
        chunked_sequence = '<br/>'.join(labelled_chunks)
    return chunked_sequence


def check_datastore():
    """
    A function to return a small piece of JSON to indicate whether or not the connection to AWS is working
    """
    scratch_json, success, errors = s3Provider(app.config['AWS_CONFIG']).get('scratch/hello.json')
    if not success:
        scratch_json = {'error':'unable to connect'}
    scratch_json['cached'] = datetime.datetime.now()
    return scratch_json






@app.route('/')
@templated('index')
def home_route():
    scratch_json = check_datastore()
    s3 = s3Provider(app.config['AWS_CONFIG'])
    key_provider = awsKeyProvider()
    collections = {}
    canned = True
    if not canned:
        collections['species'] = get_collection_sets(s3, key_provider, 'species')
        collections['peptide_lengths'] = get_collection_sets(s3, key_provider, 'peptide_lengths')
        collections['complex_types'] = get_collection_sets(s3, key_provider, 'complex_types')
        collections['deposition_years'] = get_collection_sets(s3, key_provider, 'deposition_years')
        collections['peptide_features'] = get_collection_sets(s3, key_provider, 'peptide_features')
    return {'collection_colours':get_collection_colours(), 'collections':collections, 'canned':canned}


@app.route('/structures')
@app.route('/structures/')
@templated('structures')
def structures_home_route():
    s3 = s3Provider(app.config['AWS_CONFIG'])
    key_provider = awsKeyProvider()
    species_collection = get_collection_sets(s3, key_provider, 'species')
    peptides_collection = get_collection_sets(s3, key_provider, 'peptide_lengths')
    return {'species_collection':species_collection, 'peptides_collection':peptides_collection, 'collection_colours':get_collection_colours()}


@app.route('/structures/collections/browse/<string:collection_slug>')
@templated('collection')
def structures_collections_route(collection_slug):
    s3 = s3Provider(app.config['AWS_CONFIG'])
    key_provider = awsKeyProvider()
    collection = get_collection_sets(s3, key_provider, collection_slug)
    return {'collection':collection, 'collection_colours':get_collection_colours()}


@app.route('/structures/sets/browse/<string:set_context>/<string:set_slug>')
@templated('shared/browse')
def structures_sets_route(set_context:str, set_slug:str) -> Dict:
    """
    This handler provides the for viewing a set and the various facets

    Args: 
        userobj (Dict): a dictionary describing the currently logged in user with the correct privileges

    Returns:
        Dict: a dictionary containing the user object, an empty variables dictionary and an errors array containing the indication that it's an empty form

    """
    variables = request_variables(None, params=['page_number'])
    set_slug = slugify(set_slug)
    set_context = slugify(set_context)
    itemset = None
    page_size = 25
    if variables['page_number'] is not None :
        page_number = int(variables['page_number'])
    else:
        page_number = 1    
    itemset = itemSet(set_slug, set_context).get(page_number=page_number, page_size=page_size)
    if itemset is not None:
        itemset, success, errors = Core(app.config['AWS_CONFIG']).hydrate(itemset)
    return {'itemset':itemset, 'facet_display':'info',  'chain_types':fetch_constants('chains')}


@app.route('/structures/lookup')
@templated('lookup')
def structure_lookup():
    return views.structure_lookup()


@app.route('/structures/view/<string:pdb_code>')
@templated('structure/view')
def structure_view(pdb_code):    
    return views.structure_view(pdb_code)


@app.route('/structures/files/<string:action>/<string:structure_type>/<string:pdb_code>_<string:assembly_id>.<string:fileformat>')
def structure_file_route(action, structure_type, pdb_code, assembly_id, fileformat):
    print (action)
    s3 = s3Provider(app.config['AWS_CONFIG'])
    assembly_identifier = f'{pdb_code}_{assembly_id}'
    #file_key = awsKeyProvider().cif_file_key(assembly_identifier, 'split')
    if structure_type == 'aligned':
        file_key = awsKeyProvider().structure_key(assembly_identifier, structure_type)
        structure_file, success, errors = s3.get(file_key, data_format='pdb')
    else:
        file_key = awsKeyProvider().cif_file_key(assembly_identifier, structure_type)
        structure_file, success, errors = s3.get(file_key, data_format='cif')
    print (type(structure_file))
    if not isinstance(structure_file, str):
        structure_file = structure_file.decode('utf-8')
    else:
        structure_file = structure_file.encode('utf-8')
    response = make_response(structure_file, 200)
    response.mimetype = "text/plain"
    return response


@app.route('/structures/downloads/<string:pdb_code>_<string:assembly_id>_<string:download_type>.<string:file_extension>')
def download_file_route(pdb_code, assembly_id, download_type, file_extension):
    print (download_type)
    s3 = s3Provider(app.config['AWS_CONFIG'])
    assembly_identifier = f'{pdb_code}_{assembly_id}'
    if file_extension == 'cif' and download_type in ['aligned','alpha', 'peptide', 'abd']:
        file_key = awsKeyProvider().cif_file_key(assembly_identifier, download_type)
        structure_file, success, errors = s3.get(file_key, data_format='cif')
        if not isinstance(structure_file, str):
            structure_file = structure_file.decode('utf-8')
        else:
            structure_file = structure_file.encode('utf-8')
        file_name = f'{pdb_code}_{assembly_id}_{download_type}.cif'
        plausible = plausibleProvider('histo.fyi')    
        plausible.structure_download(file_name, download_type, pdb_code)    
        return Response(structure_file,
                        mimetype="text/plain",
                        headers={"Content-disposition": f"attachment; filename={file_name}"})
            
    elif file_extension == 'json' and download_type in ['calphas','neighbours']:
        if download_type == 'neighbours':
            download_type = 'peptide_neighbours'
        print (download_type)
        data_file, success, errors = fetch_facet(pdb_code, download_type, app.config['AWS_CONFIG'])
        if assembly_id in data_file:
            data_file = data_file[assembly_id]
        data_file = json.dumps(data_file)
        file_name = f'{pdb_code}_{assembly_id}_{download_type}.json'
        print (file_name)
        plausible = plausibleProvider('histo.fyi')    
        plausible.data_download(file_name, download_type, pdb_code)    
        return Response(data_file,
                        mimetype="application/json",
                        headers={"Content-disposition": f"attachment; filename={file_name}"})
        



@app.get('/search')
@templated('search_page')
def search():
    empty_search = True
    variables = request_variables(None, params=['query','page_number'])
    if not variables['page_number']:
        current_page = 1
    else:
        current_page = int(variables['page_number'])
    print (variables)
    hits = 0
    pages = 0
    itemset = {'pagination':{}}
    if variables['query'] is not None:
        query = variables['query']
        algolia = algoliaProvider(app.config['ALGOLIA_APPLICATION_ID'], app.config['ALGOLIA_KEY'])
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
                    'pages':range(1,search_results['nbPages'] + 1)
                }
                processed_search_results = [{'pdb_code':structure['pdb_code'], 'core':structure} for structure in search_results['hits']]
                empty_search = False
    else:
        processed_search_results = []
    return {'search_results':processed_search_results, 'variables':variables, 'query':variables['query'], 'page_number':variables['page_number'], 'empty_search':empty_search, 'itemset':itemset, 'chain_types':fetch_constants('chains')}


@app.route('/changelog')
@templated('content')
def content_route():
    route = str(request.url_rule)
    content_route = 'content{route}.html'.format(route=route)
    with app.open_resource(content_route) as f:
        content = f.read().decode('UTF-8')
    return {'content': content, 'route':route}



def about_handler(route):
    navigation = [
        {'url': '/about/','title': 'About histo.fyi'},
        {'url': '/about/why-needed','title': 'Why is this resource needed?'},
        {'url': '/about/how-can','title': 'How can the data be used?'},
        #{'url': '/about/structural-introduction-to-class-i','title': 'A structural introduction to MHC Class I molecules'},
        #{'url': '/about/mhc-binding-molecules','title': 'Information about molecules which bind to MHC molecules'},
        {'url': '/about/data-provenance','title': 'Data provenance'},
        #{'url': '/about/data-pipeline','title': 'Data pipeline'},
        {'url': '/about/why-histo','title': 'Why histo.fyi?'},
        {'url': '/about/technology-used','title': 'Technology used'},
        #{'url': '/about/acknowledgements-and-references','title': 'Acknowledgements and references'},
        {'url': '/about/contact','title': 'Contact'},
        {'url': '/about/team','title': 'Team'},
        {'url': '/feedback?feedback_type=general','title': 'Feedback'}
    ]
    content_route = f'content{route}.html'
    with app.open_resource(content_route) as f:
        content = f.read().decode('UTF-8')
    if '---' in content:
        elements = [element.strip() for element in content.split('---')]
        metadata = {}
        for row in [element for element in elements[1].split('\n')]:
            key = row.split(':')[0]
            value = row.split(':')[1]
            metadata[key] = value
        content = elements[2]
        if '{{static_route}}' in content:
            content = content.replace('{{static_route}}', app.config['STATIC_ROUTE'])
    else:
        metadata = None
    return {'content': content, 'route':route, 'navigation':navigation, 'metadata':metadata}


@app.route('/about/')
@app.route('/about')
@templated('about_section')
def about_home():
    return about_handler('/about')
    

@app.route('/about/<string:about_page>')
@templated('about_section')
def about_page(about_page):
    route = f'/about/{about_page}'
    return about_handler(route)



@app.route('/posters/2021/bsi/')
@app.route('/posters/2021/bsi')
@templated('poster')
def posters_route():
    content_route = 'content{route}.html'.format(route='/posters/2021/bsi')
    with app.open_resource(content_route) as f:
        content = f.read().decode('UTF-8')
    return {'content': content}


@app.route('/<path:path>')
@templated('404')
def error_404(path):
    plausible = plausibleProvider('histo.fyi')
    plausible.record_404(path)
    return {'path': path, 'code':404}




@app.get('/feedback')
@templated('feedback')
def feedback_form():
    variables = request_variables(None, ['url','feedback_type'])
    return {'variables':variables}


@app.post('/feedback')
@templated('feedback')
def post_feedback():
    variables = request_variables(None, ['name','email','feedback','url','feedback_type'])
    if variables['name'] is not None and variables['email'] is not None and variables['feedback'] is not None:
        variables['feedback'] = '\n'.join(variables['feedback'].splitlines())
        variables['date'] = datetime.datetime.now().isoformat()
        stein = steinProvider(app.config['STEIN_API_URL'], app.config['STEIN_USERNAME'], app.config['STEIN_PASSCODE'])
        stein_response = stein.add('alpha', variables)
        slack = slackProvider(app.config['SLACK_WEBHOOK'])
        slack_response = slack.send('feedback', variables)
        return {'redirect_to': f'/feedback/thank-you'}
    else:
        return {'variables':variables, 'errors':True}


@app.get('/feedback/thank-you')
@templated('feedback')
def feedback_thanks():
    return {'message':'Thank you for your feedback. We\'ll be in touch soon'}

