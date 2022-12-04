from models.sets import StructureSet
from functions.app import app_context


def home_handler():
    """
    This is the home action.

    """
    try:
        latest = StructureSet('website','latest').hydrate()
    except Exception as error:
        latest = None
        print (error)
    total_structures = len(app_context.data['index']['deposition_date_asc'])
    print (total_structures)
    page_data = {
        'collections':app_context.data['collections']['homepage'],
        'latest':latest,
        'total_structures':total_structures
    }
    return page_data