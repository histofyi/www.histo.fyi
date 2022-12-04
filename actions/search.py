import re
from functions.helpers import slugify
from functions.app import app_context


def parse_query(query):
    query = query.lower()
    slug = None
    if query is not None:
        querytype = None
        if ' ' in query:
            querytype = 'fulltext'
            slug = None
        elif 'mer' in query:
            length = query.replace('mer','') 
            length_number_query = '[0-9]{1,2}'
            if re.search(length_number_query, length):
                peptide_lengths = app_context.data['peptide_lengths']
                if str(length) in peptide_lengths:
                    querytype = 'peptide_lengths'
                    slug = peptide_lengths[str(length)]
                else:
                    querytype = 'fulltext'
            else:
                querytype = 'peptide_lengths'
                slug = query.lower()
        elif '-' in query:
            if '*' in query:
                if ':' in query:
                    querytype = 'alleles'
                    slug = slugify(query)
                else:
                    numbers = query.split('*')[1]
                    if len(numbers) < 4:
                        querytype = 'allele_groups'
                        slug = slugify(query)
                    else:
                        querytype = 'alleles'
                        numbers = f'{numbers[0:2]}:{numbers[2:]}'
                        slug = slugify(f'{query.split("*")[0]}*{numbers}')
                query = query.upper()
            elif 'h2-' in query: # special case for mouse
                if len(query) > 4:
                    querytype = 'alleles'
                    slug = slugify(query)
                else:
                    querytype = 'locus'
                    slug = slugify(query)
            else:
                species_stem = query.split('-')[0]
                locus_stem = query.split('-')[1]

                sepcies_stem_query = '[a-z]{3,4}'
                hla_locus_query = '[d]{1}[a-z]{1,3}[0-9]{1,2}'
                hla_allele_query = '.[0-9]{1,4}'

                if re.search(sepcies_stem_query, species_stem):
                    querytype = 'maybe'
                else:
                    querytype = 'fulltext'

                if querytype == 'maybe':
                    if re.search(hla_allele_query, locus_stem):
                        if re.search(hla_locus_query, locus_stem):
                            querytype = 'loci'
                            slug = slugify(query)
                        else:   
                            if 'w' in locus_stem:
                                locus_stem = locus_stem.replace('w','')
                            match = re.match(r"([a-z]+)([0-9]+)", locus_stem, re.I)    
                            if match:
                                items = match.groups()
                                locus = items[0]
                                numbers = str(items[1])
                                if len(numbers) > 2:
                                    if len(numbers) == 3:
                                        numbers = f'0{numbers}'
                                    slug = f''
                                    querytype = 'alleles'
                                    numbers = f'{numbers[0:2]}:{numbers[2:]}'
                                elif locus in ['a','b','c','e','f']:
                                    if len(numbers) == 1:
                                        numbers = f'0{numbers}'
                                    querytype = 'allele_groups'
                                query = f'{species_stem}-{locus}*{numbers}'.upper()
                                slug = slugify(query)
                    else:
                        querytype = 'loci'
            if querytype == 'maybe':
                querytype = 'loci'
        else:
            peptide_query = '[acdefghiklmnpqrstwyx]{8,20}'
            if re.search(peptide_query, query):
                querytype = 'peptide_sequences'
                slug = query
                query = query.upper()
            else:
                querytype = 'fulltext'
    # TODO handle non-classical with a rule
    return {'query':query, 'querytype':querytype, 'slug':slug}