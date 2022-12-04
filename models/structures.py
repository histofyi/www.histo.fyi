from functions.app import app_context


class StructureRecord():

    def __init__(self, pdb_code:str):
        cores = app_context.data['core']
        self.pdb_code = pdb_code.lower()
        if pdb_code not in cores:
            raise Exception('Structure not found. The pdb_code "{pdb_code}" is not in the dataset.'.format(pdb_code=pdb_code))
            self.structure_record = None
        else:
            self.structure_record = cores[pdb_code]

    def get(self):
        return self.structure_record


