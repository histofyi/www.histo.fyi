from flask import Flask, request

import doi

from common.decorators import templated
from common.providers import s3Provider, awsKeyProvider
import common.functions as functions

from common.helpers import fetch_core


import toml
import datetime


import logging

current_species = ['human', 'mouse', 'chicken', 'norway_rat', 'rhesus_monkey', 'horse', 'feral_pig']
peptide_lengths = ['octamer', 'nonamer', 'decamer', 'undecamer', 'dodecamer', 'tridecamer', 'tetradecamer', 'pentadecamer']


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


def get_species_sets(s3, key_provider):
    species_collection = {
        'class_i':[]
    }
    for species in current_species:
        species_slug = f'{species}_class_i'
        species_key = key_provider.set_key(species_slug, 'structures', 'species')
        species_set, success, errors = s3.get(species_key)
        if species_set:
            species_collection['class_i'].append(species_set)
    return species_collection


def get_peptides_sets(s3, key_provider):
    peptides_collection = {
        'class_i':[]
    }
    for peptide_slug in peptide_lengths:
        peptide_key = key_provider.set_key(peptide_slug, 'structures', 'peptide_length')
        peptide_set, success, errors = s3.get(peptide_key)
        if peptide_set:
            peptides_collection['class_i'].append(peptide_set)
    return peptides_collection


@app.route('/')
@templated('index')
def home_route():
    scratch_json = check_datastore()
    return {}


@app.route('/structures')
@app.route('/structures/')
@templated('structures')
def structures_home_route():
    s3 = s3Provider(app.config['AWS_CONFIG'])
    key_provider = awsKeyProvider()
    species_collection = get_species_sets(s3, key_provider)
    peptides_collection = get_peptides_sets(s3, key_provider)
    return {'species_collection':species_collection, 'peptides_collection':peptides_collection}


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
            #structure['facets'][block] = block_data
        if structure['doi'] is not None:
            structure['doi_url'] = doi.get_real_url_from_doi(structure['doi'])
    return {'structure':structure}



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



