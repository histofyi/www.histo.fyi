from typing import Dict, List
import json

import toml
import datetime
import itertools

from flask import Flask, Response, redirect, jsonify


from functions.files import load_json
from functions.decorators import templated, webview
from functions.helpers import slugify


from api import api_handlers

import handlers



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

    app.register_blueprint(api_handlers, url_prefix='/v1')
    
    app.config.from_file('config.toml', toml.load)
    app.secret_key = app.config['SECRET_KEY']

    # removing whitespace from templated returns    
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    return app


app = create_app()



@app.before_first_request
def load_data():
    """
    This is a function which loads the generated datasets which are used by the site.

    By loading them in here, we can reduce S3 calls and speed the app up significantly.
    """
    datasets = ['collections','features','index','ordering','sets','core','listings','chains','collection_colours','peptide_lengths']
    app.data = {}
    for dataset in datasets:
        app.data[dataset] = load_json(dataset)
    app.data['pdb_codes'] = app.data['index']['deposition_date_asc']


@app.route('/')
@webview
@templated('index')
def home_handler():
    return handlers.home_handler()


@app.route('/structures/lookup/')
@app.route('/structures/lookup')
@webview
@templated('lookup')
def structure_lookup_handler():
    return handlers.structure_lookup_handler()


@app.route('/api/v1/structures/<string:pdb_code>/')
@app.route('/api/v1/structures/<string:pdb_code>')
def structure_api_handler(pdb_code):
    return handlers.structure_view_handler(pdb_code)


@app.route('/structures/view/<string:pdb_code>/')
@app.route('/structures/view/<string:pdb_code>')
@webview
@templated('structure/view')
def structure_view_handler(pdb_code):
    return handlers.structure_view_handler(pdb_code)


@app.route('/structures/browse/<string:context>/<string:set_slug>/')
@app.route('/structures/browse/<string:context>/<string:set_slug>')
@webview
@templated('shared/browse')
def structure_browse_handler(context, set_slug):
    return handlers.structure_browse_handler(context, set_slug)


@app.route('/structures/collections/<string:collection_slug>/')
@app.route('/structures/collections/<string:collection_slug>')
@webview
@templated('collection')
def structure_collection_handler(collection_slug):
    return handlers.structure_collection_handler(collection_slug)


@app.get('/search')
@webview
@templated('search_page')
def search():
    return handlers.search_handler()


@app.route('/about/')
@app.route('/about')
@webview
@templated('about_section')
def about_home():
    return handlers.about_handler('/about')
    

@app.route('/about/<string:about_page>')
@templated('about_section')
@webview
def about_page(about_page):
    route = f'/about/{about_page}'
    return handlers.about_handler(route)


@app.route('/changelog')
@webview
@templated('content')
def content_route():
    return handlers.about_handler('changelog')


@app.get('/feedback')
@webview
@templated('feedback')
def feedback_form():
    return handlers.feedback_form_page()


@app.post('/feedback')
@webview
@templated('feedback')
def post_feedback():
    return handlers.feedback_form_handler()


@app.get('/feedback/thank-you')
@webview
@templated('feedback')
def feedback_thanks():
    return {'message':'Thank you for your feedback. We\'ll be in touch soon'}


@app.route('/posters/<string:year>/<string:conference>/')
@app.route('/posters/<string:year>/<string:conference>')
@webview
@templated('poster')
def posters_route(year, conference):
    return handlers.poster_handler(year, conference)



@app.route('/robots.txt')
def robots_txt():
    raw_response = '''
    User-agent: *
    Allow: /
    '''
    response_text = '\n'.join([line.strip() for line in raw_response.splitlines() if len(line) > 0])
    r = Response(response=response_text, status=200, mimetype="text/plain")
    r.headers["Content-Type"] = "text/plain; charset=utf-8"
    return r


@app.route('/favicon.ico')
def favicon():
    return redirect('/static/histo-32-color.png')

@app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404


@app.route('/<path:path>')
@webview
@templated('404')
def error_404(path):
    return handlers.handle_404(path)
    


@app.template_filter()
def deslugify(text):
    return text.replace('_',' ')


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


@app.template_filter()
def imgt_ipd_hla_parser(id):
    stem = None
    accession_id = None
    print(id)
    if id:
        if 'uniprot' in id:
            stem = None
            accession_id = None
        else:
            if 'imgt' in id:
                split_id = id.split(':')
                stem = f'{split_id[0].lower()}'
                accession_id = split_id[1]
                resource = 'IPD-IMGT/HLA'
            if 'mhc' in id:
                split_id = id.split(':')
                stem = f'{split_id[0].lower()}'
                accession_id = split_id[1]
                resource = 'IPD-MHC'
            elif 'H2-' in id or 'mouse' in id.lower():
                stem = None
                accession_id = None
    if stem and accession_id:
        if stem == 'ipd-imgt':
            url = f'https://www.ebi.ac.uk/ipd/imgt/hla/alleles/allele/?accession={accession_id}'
        else:
            url = f'https://www.ebi.ac.uk/ipd/mhc/allele/?accession={accession_id}'
        return f'<strong>{resource}</strong><br />[<a href="{url}" target="_new">{id}</a>]'
    else:
        return ''

@app.template_filter()
def slugify_this(text):
    return slugify(text)


@app.template_filter()
def html_stripped(text):
    html_tags = ['strong']
    for tag in html_tags:
        text = text.replace(f'<{tag}>','').replace(f'</{tag}>','').replace(f'<{tag}/>','')
    return text

