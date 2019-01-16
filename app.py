import os
from metamapy import MetaMaPY
from flask import Flask
from flask_restful import Resource, Api, reqparse

app = Flask(__name__)
api = Api(app)
MAX_PROCESSES = int(os.getenv('MAX_PROCESSES', 1))

_cache = {}


class Terms(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('text', type=str, required=True, help="missing argument 'text' in request body.")
    parser.add_argument('keyword', type=str, required=True, help="missing argument 'keyword' in request body.")

    def post(self):
        data = self.parser.parse_args()
        metamapy = MetaMaPY(MAX_PROCESSES)
        cached_res = _cache.get(data['keyword'])
        if cached_res:
            return {'terms': cached_res}, 200

        res = metamapy.run(data['text'])
        _cache[data['keyword']] = res
        return {'terms': res}, 200


api.add_resource(Terms, '/metamap')

if __name__ == '__main__':
    app.run(debug=True)
