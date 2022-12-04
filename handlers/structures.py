from models.sets import StructureSet
from models.structures import StructureRecord
from models.collections import StructureCollection
from actions.structures import StructureLookup
from functions.forms import request_variables


def transform_neighbours(neighbours, assigned_chains):
    transformed_neighbours = {}
    intermediate_neighbours = neighbours['1']
    if 'peptide' in assigned_chains:
        peptide_chains = assigned_chains['peptide']['chains']
        for chain in intermediate_neighbours:
            if chain in peptide_chains:
                print ('hello')
                transformed_neighbours = intermediate_neighbours[chain]
                print (transformed_neighbours)
    if transformed_neighbours:
        return transformed_neighbours
    else:
        return None

def transform_pockets(pockets):
    return pockets['1']


def structure_view_handler(pdb_code):
    """
    This function is the structure view handler

    """
    if True:
        structure_record = StructureRecord(pdb_code).get()
        altered_structure_record = {}
        for key in structure_record:
            altered_structure_record[key] = structure_record[key]
        if 'peptide_neighbours' in altered_structure_record:
            altered_structure_record['peptide_neighbours'] = transform_neighbours(altered_structure_record['peptide_neighbours'], structure_record['assigned_chains'])
        if 'pockets' in altered_structure_record:
            altered_structure_record['pockets'] = transform_pockets(altered_structure_record['pockets'])
        return  {
            'structure':altered_structure_record,
            'display':True
         }
    #except Exception as error:
    #    return {
    #        'error':str(error),
    #        'error_code':404,
    #        'structure':None,
    #        'pdb_code':pdb_code,
    #        'suggestions':StructureLookup(pdb_code=pdb_code).get()
    #    }


def structure_lookup_handler():
    """
    This function is the structure lookup handler.

    It looks up pdb codes entered into the lookup form box, or in the query string

    If a single result is found, it redirects to the structure view page for that pdb code

    If there's no single match, some suggestions are given
    """
    variables = request_variables(None, params=['pdb_code'])
    pdb_code = variables['pdb_code']
    lookup = StructureLookup(pdb_code=pdb_code).get()
    if 'exact_match' in lookup:
        return {'redirect_to':f'/structures/view/{pdb_code}'}
    else:
        return lookup 


def structure_browse_handler(context, set_slug, api=False):
    """
    This function is the structure browse handler

    """
    variables = request_variables(None, params=['page_number'])
    if not variables['page_number']:
        page = 1
    else:
        page = int(variables['page_number'])
    if api:
        depth = 'core'
    else:
        depth = 'listings'
    page_size = 25
    itemset = StructureSet(context, set_slug).hydrate(page=page, page_size=25, depth=depth)
    return {'set':itemset}


def structure_collection_handler(collection_slug):
    """
    This function is the structure collection handler

    """
    if collection_slug in ['deposited','revised','released']:
        order = 'chronology'
    else:
        order = 'count'
    collection = StructureCollection(collection_slug).get(order=order)
    return {'collection':collection,'order':order}
