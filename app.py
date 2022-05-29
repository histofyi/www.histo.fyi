from flask import Flask, request, make_response
from typing import Dict, List
from cache import cache


import doi

from common.decorators import templated
from common.providers import s3Provider, awsKeyProvider

import common.functions as functions
import common.views as views
import common.filters as filters

from common.forms import request_variables
from common.helpers import fetch_constants, fetch_core, slugify

from sitespecific import get_collection_colours, get_collection_sets

from common.models import itemSet, Core

import toml
import datetime


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
                's3_bucket':app.config['S3_BUCKET'] 
            }
    else:
        app.config['AWS_CONFIG'] = {
            'aws_access_key_id':app.config['AWS_ACCESS_KEY_ID'],
            'aws_access_secret':app.config['AWS_ACCESS_SECRET'],
            'aws_region':app.config['AWS_REGION'],
            'local':False,
            's3_bucket':app.config['S3_BUCKET'] 
    }
    return app

app = create_app()


@app.template_filter()
def collection_title(title):
    print (title)
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
def short_structure_title(structure):
    return filters.structure_title(structure, short=True)


@app.template_filter()
def full_structure_title(structure):
    return filters.structure_title(structure)


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
    collections['species'] = get_collection_sets(s3, key_provider, 'species')
    collections['peptide_lengths'] = get_collection_sets(s3, key_provider, 'peptide_lengths')
    collections['complex_types'] = get_collection_sets(s3, key_provider, 'complex_types')
    collections['deposition_years'] = get_collection_sets(s3, key_provider, 'deposition_years')
    collections['peptide_features'] = get_collection_sets(s3, key_provider, 'peptide_features')
    return {'collection_colours':get_collection_colours(), 'collections':collections}


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
    return {'itemset':itemset, 'facet_display':'info'}


@app.route('/structures/lookup')
@templated('lookup')
def structure_lookup():
    return views.structure_lookup()


@app.route('/structures/view/<string:pdb_code>')
@templated('structure/view')
def structure_view(pdb_code):    
    return views.structure_view(pdb_code)


@app.route('/structures/files/<string:action>/<string:structure_type>/<string:pdb_code>_<string:assembly_id>.cif')
def structure_file_route(action, structure_type, pdb_code, assembly_id):
    print (action)
    s3 = s3Provider(app.config['AWS_CONFIG'])
    assembly_identifier = f'{pdb_code}_{assembly_id}'
    file_key = awsKeyProvider().cif_file_key(assembly_identifier, 'split')
    structure_file, success, errors = s3.get(file_key, data_format='cif')
    structure_file = structure_file.decode('utf-8')
    response = make_response(structure_file, 200)
    response.mimetype = "text/plain"
    return response


@app.route('/changelog')
@app.route('/about')
@templated('content')
def content_route():
    route = str(request.url_rule)
    content_route = 'content{route}.html'.format(route=route)
    with app.open_resource(content_route) as f:
        content = f.read().decode('UTF-8')
    return {'content': content, 'route':route}


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
    return {'path': path, 'code':404}



