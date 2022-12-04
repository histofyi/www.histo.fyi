from typing import Dict, List, Union, Tuple

from algoliasearch.search_client import SearchClient


class algoliaProvider():

    def __init__(self, application_id:str, application_key:str, read_only:bool=False):
        self.application_id = application_id
        self.application_key = application_key
        self.read_only = read_only
        self.client = SearchClient.create(self.application_id, self.application_key)


    def index_item(self, pdb_code:str, index_name:str, data:Dict) -> Tuple[Dict, bool, List]:
        if not self.read_only:
            index = self.client.init_index(index_name)
            data['objectID'] = pdb_code
            index.save_object(data)
            return {'indexing_status':'done'}, True, None
        else:
            return {}, False, ['read_only_key']


    def search(self, index_name:str, search_terms:List, page_number:int, page_size:int = 25) -> Tuple[Dict, bool, List]:
        index = self.client.init_index(index_name)
        page = page_number - 1
        search_results = index.search(search_terms, {'hitsPerPage': page_size,'page': page})
        if 'hits' in search_results:
            return search_results, True, []
        else:
            return {}, False, ['no_hits']

    
