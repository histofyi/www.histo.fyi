from functions.app import app_context

class StructureCollection():
    
    def __init__(self, collection_slug):
        self.collection_slug = collection_slug

    def get(self, order='count'):
        if self.collection_slug in app_context.data['sets']:
            sets = app_context.data['sets'][self.collection_slug]

            if order == 'count':
                sort_list = sorted(sets, key=lambda x: int(sets[x]['count']))
                sorted_sets = {item:sets[item] for item in reversed(sort_list)}
            else:
                sorted_sets = {item:sets[item] for item in sets}
            return {
                'slug':self.collection_slug,
                'sets':sorted_sets
            }
        else:
            return {}

