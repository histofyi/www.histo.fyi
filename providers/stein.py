from typing import Dict, List, Tuple
import json

import requests
from requests.auth import HTTPBasicAuth

#import base64
# TODO look at Stein authentication, doesn't play well with HTTPBasicAuth from requests

class steinProvider():

    def __init__(self, api_url:str, api_username:str, api_password:str):
        self.api_url = api_url
        self.api_username = api_username
        self.api_password = api_password


    def add(self, sheet:str, data:Dict) -> Tuple[Dict, bool, List]:
        errors = []
        url = f'{self.api_url}/{sheet}'
        payload = str(json.dumps([data]))
        r = requests.post(url, data=payload, auth=HTTPBasicAuth(self.api_username,  self.api_password))
        if r.status_code == 200:
            return r.json(), True, errors
        else:
            print (r.status_code)
            print (r.text)
            return r.json(), False, ['stein_errors']
