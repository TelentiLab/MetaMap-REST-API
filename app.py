from dotenv import load_dotenv
from pathlib import Path
from utils.logger import logger
from flask import Flask
from flask_restful import Api
from resources.terms import Article, Keyword

# explicitly providing path to '.env'
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, verbose=True)

app = Flask(__name__)
api = Api(app)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # limit request size to 10MB
app.config['PROPAGATE_EXCEPTIONS'] = True
logger.info('app starts.')


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response


api.add_resource(Article, '/metamap/articles')
api.add_resource(Keyword, '/metamap/keyword/<string:keyword>')

if __name__ == '__main__':
    app.run(debug=True)
