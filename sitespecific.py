from common.providers import filesystemProvider, s3Provider
from cache import cache



def get_json_file(filename):
    fs = filesystemProvider('constants')
    file, success, errors = fs.get(filename)
    if success:
        return file
    else:
        return None


def get_collection_colours():
    return get_json_file('collection_colours')


def get_collection(collection_name):
    return get_json_file(collection_name)


#@cache.memoize(timeout=120)
def get_collection_sets(s3, key_provider, collection_name):
    count = 0
    collection = get_collection(collection_name)
    if collection is not None:
        context = collection['context']
        collection['hydrated_members'] = {}
        collection['all_members'] = []
        for thing in collection['members']:
            thing_key = key_provider.set_key(thing, 'structures', context)
            thing_set, success, errors = s3.get(thing_key)
            if thing_set:
                collection['hydrated_members'][thing] = thing_set
                collection['all_members'] += thing_set['members']
    return collection



def get_collection_items(s3, key_provider, collection_slug):
    collection = get_collection(collection_slug)
    if collection is not None:
        context = collection['context']
        collection['hydrated_members'] = {}
        collection['all_members'] = []
        for set_slug in collection['members']:
            item_key = key_provider.set_key(set_slug.replace('.json',''), 'structures', context)
            item_set, success, errors = s3.get(item_key)
            if success:
                collection['hydrated_members'][set_slug] = item_set
                collection['all_members'] += item_set['members']
    return collection
