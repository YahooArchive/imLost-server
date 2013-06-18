from pyramid.config import Configurator
from urlparse import urlparse
import pymongo


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)    
    # config mongodb
    db_url = urlparse(settings['mongo_uri'])
    config.registry.db = pymongo.Connection(
       host=db_url.hostname,
       port=db_url.port,
    )
   
    def add_db(request):
       db = config.registry.db[db_url.path[1:]]
       if db_url.username and db_url.password:
           db.authenticate(db_url.username, db_url.password)
       return db
    config.add_request_method(add_db, 'db', reify=True)
    
    # config routes
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('signin', '/signin')
    config.add_route('signup', '/signup')
    config.add_route('signout', '/signout')
    config.add_route('user_profile', '/user/{access_token}')
    config.add_route('update_profile', '/user/{access_token}')
    config.add_route('update_password', '/user/{access_token}/new_password')
    config.add_route('contacts', '/user/{access_token}/contacts')
    config.add_route('update_location', '/user/{access_token}/update_location')
    config.add_route('imlost', '/user/{access_token}/imlost')
    config.scan()
    return config.make_wsgi_app()

    