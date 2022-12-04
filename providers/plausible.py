from typing import Dict, List, Tuple
import json


import requests


class plausibleProvider():

    def __init__(self, domain:str):
        self.url = 'https://plausible.io/api/event'
        self.domain = domain


    def handle_event(self, event_name:str, site_url:str, props:Dict) -> Tuple[Dict, bool, List]:
        headers = {'Content-type': 'application/json'}
        payload = {'name': event_name, 'domain': 'histo.fyi','url':site_url,'props':props}
        r = requests.post(self.url, data=json.dumps(payload), headers=headers)
        print (r.content)
        if r.status_code == 200:
            return {'return':r.content}, True, []
        else:
            return {'return':r.content}, False, ['plausible_errors']



    def empty_search(self, query:str) -> Tuple[Dict, bool, List]:
        search_url = f'https://www.histo.fyi/search?query={query}'
        return self.handle_event('EmptySearch', search_url, {'query':query})


    def record_404(self, path:str) -> Tuple[Dict, bool, List]:
        error_url = f'https://www.histo.fyi/{path}'
        return self.handle_event('404', error_url, {'path':f'/{path}'})


