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
    config.scan()
    return config.make_wsgi_app()

    