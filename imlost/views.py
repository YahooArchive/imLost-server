from pyramid.view import view_config
import pymongo
import hashlib
import time

from .common import *
from .helpers import *

@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):
    return {'project': 'imLost'}

@view_config(context=PermissionFailure)
def no_permission(exc, request):
    return response_wrapper(403, "Access Denied")

@view_config(route_name='signup', request_method='POST')
def signup(request):
    userdb = request.db['users']
    new_user = dict([(k,v) for k,v in request.params if k in USER_FIELDS])
    if len(new_user) != len(USER_FIELDS):
        return response_wrapper(400, 'Required fields not provided')
    new_user['user_id'] = new_user['user_id'].lower()    
    # check if user exist
    if userdb.find_one({'user_id':new_user['user_id']}) != None:
        return response_wrapper(403, 'User already exists')
    # encrypt password
    new_user['password'] = encrypted_password(new_user['password'])
    try:
        new_user['contacts'] = []
        new_user['last_seen'] = 0
        userdb.insert(new_user)
        return response_wrapper(201, 'User Created')
    except:
        return response_wrapper(500, 'Unable to create user')

@view_config(route_name='signin', request_method='POST')    
def signin(request):
    userdb = request.db['users']
    user_id = request.params['user_id']
    password = encrypted_password(request.params['password'])
    user = userdb.find_one({'user_id':user_id,'password':password})
    if user is None:
        return response_wrapper(403, 'Login failed')
    access_token = generate_token(user['_id'])
    try:
        userdb.update({'_id':user['_id']}, {'$set':
                        {'access_token':access_token, 'last_seen':time.time()}})        
    except:
        return response_wrapper(403, 'Unable to login')
    return response_wrapper(200, 'OK', {'access_token':access_token})

@view_config(route_name='signout', request_method='GET')
def signout(request):
    user = get_current_user(request)
    userdb = request.db['users']
    userdb.update({'_id':user['_id']}, {'$set':
                        {'access_token':None, 'last_seen':0}})
    return response_wrapper(200, 'OK')

def get_contacts(request):
    user = get_current_user(request)
    contacts = user['contacts']
    if contacts is None:
        contacts = []
    else:
        for c in contacts:
            if time.time() - c['last_seen'] < ONLINE_THRESHOLD:
                c['online'] = True
            else:
                c['online'] = False
    
    return response_wrapper(200, 'OK', {'contacts':contacts})

def add_contact(request):
    user = get_current_user(request)
    userdb = request.db['users']
    if userdb.find_one({'_id':user['_id'], 'contacts.user_id':contact_id}) is None:
        user.update({'_id':user['_id']}, {'$addToSet':{'contacts':{'contact_id':contact_id}}})
        return response_wrapper(200, 'OK')
    else:
        return response_wrapper(403, 'Contact already exists')

def update_location(request):
    user = get_current_user(request)
    userdb = request.db['users']
    lng = request.params['lng']
    lat = request.params['lat']
    userdb.update({'_id':user['_id']}, {'$set':{'last_seen':time.time(),'location':{'lng':lng,'lat':lat}}})
    userdb.update({'contacts.contact_id':user['user_id']}, 
                  {'$set':{'contacts.$.last_seen':time.time(),'contacts.$.location':{'lng':lng,'lat':lat}}})
    return response_wrapper(200, 'OK')

def i_am_lost(request):
    user = get_current_user(request)
    lng = request.params['lng']
    lat = request.params['lat']
    