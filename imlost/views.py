from pyramid.view import view_config
from pyramid.paster import get_appsettings
import pymongo
import time
from applepushnotification import *

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
    new_user = dict([(k,v) for k,v in request.params.items() if k in USER_FIELDS])
    if len(new_user) != len(USER_FIELDS):
        return response_wrapper(400, 'Required fields not provided')
    if new_user['user_type'] not in USER_TYPES:
        return response_wrapper(400, 'User type must be: caretaker or dependant')
    new_user['user_id'] = new_user['user_id'].lower()    
    # check if user exist
    if userdb.find_one({'user_id':new_user['user_id']}) is not None:
        return response_wrapper(403, 'User already exists')
    # encrypt password
    new_user['password'] = encrypted_password(new_user['password'])
    try:
        new_user['contacts'] = []
        new_user['location'] = {'lat':None, 'lng':None}
        new_user['last_seen'] = time.time()
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

@view_config(route_name='user_profile', request_method='GET')
def get_profile(request):
    user = get_current_user(request)
    for k in user.keys():
        if k not in ['user_id','user_name','user_type','device_type','device_token','phone']:
            user.pop(k)
    return response_wrapper(200, 'OK', {'user':user})

@view_config(route_name='user_profile', request_method='PUT')
def update_profile(request):
    user = get_current_user(request)
    params = dict([(k,v) for k,v in request.params.iteritems() if k in CHANGEABLE_FIELDS])
    userdb = request.db['users']
    userdb.update({'_id':user['_id']}, {'$set':params})
    return response_wrapper(200, 'OK')

@view_config(route_name='update_password', request_method='PUT')
def update_password(request):
    user = get_current_user(request)
    old_password = request.params.get('old_password', None)
    new_password = request.params.get('new_password', None)
    if old_password is None or new_password is None:
        return response_wrapper(403, 'Old password or new password not provided')
    old_password = encrypted_password(old_password)
    if old_password != user['password']:
        return response_wrapper(403, 'Old password is incorrect')
    else:
        userdb = request.db['users']
        userdb.update({'_id':user['_id']}, {'$set':
                            {'password':encrypted_password(new_password)}})
        return response_wrapper(200, 'OK')

@view_config(route_name='contacts', request_method='GET')
def get_contacts(request):
    user = get_current_user(request)
    contacts = user['contacts']
    if contacts is None:
        contacts = []
    else:
        for c in contacts:
            c.pop('_id')
            if time.time() - c['last_seen'] < ONLINE_THRESHOLD:
                c['online'] = True
            else:
                c['online'] = False
    
    return response_wrapper(200, 'OK', {'contacts':contacts})

@view_config(route_name='contacts', request_method='POST')
def add_contact(request):
    # send a request to another user to make a connection
    user = get_current_user(request)
    contact_id = request.params['contact_id'].lower()
    # check if already in the contact list
    for c in user['contacts']:
        if c['user_id'] == contact_id:
            return response_wrapper(400, 'Contact already exists')
    userdb = request.db['users']
    new_contact = userdb.find_one({'user_id':contact_id})
    if new_contact is None:
        return response_wrapper(500,'Contact not exist')
    userdb.update({'_id':user['_id']}, {'$addToSet':{'contacts':{'user_id':contact_id, 'status':'waiting'}}})
    user_data = extract_public_info(user)
    user_data['status'] = 'pending'
    userdb.update({'_id':new_contact['_id']}, {'$addToSet':{'contacts':user_data}})
    return response_wrapper(200, 'OK')

@view_config(route_name='contacts', request_method='PUT')
def accept_contact(request):
    user = get_current_user(request)
    contact_id = request.params['contact_id'].lower()
    if contact_id not in [c['user_id'] for c in user['contacts']]:
        return response_wrapper(400, 'No such contact')
    userdb = request.db['users']
    userdb.update({'_id':user['_id'], 'contacts.user_id':contact_id}, 
                  {'$set':{'contacts.$.status':'accepted'}})
    user_data = extract_public_info(user)
    user_data['status'] = 'accepted'
    print user_data
    userdb.update({'user_id':contact_id, 'contacts.user_id':user['user_id']}, 
                  {'$set':{'contacts.$':user_data}})
    return response_wrapper(200, 'OK')

# @view_config(route_name='contacts', request_method='DELETE')
# def remove_contact(request):
#     #TODO
#     pass 

@view_config(route_name='update_location', request_method='PUT')
def update_location(request):
    user = get_current_user(request)
    userdb = request.db['users']
    lng = request.params['lng']
    lat = request.params['lat']
    userdb.update({'_id':user['_id']}, {'$set':{'last_seen':time.time(),'location':{'lng':lng,'lat':lat}}})
    userdb.update({'contacts.user_id':user['user_id']}, 
                  {'$set':{'contacts.$.last_seen':time.time(),'contacts.$.location':{'lng':lng,'lat':lat}}})
    return response_wrapper(200, 'OK')

@view_config(route_name='imlost', request_method='PUT')
def i_am_lost(request):
    user = get_current_user(request)
    if user['user_type'] != 'dependant':
        return response_wrapper(400, 'You cannot be lost')
    userdb = request.db['users']
    lng = request.params['lng']
    lat = request.params['lat']
    time_stamp = time.strftime('%H:%M:%S %D')
    userdb.update({'_id':user['_id']}, {'$set':{'last_seen':time.time(),'location':{'lng':lng,'lat':lat}}})
    userdb.update({'contacts.user_id':user['user_id']}, 
                  {'$set':{'contacts.$.last_seen':time.time(),'contacts.$.location':{'lng':lng,'lat':lat}}})
    # send push notifications 
    # TODO: should use a subprocess to do it
    service = NotificationService(certfile=get_appsettings('apns_cert'))
    for c in user['contacts']:
        if c['status'] == 'accepted' and c['device_type'] == 'apple':
            token = c['device_token'].decode('hex')
            msg = "%s is lost, your help is needed (%s)" % (user['user_name'], time_stamp)
            service.send(msg)
            service.wait_send()
    service.stop()
    return response_wrapper(200, 'OK')
            
    
        
    