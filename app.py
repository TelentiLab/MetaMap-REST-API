import os
from flask import Flask
from flask_restful import Resource, Api, reqparse
from metamapy import MetaMaPY
from query_cache import QueryCache

app = Flask(__name__)
api = Api(app)
MAX_PROCESSES = int(os.getenv('MAX_PROCESSES', 1))
CACHE_SIZE = int(os.getenv('CACHE_SIZE', 30))

_cache = QueryCache(CACHE_SIZE)


class Terms(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('text', type=str, required=True, help="missing argument 'text' in request body.")
    parser.add_argument('keyword', type=str, required=True, help="missing argument 'keyword' in request body.")

    def post(self):
        data = self.parser.parse_args()
        metamapy = MetaMaPY(MAX_PROCESSES)
        if data['keyword'] in _cache:   # try to use cache first
            return {'terms': _cache.get(data['keyword'])}, 200

        res = metamapy.run(data['text'])    # run MetaMap if cache misses
        _cache.remember(data['keyword'], res)
        return {'terms': res}, 200


api.add_resource(Terms, '/metamap')

if __name__ == '__main__':
    app.run(debug=True)
