from common.providers import filesystemProvider, s3Provider


def get_collection_colours():
    fs = filesystemProvider
    file, status, errors = fs.get('collection_colours.json')

