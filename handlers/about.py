from functions.app import app_context

def about_handler(route):
    navigation = [
        {'url': '/about/','title': 'About histo.fyi'},
        {'url': '/about/why-needed','title': 'Why is this resource needed?'},
        {'url': '/about/how-can','title': 'How can the data be used?'},
        #{'url': '/about/structural-introduction-to-class-i','title': 'A structural introduction to MHC Class I molecules'},
        #{'url': '/about/mhc-binding-molecules','title': 'Information about molecules which bind to MHC molecules'},
        {'url': '/about/data-provenance','title': 'Data provenance'},
        #{'url': '/about/data-pipeline','title': 'Data pipeline'},
        {'url': '/about/why-histo','title': 'Why histo.fyi?'},
        {'url': '/about/technology-used','title': 'Technology used'},
        #{'url': '/about/acknowledgements-and-references','title': 'Acknowledgements and references'},
        {'url': '/about/contact','title': 'Contact'},
        {'url': '/about/team','title': 'Team'},
        {'url': '/feedback?feedback_type=general','title': 'Feedback'}
    ]
    content_route = f'content/{route}.html'
    with app_context.open_resource(content_route) as f:
        content = f.read().decode('UTF-8')
    if '---' in content:
        elements = [element.strip() for element in content.split('---')]
        metadata = {}
        for row in [element for element in elements[1].split('\n')]:
            key = row.split(':')[0]
            value = row.split(':')[1]
            metadata[key] = value
        content = elements[2]
        if '{{static_route}}' in content:
            content = content.replace('{{static_route}}', app_context.config['STATIC_ROUTE'])
    else:
        metadata = None
    return {'content': content, 'route':route, 'navigation':navigation, 'metadata':metadata}

