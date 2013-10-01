""" 
JSON Web Token implementation
 
Minimum implementation based on this spec:
http://self-issued.info/docs/draft-jones-json-web-token-01.html
"""
import base64
from OpenSSL import crypto
from M2Crypto import BIO, RSA, m2
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
        #if key.startswith('-----BEGIN '):
            #pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key)
        #else:
            #pkey = crypto.load_pkcs12(key, password).get_privatekey()
        k = RSA.load_key_string(key, lambda x: None)
        signature = k.sign(signing_input, algorithm)
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
    pk = RSA.gen_key(2048, m2.RSA_F4, lambda x: None)
    private = pk.as_pem(None)
    pu = BIO.MemoryBuffer()
    pk.save_pub_key_bio(pu)
    public = pu.read()
    return private, public
 
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
                bio = BIO.MemoryBuffer(key)
                k = RSA.load_pub_key_bio(bio)
                k.verify(signing_input, signature, header['alg'])
                break #this causes the else block not to run. ie we have successfully verified
            except Exception as e:
                pass
        else:
            raise DecodeError("Signature verification failed")
    except KeyError:
        raise DecodeError("Algorithm not supported")
 
 
def create(iss, scope='', aud=None, exp=None, iat=None, prn=None, **kwargs):
    t = exp or long(time.time())
    payload = {
        'iss'   : iss,
        'scope' : scope,
        'aud'   : aud or '',
        'iat'   : t,
        'exp'   : t + 3600 # Token valid for 1 hour
        }
    if prn :
        payload['prn'] = prn
 
    payload.update(kwargs)
    return payload
 
 
import sys
 
 
if __name__ == '__main__' :
 
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
 
    print json.dumps(jwt)
    if pkey:
        with open(pkey, 'rb') as f:
            print encode(jwt, f.read())
 
