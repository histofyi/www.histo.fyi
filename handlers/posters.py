from functions.app import app_context

def poster_handler(year:str, conference:str) -> str:
    content_route = 'content{route}.html'.format(route=f'/posters/{year}/{conference}')
    with app_context.open_resource(content_route) as f:
        content = f.read().decode('UTF-8')
    return {'content': content}