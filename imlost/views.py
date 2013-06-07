from pyramid.view import view_config
import pymongo
import hashlib
import time

USER_FIELDS = ['user_id', 'user_name', 'user_type', 'device_type', 'device_code', 'phone', 'password']
SALT = "imLost5aBadsf,>213" # need to move to config
ONLINE_THRESHOLD = 900 # 15 mins

# being called everytime
def update_online_status(access_token):
    pass

def encrypted_password(raw_password):
    h = hashlib.sha1(SALT)
    h.update(raw_password)
    return h.hexdigest()

def generate_token(id):
    h = hashlib.sha256("%s - %s - %s" % (SALT, id, time.time()))
    return h.hexdigest()

@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):
    return {'project': 'imLost'}

@view_config(route_name='signup', renderer='json', request_method='POST')
def signup(request):
    userdb = request.db['users']
    new_user = dict([(k,v) for k,v in request.params if k in USER_FIELDS])
    if len(new_user) != len(USER_FIELDS):
        return {'status_code':400, 'message':'Required fields not provided'}
    new_user['user_id'] = new_user['user_id'].lower()    
    # check if user exist
    if userdb.find_one({'user_id':new_user['user_id']}) != None:
        return {'status_code':403, 'message':'User already exists'}
    # encrypt password
    new_user['password'] = encrypted_password(new_user['password'])
    try:
        new_user['contacts'] = []
        new_user['last_seen'] = 0
        userdb.insert(new_user)
        return {'status_code':201, 'message':'User Created'}
    except:
        return {'status_code':500, 'message':'Unable to create user'}

@view_config(route_name='signin', renderer='json', request_method='POST')    
def signin(request):
    userdb = request.db['users']
    user_id = request.params['user_id']
    password = encrypted_password(request.params['password'])
    user = userdb.find_one({'user_id':user_id,'password':password})
    if user is None:
        return {'status_code':403, 'message':'Login failed'}
    access_token = generate_token(user['_id'])
    try:
        userdb.update({'_id':user['_id']}, {'$set':
                        {'access_token':access_token, 'last_seen':time.time()}})        
    except:
        return {'status_code':500, 'message':'Unable to login'}
    return {'status_code':200, 'result':{'access_token':access_token}}

@view_config(route_name='signout', renderer='json', request_method='GET')
def signout(request):
    userdb = request.db['users']
    access_token = request.params['access_token']
    user = userdb.find_one({'access_token':access_token})
    if user is None:
        return {'status_code':403, 'message':'Access denied'}
    else:
        userdb.update({'_id':user['_id']}, {'$set':
                        {'access_token':None, 'last_seen':0}})
    
    return {'code':200}

def get_contacts(request):
    userdb = request.db['users']
    access_token = request.params['access_token']
    user = userdb.find_one({'access_token':access_token})
    if user is None:
        return {'status_code':403, 'message':'Access denied'}
    contacts = user['contacts']
    if contacts is None:
        contacts = []
    else:
        for c in contacts:
            if time.time() - c['last_seen'] < ONLINE_THRESHOLD:
                c['online'] = True
            else:
                c['online'] = False
    
    return {'status_code':200, 'result':{'contacts':contacts}}

def add_contact(request):
    userdb = request.db['users']
    access_token = request.params['access_token']
    user = userdb.find_one({'access_token':access_token})
    contact_id = request.params['contact_id']
    contact = userdb.find_one({'user_id':contact_id})
    if user is None or contact is None:
        return {'status_code':403, 'message':'Access denied'}
    if userdb.find_one({'_id':user['_id'], 'contacts.user_id':contact_id}) is None:
        user.update({'_id':user['_id']}, {'$set':{'last_seen':time.time()},
                                          '$addToSet':{'contacts':{'contact_id':contact_id}}})
        return {'status_code':200, 'message':'Added contact'}
    else:
        return {'status_code':403, 'message':'Contact already exists'}

def update_location(request):
    userdb = request.db['users']
    access_token = request.params['access_token']
    lng = request.params['lng']
    lat = request.params['lat']
    user = userdb.find_one({'access_token':access_token})
    if user is None:
        return {'status_code':403, 'message':'Access denied'}
    
    userdb.update({'_id':user['_id']}, {'$set':{'last_seen':time.time(),'location':{'lng':lng,'lat':lat}}})
    userdb.update({'contacts.contact_id':user['user_id']}, 
                  {'$set':{'contacts.$.last_seen':time.time(),'contacts.$.location':{'lng':lng,'lat':lat}}})
    return {'status_code':200, 'message':'Location updated'}

def imLost(request):
    pass