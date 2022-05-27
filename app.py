from flask import Flask, request, make_response
from cache import cache


import doi

from common.decorators import templated
from common.providers import s3Provider, awsKeyProvider
import common.functions as functions
from common.forms import request_variables
from common.helpers import fetch_constants

from common.helpers import fetch_core


import toml
import datetime


import logging

current_species = ['human', 'mouse', 'chicken', 'norway_rat', 'rhesus_monkey', 'horse', 'feral_pig', 'domestic_cat', 'domestic_dog', 'domestic_cattle', 'mallard_duck', 'european_rabbit', 'black_fruit_bat', 'african_clawed_frog', 'giant_panda', 'grass_carp', 'green_anole_lizard', 'nurse_shark']
peptide_lengths = ['octamer', 'nonamer', 'decamer', 'undecamer', 'dodecamer', 'tridecamer', 'tetradecamer', 'pentadecamer', 'hexadecamer', 'nonadecamer']


collection_colours = {
    'species':'indy',
    'peptide_lengths':'purple',
    'complex_types':'teal',
    'deposition_years':'indigo',
    'peptide_features':'fuel'
}


collections = {
    'species':{
        'context':'species',
        'slug':'species',
        'name':'species',
        'description':'MHC Class I structures of different species',
        'members':['human_class_i.json','mouse_class_i.json', 'chicken_class_i.json', 'norway_rat_class_i.json', 'rhesus_monkey_class_i.json', 'horse_class_i.json', 'feral_pig_class_i.json']
    },
    'peptide_lengths':{
        'context':'peptide_length',
        'slug':'peptide_lengths',
        'name':'peptide lengths',
        'description':'Lengths of peptides',
        'members':[
                    'octamer.json',
                    'nonamer.json',
                    'decamer.json',
                    'undecamer.json',
                    'dodecamer.json',
                    'tridecamer.json',
                    'tetradecamer.json',
                    'pentadecamer.json',
                    'hexadecamer.json',
                    'nonadecamer.json',
                    'icosamer.json'
                ]
    },
    'complex_types':{
        'context':'complex_type',
        'slug':'complex_types',
        'name':'complex types',
        'description':'Different accessory molucules and receptors',
        'members':[
            'class_i_with_peptide.json',
            'class_i_with_peptide_and_alpha_beta_tcr.json',
            'class_i_with_peptide_and_gamma_delta_tcr.json',
            'class_i_with_tapbpr.json'
            ]
    },
    'deposition_years':{
        'context':'chronology',
        'slug':'deposition_years',
        'name':'deposition years',
        'description':'Structures deposited in specific years',
        'members':[
                    'structures_released_in_1990.json', 
                    'structures_released_in_1992.json', 
                    'structures_released_in_1993.json', 
                    'structures_released_in_1994.json', 
                    'structures_released_in_1995.json', 
                    'structures_released_in_1996.json', 
                    'structures_released_in_1997.json', 
                    'structures_released_in_1998.json', 
                    'structures_released_in_1999.json', 
                    'structures_released_in_2000.json', 
                    'structures_released_in_2001.json', 
                    'structures_released_in_2002.json', 
                    'structures_released_in_2003.json', 
                    'structures_released_in_2004.json', 
                    'structures_released_in_2005.json', 
                    'structures_released_in_2006.json', 
                    'structures_released_in_2007.json', 
                    'structures_released_in_2008.json', 
                    'structures_released_in_2009.json', 
                    'structures_released_in_2010.json', 
                    'structures_released_in_2011.json', 
                    'structures_released_in_2012.json', 
                    'structures_released_in_2013.json', 
                    'structures_released_in_2014.json', 
                    'structures_released_in_2015.json',
                    'structures_released_in_2016.json',
                    'structures_released_in_2017.json',
                    'structures_released_in_2018.json',
                    'structures_released_in_2019.json',
                    'structures_released_in_2020.json',
                    'structures_released_in_2021.json',
                    'structures_released_in_2022.json'
                ]
    },
    'peptide_features':{
        'context':'features',
        'slug':'peptide_features',
        'name':'peptide features',
        'description':'Features of MHC bound peptides, extensions, bulges etc',
        'members':['c_terminally_extended.json']
    }
}


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
def mhc_class_stripper(species_title):
    return species_title.split('Class')[0]


@app.template_filter()
def timesince(start_time):
    return functions.timesince(start_time)



def check_datastore():
    """
    A function to return a small piece of JSON to indicate whether or not the connection to AWS is working
    """
    scratch_json, success, errors = s3Provider(app.config['AWS_CONFIG']).get('scratch/hello.json')
    if not success:
        scratch_json = {'error':'unable to connect'}
    scratch_json['cached'] = datetime.datetime.now()
    return scratch_json


@cache.memoize(timeout=120)
def get_species_sets(s3, key_provider):
    species_collection = {
        'class_i':[]
    }
    count = 0
    for species in current_species:
        species_slug = f'{species}_class_i'
        species_key = key_provider.set_key(species_slug, 'structures', 'species')
        species_set, success, errors = s3.get(species_key)
        if species_set:
            species_collection['class_i'].append(species_set)
            count += len(species_set['members'])
    print(count)
    return species_collection


@cache.memoize(timeout=120)
def get_peptides_sets(s3, key_provider):
    peptides_collection = {
        'class_i':[]
    }
    count = 0
    for peptide_slug in peptide_lengths:
        peptide_key = key_provider.set_key(peptide_slug, 'structures', 'peptide_length')
        peptide_set, success, errors = s3.get(peptide_key)
        if peptide_set:
            peptides_collection['class_i'].append(peptide_set)
            count += len(peptide_set['members'])
    print(count)
    return peptides_collection


def get_collection_items(s3, key_provider, collection_slug):
    collection = get_collection(collection_slug)
    if collection is not None:
        context = collection['context']
        collection['hydrated_members'] = {}
        collection['all_members'] = []
        for set_slug in collection['members']:
            item_key = key_provider.set_key(set_slug.replace('.json',''), 'structures', context)
            item_set, success, errors = s3.get(item_key)
            if success:
                collection['hydrated_members'][set_slug] = item_set
                collection['all_members'] += item_set['members']
    return collection



def get_collections():
    return collections


def get_collection(collection_slug):
    collections = get_collections()
    if collection_slug in collections:
        return collections[collection_slug]
    else:
        return None



@app.route('/')
@templated('index')
def home_route():
    scratch_json = check_datastore()
    collections = get_collections()
    s3 = s3Provider(app.config['AWS_CONFIG'])
    key_provider = awsKeyProvider()
    for collection in collections:
        hydrated_collection = get_collection_items(s3, key_provider, collection)
    return {'collections':collections, 'collection_colours':collection_colours}


@app.route('/structures')
@app.route('/structures/')
@templated('structures')
def structures_home_route():
    s3 = s3Provider(app.config['AWS_CONFIG'])
    key_provider = awsKeyProvider()
    species_collection = get_species_sets(s3, key_provider)
    peptides_collection = get_peptides_sets(s3, key_provider)
    return {'species_collection':species_collection, 'peptides_collection':peptides_collection}


@app.route('/structures/collections/<string:collection_slug>')
@templated('collection')
def structures_collections_route(collection_slug):
    s3 = s3Provider(app.config['AWS_CONFIG'])
    key_provider = awsKeyProvider()
    collection = get_collection_items(s3, key_provider, collection_slug)
    return {'collection':collection, 'collection_colours':collection_colours}


@app.route('/structures/lookup')
@templated('lookup')
def structures_lookup():
    s3 = s3Provider(app.config['AWS_CONFIG'])
    variables = request_variables(None, ['pdb_code'])
    if variables['pdb_code'] is not None:
        pdb_code = variables['pdb_code'].lower()
        if '_' in pdb_code:
            pdb_code = pdb_code.split('_')[0]
        data, success, errors = s3.get(awsKeyProvider().block_key(pdb_code, 'core', 'info'))
    else:
        success = False
    if success:
        return {'redirect_to': f'/structures/view/{pdb_code}'}
    else:
        return {'variables': variables}





@app.route('/structures/view/<string:pdb_code>')
@templated('structure/view')
def structure_view_route(pdb_code):
    blocks = ['chains', 'allele_match', 'peptide_matches', 'peptide_neighbours', 'peptide_structures', 'peptide_angles', 'cleft_angles', 'c_alpha_distances']
    structure, success, errors = fetch_core(pdb_code, app.config['AWS_CONFIG'])
    if success:
        structure['pdb_code'] = pdb_code
        structure['facets'] = {}
        s3 = s3Provider(app.config['AWS_CONFIG'])
        for block in blocks:
            block_key = awsKeyProvider().block_key(pdb_code, block, 'info')
            block_data, success, errors = s3.get(block_key)
            structure['facets'][block] = block_data
        if structure['doi'] is not None:
            structure['doi_url'] = doi.get_real_url_from_doi(structure['doi'])
    return {'structure':structure, 'pdb_code':pdb_code, 'chain_types':fetch_constants('chains')}


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



