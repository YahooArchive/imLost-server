# helper functions

from .common import *
from pyramid.response import Response
import json
import time
import hashlib

USER_PUBLIC_FIELDS = ['_id', 'user_id', 'user_name', 'user_type', 'phone', 'last_seen', 'location', 'device_type', 'device_token']

class PermissionFailure(Exception):
    pass

def response_wrapper(status_code, message, result=None):
    resp = Response(status_code=status_code, content_type='application/json')
    data = {'status_code':status_code, 'message':message}
    if result is not None:
        data['result'] = result
    resp.body = json.dumps(data)
    return resp

# being called everytime
def get_current_user(request):
    userdb = request.db['users']
    access_token = request.params['access_token']
    if access_token is None:
        raise LoginFailure()
    user = userdb.find_one({'access_token':access_token})
    if user is not None:
            # update online time
            userdb.update({'_id':user['_id']}, {'$set':{'last_seen':time.time()}})
    else:
        raise PermissionFailure()
    return user

def encrypted_password(raw_password):
    h = hashlib.sha1(SALT)
    h.update(raw_password)
    return h.hexdigest()

def generate_token(id):
    h = hashlib.sha256("%s - %s - %s" % (SALT, id, time.time()))
    return h.hexdigest()

def extract_public_info(user):
    return dict([(k,v) for k,v in user.iteritems() if k in USER_PUBLIC_FIELDS])