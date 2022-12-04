from flask import Blueprint, jsonify

import handlers

api_handlers = Blueprint('api_handlers', __name__)



@api_handlers.route('/')
def api_route():
    return {'hello':'world'}


@api_handlers.route('/structures/<string:pdb_code>/')
@api_handlers.route('/structures/<string:pdb_code>')
def structures_route(pdb_code):
    return handlers.structure_view_handler(pdb_code)


@api_handlers.route('/search')
def search_route():
    # setting api=True returns full-fat listings (core records)
    return handlers.search_handler(api=True)


@api_handlers.route('/sets/<string:context>/<string:slug>/')
@api_handlers.route('/sets/<string:context>/<string:slug>')
def sets_route(context, slug):
    return handlers.structure_browse_handler(context, slug, api=True)


@api_handlers.route('/collections/<string:slug>/')
@api_handlers.route('/collections/<string:slug>')
def collections_route(slug):
    return handlers.structure_collection_handler(slug)