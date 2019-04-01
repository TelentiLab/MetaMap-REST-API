import settings
from flask import Flask
from flask_restful import Api
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from resources.terms import Article, Keyword

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=1)  # fix x-forwarded-for
limiter = Limiter(app, key_func=get_remote_address, default_limits=["2/second"])
api = Api(app)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # limit request size to 10MB
app.config['PROPAGATE_EXCEPTIONS'] = True


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response


api.add_resource(Article, '/metamap/articles')
api.add_resource(Keyword, '/metamap/keyword/<string:keyword>')

if __name__ == '__main__':
    app.run(debug=True)
