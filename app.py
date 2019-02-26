from logger import logger
from flask import Flask
from flask_restful import Api
from resources.variant import Variant

app = Flask(__name__)
api = Api(app)
app.config['PROPAGATE_EXCEPTIONS'] = True
logger.info('app starts.')


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response


api.add_resource(Variant, '/metamap/rsid/<string:rsid>')

if __name__ == '__main__':
    app.run(debug=True)
