from functions.forms import request_variables
from functions.app import app_context

from providers.stein import steinProvider
from providers.slack import slackProvider

import datetime

def feedback_form_page():
    variables = request_variables(None, ['url','feedback_type'])
    return {'variables':variables}


def feedback_form_handler():
    variables = request_variables(None, ['name','email','feedback','url','feedback_type','this_title'])
    if variables['name'] is not None and variables['email'] is not None and variables['feedback'] is not None:
        if variables['name'] not in ['Ritobill','CrytoBoype','Boype'] or variables['this_title'] is None:
            variables['feedback'] = '\n'.join(variables['feedback'].splitlines())
            variables['date'] = datetime.datetime.now().isoformat()
            stein = steinProvider(app_context.config['STEIN_API_URL'], app_context.config['STEIN_USERNAME'], app_context.config['STEIN_PASSCODE'])
            stein_response = stein.add('alpha', variables)
            slack = slackProvider(app_context.config['SLACK_WEBHOOK'])
            slack_response = slack.send('feedback', variables)
        return {'redirect_to': f'/feedback/thank-you'}
    else:
        return {'variables':variables, 'errors':True}