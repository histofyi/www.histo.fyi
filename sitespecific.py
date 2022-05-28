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
def get_species_sets(s3, key_provider):
    species_collection = {
        'class_i':[]
    }
    count = 0
    print ('hello')
    collection = get_collection('species')
    print (collection)
    for species in collection['members']:
        species_key = key_provider.set_key(species, 'structures', 'species')
        print (species_key)
        species_set, success, errors = s3.get(species_key)
        if species_set:
            species_collection['class_i'].append(species_set)
            count += len(species_set['members'])
    print(count)
    return species_collection