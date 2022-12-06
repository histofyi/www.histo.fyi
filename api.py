from flask import Blueprint, jsonify, redirect
from flasgger import swag_from



import handlers

api_handlers = Blueprint('api_handlers', __name__)


@api_handlers.route('/')
def api_route():
    return redirect('/apidocs/')


@api_handlers.route('/structures/<string:pdb_code>')
def structures_route(pdb_code):
    """Endpoint returning the record for a structure.
    ---
    responses:
      200:
        description: A structure record
    """
    return handlers.structure_view_handler(pdb_code)


@api_handlers.route('/search')
def search_route():
    """Endpoint returning a set of structure records that match a search.
    ---
    parameters:
      - name: query
        in: query
        type: string
        required: true
      - name: page_number
        in: query
        type: string
        required: false
        default: 1
    responses:
      200:
        description: A set of structure records
    """
    # setting api=True returns full-fat listings (core records)
    return handlers.search_handler(api=True)


@api_handlers.route('/sets/<string:context>/<string:slug>')
def sets_route(context, slug):
    """Endpoint returning a set of structure records for a specific context (type of set) and slug (slugified name of set)
    ---
    responses:
      200:
        description: A set of structure records
    """
    return handlers.structure_browse_handler(context, slug, api=True)


@api_handlers.route('/collections/<string:slug>')
def collections_route(slug):
    """Endpoint returning a set of set records for a specific context (type of set)
    ---
    responses:
      200:
        description: A set of set records
    """
    return handlers.structure_collection_handler(slug)