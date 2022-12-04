from typing import List, Dict, Tuple, Union
from flask import current_app
import math


class StructureSetMembers():

    def hydrate(members, depth='listings'):
        if depth == 'listings':
            hydration = current_app.data['listings']
        else:
            hydration = current_app.data['core']
        return [hydration[pdb_code] for pdb_code in members]

  
class StructureSet():

    def __init__(self, context:str, slug:str):
        self.errors = []
        self.context = context
        self.slug = slug
        self.sets = current_app.data['sets']
        if context in self.sets:
            if slug in self.sets[context]:
                self.set = self.sets[context][slug]
                self.set['slug'] = slug
                self.set['context'] = context
            else:
                self.set = None
                raise Exception('Set not found error. No set named "{slug}" could be found within the contect "{context}"'.format(slug=slug,context=context))
        else:
            self.set = None
            raise Exception('Context not found error. No context named "{context}" could be found'.format(context=context))


    def paginate(self, page, page_size):
        all = self.get()['members']
        last_page = math.ceil(len(all) / page_size)
        first_record = (page -1)*page_size
        last_record = (page * page_size)
        members = all[first_record:last_record]
        pagination = {
            'current_page':page,
            'page_count':last_page,
            'page_size':page_size,
            'pages': [page_number for page_number in range(1,last_page + 1)],
            'total':len(all)
        }
        return pagination, members


    def get(self, page=None, page_size=None):
        if not page_size:
            return self.set
        else:
            return self.paginate(page, page_size)

    
    def hydrate(self, page=None, page_size=None, depth='listings'):

        hydrated_set = {}
        for key in self.set:
            hydrated_set[key] = self.set[key]
        if page and page_size:
            pagination, members = self.paginate(page, page_size)
            hydrated_set['pagination'] = pagination
        else:
            self.get()
            members = self.set['members']
        hydrated_set['members'] = StructureSetMembers.hydrate(members, depth=depth)
        return hydrated_set




