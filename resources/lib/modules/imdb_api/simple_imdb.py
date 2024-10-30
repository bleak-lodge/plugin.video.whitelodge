# -*- coding: utf-8 -*-

import requests

from .query import get_imdb_trailers

_GRAPHQL_IMDB_API_URL = 'https://graphql.imdb.com'
_GRAPHQL_IMDB_API_URL2 = 'https://graphql.prod.api.imdb.a2z.com/'
headers = {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Referer': 'https://www.imdb.com/',
        'Origin': 'https://www.imdb.com'
}


def _get_imdb_trailers(imdb_id):
    request = get_imdb_trailers(imdb_id)
    response = requests.post(_GRAPHQL_IMDB_API_URL2, headers=headers, json=request)
    response.raise_for_status()
    return response.json()
