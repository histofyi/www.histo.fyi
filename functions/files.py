import json

def load_json(filekey:str):
    with open(f'data/{filekey}.json') as json_file:
        json_data = json.load(json_file)
    return json_data
