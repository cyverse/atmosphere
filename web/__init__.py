"""
Atmosphere web helper methods..

"""
from threepio import logger


def extractUser(request):
    from core.models import AtmosphereUser as DjangoUser
    if request and request.session:
        username = request.session.get('username', None)
    if not username and request and request.META:
        username = request.META.get('username', None)
    if not username:
        username = 'esteve'
    return DjangoUser.objects.get_or_create(username=username)[0]


def getRequestParams(request):
    """
    Extracts paramters from GET/POST in a Django Request object
    """
    if request.META['REQUEST_METHOD'] == 'GET':
        try:
            #Will only succeed if a GET method with items
            return dict(request.GET.items())
        except:
            pass
    elif request.META['REQUEST_METHOD'] == 'POST':
        try:
            #Will only succeed if a POST method with items
            return dict(request.POST.items())
        except:
            pass
    logger.debug("REQUEST_METHOD is neither GET or POST.")


def getRequestVars(request):
    """
    Extracts parameters from a Django Request object
    Expects ALL or NOTHING. You cannot mix data!
    """

    username = None
    token = None
    api_server = None
    emulate = None
    try:
        #Attempt #1 - SessionStorage - Most reliable
        logger.debug(request.session.items())
        username = request.session['username']
        token = request.session['token']
        api_server = request.session['api_server']
        emulate = request.session.get('emulate', None)
        return {'username': username, 'token': token, 'api_server': api_server,
                'emulate': emulate}
    except KeyError:
        pass
    try:
        #Attempt #2 - Header/META values, this is DEPRECATED as of v2!
        logger.debug(request.META.items())
        username = request.META['HTTP_X_AUTH_USER']
        token = request.META['HTTP_X_AUTH_TOKEN']
        api_server = request.META['HTTP_X_API_SERVER']
        emulate = request.META.get('HTTP_X_AUTH_EMULATE', None)
        return {'username': username, 'token': token,
                'api_server': api_server, 'emulate': emulate}
    except KeyError:
        pass
    try:
        #Final attempt - GET/POST values
        params = getRequestParams(request)
        logger.debug(params.items())
        username = params['HTTP_X_AUTH_USER']
        token = params['HTTP_X_AUTH_TOKEN']
        api_server = params['HTTP_X_API_SERVER']
        emulate = params.get('HTTP_X_AUTH_EMULATE', None)
        return {'username': username, 'token': token,
                'api_server': api_server, 'emulate': emulate}
    except KeyError:
        pass
    return None
