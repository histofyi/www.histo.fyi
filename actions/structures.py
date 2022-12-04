from typing import Dict, List
from functions.app import app_context
from fuzzywuzzy import fuzz

from models.sets import StructureSetMembers

import random

class StructureLookup():

    def __init__(self, pdb_code=None):
        self.pdb_code = pdb_code
        self.pdb_codes = app_context.data['pdb_codes']


    def get(self) -> Dict:
        if not self.pdb_code:
            return {'pdb_code':None, 'matches':StructureSetMembers.hydrate(self.get_random(self.pdb_codes, 10))}
        else:
            if self.pdb_code in self.pdb_codes:
                return {'exact_match':self.pdb_code}
            else:
                return self.get_fuzzy()

    
    def get_random(self, list:List, number:int) -> List:
        """
        This function returns a random selection of pdb_codes from the pdb code list

        Args:
            pdb_codes (List) - the list of pdb codes
            number (int) - the number of random pdb codes to return
        
        Returns:
            List - a list of randomly selected pdb codes
        """
        return random.sample(list, number)


    def get_fuzzy(self):
        best_matches = []
        matches = []
        for pdb_code in self.pdb_codes:
            score = fuzz.ratio(pdb_code, self.pdb_code)
            if score >= 75:
                best_matches.append(pdb_code)
            elif score >= 50:
                matches.append(pdb_code)
        if len(matches) > 5:
            matches = [pdb_code for pdb_code in matches if pdb_code not in best_matches]
            matches = self.get_random(matches, 5)
        if len(matches) == 0 and len(best_matches) == 0:
            matches = self.get_random(self.pdb_codes, 5)
        return {'pdb_code':self.pdb_code, 'best_matches':StructureSetMembers.hydrate(best_matches), 'matches':StructureSetMembers.hydrate(matches)}


