from providers.plausible import plausibleProvider

def handle_404(path):
    plausible = plausibleProvider('histo.fyi')
    plausible.record_404(path)
    return {'path': path, 'code':404}