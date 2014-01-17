""" JSON Web Token implementation
 
Minimum implementation based on this spec:
http://self-issued.info/docs/draft-jones-json-web-token-01.html
"""
import base64
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
import time
 
try:
    import json
except ImportError:
    import simplejson as json
 
__all__ = ['encode', 'decode', 'DecodeError']
 
class DecodeError(Exception): pass
 
 
def base64url_decode(input):
    rem = len(input) % 4
    if rem > 0:
        input += '=' * (4 - rem)
    return base64.urlsafe_b64decode(input)
 
def base64url_encode(input):
    return base64.urlsafe_b64encode(input).replace('=', '')
 
def encode(payload, key, algorithm='sha256', password='notasecret'):
    segments = []
    header = {"typ": "JWT", "alg": algorithm}
    segments.append(base64url_encode(json.dumps(header)))
    segments.append(base64url_encode(json.dumps(payload)))
    signing_input = '.'.join(segments)
    try:
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        k = RSA.importKey(key)
        signature = PKCS1_v1_5.new(k).sign(SHA256.new(signing_input))
    except Exception as e:
        raise
    segments.append(base64url_encode(signature))
    return '.'.join(segments)
 
def decode(jwt):
    try:
        signing_input, crypto_segment = str(jwt).rsplit('.', 1)
        header_segment, payload_segment = signing_input.split('.', 1)
    except ValueError:
        raise DecodeError("Not enough segments")
    try:
        header = json.loads(base64url_decode(header_segment))
        payload = json.loads(base64url_decode(payload_segment))
        signature = base64url_decode(crypto_segment)
    except (ValueError, TypeError):
        raise DecodeError("Invalid segment encoding")
    return payload
 
 
def generate_keypair():
    pk = RSA.generate(2048)
    return pk.exportKey(), pk.publickey().exportKey()
 
def verify(jwt, *keys):
    try:
        signing_input, crypto_segment = str(jwt).rsplit('.', 1)
        header_segment, payload_segment = signing_input.split('.', 1)
    except ValueError:
        raise DecodeError("Not enough segments")
    try:
        header = json.loads(base64url_decode(header_segment))
        payload = json.loads(base64url_decode(payload_segment))
        signature = base64url_decode(crypto_segment)
    except (ValueError, TypeError):
        raise DecodeError("Invalid segment encoding")
    try:
        for key in keys:
            if isinstance(key, unicode):
                key = key.encode('utf-8')
            try:
                k = RSA.importKey(key)
                if PKCS1_v1_5.new(k).verify(
                    SHA256.new(signing_input), signature):
                    return key
            except Exception as e:
                pass
        else:
            raise DecodeError("Signature verification failed")
    except KeyError:
        raise DecodeError("Algorithm not supported")
 
 
 
default_root = "http://howe.iplantcollaborative.org:8080"
oauth_token = None
 
 
def get_assertion(pk='', *args, **kwargs):
    return {'assertion' : encode(create(*args, **kwargs), pk), 'grant_type' : 'urn:ietf:params:oauth:grant-type:jwt-bearer'}
 
def get_token(token_url=None, grant='urn:ietf:params:oauth:grant-type:jwt-bearer', pk='', *args, **kwargs):
    j = encode(create(*args, **kwargs), pk)
    try:
        import requests
        token = requests.post(token_url or (default_root + '/o/oauth2/token'), data={'assertion' : j, 'grant_type' : grant })
        if token.status_code == 200:
            if hasattr(token, 'json'):
                return str(token.json().get('access_token'))
            else:
                return str(json.loads(token.content).get('access_token'))
        else:
 
            return token
    except ImportError:
        return None
 
 
def call(endpoint, method="GET", iss=None, sub=None, pk=None, token=None, **kwargs):
    if pk and not pk.startswith('-----BEGIN RSA PRIVATE KEY-----'):
        with open(pk) as p:
            pk = p.read()
    elif not pk:
        with open('./private.key') as p:
            pk = p.read()
    
    global oauth_token
    if not token:
        if not oauth_token:
            oauth_token = get_token(pk=pk, iss=iss, sub=sub)
        token = oauth_token
  
    import requests
    
    if 'headers' in kwargs:
        headers = dict(kwargs.pop('headers'), Authorization='Bearer ' + token)
    else:
        headers = {'Authorization' : 'Bearer ' + token}
    
    r = requests.request(method.upper(), default_root + endpoint, headers = headers,  **kwargs)
    
    if r.status_code == 403:
        oauth_token = get_token(pk=pk, iss=iss, sub=sub)
        r = requests.request(method.upper(), default_root + endpoint, headers = headers,  **kwargs)
    
    return r
 
 
def create(iss, scope='admin', aud='api.iplantcollaborative.org', exp=None, iat=None, sub=None, **kwargs):
    t = exp or long(time.time())
    payload = {
        'iss'   : iss,
        'scope' : scope,
        'aud'   : aud or '',
        'iat'   : 0, #  Stupid timestamps are screwing up in some instances. I'll deal with this at some other time.
        'exp'   : t + 3600 # Token valid for 1 hour
        }
    if sub :
        payload['sub'] = sub
 
    payload.update(kwargs)
    return payload
 
 
import sys
 
 
 
if __name__ == '__main__' and not hasattr(sys, 'ps1'):
 
    import itertools
    import operator
    args = itertools.groupby(sys.argv, lambda x: '=' in x)
    pkey = None
    command = None
    jwt = None
    for k, g in args:
        if k:
            d = dict([arg.split('=', 1) for arg in g])
            jwt = create(**d)
        else:
            if jwt:
                pkey = next(g, None)
 
    if "-v" in sys.argv:
        print json.dumps(jwt)
    if pkey:
        with open(pkey, 'rb') as f:
            if "token" in sys.argv:
                t = get_token(pk=f.read(), **d)
                if isinstance(t, basestring):
                    print t
                else:
                    print t
                    sys.exit(1)
            else:
                print encode(jwt, f.read())
