# -*- coding: utf-8 -*-

import requests
from .query import prepare_search_request, get_node_by_id, get_offers_by_id


_GRAPHQL_API_URL = 'https://apis.justwatch.com/graphql'


def search(title, object_types=[], years={}, country='US', language='en', count=5, best_only=False):
    """Search JustWatch for given title.
    Returns a list of entries up to count.

    Args:
        title: title to search
        object_types: list of media types to include in search, eg MOVIE, SHOW
        years: release years range in form {'min': int, 'max': int}
        country: country to search for offers, "US" by default
        language: language of responses, "en" by default
        count: how many responses should be returned
        best_only: return only best offers if True, return all offers if False

    Returns:
        JustWatch json response
    """
    request = prepare_search_request(title, object_types, years, country, language, count, best_only)
    response = requests.post(_GRAPHQL_API_URL, json=request)
    response.raise_for_status()
    return response.json()


def node_by_id(id, country='US'):
    request = get_node_by_id(id, country)
    response = requests.post(_GRAPHQL_API_URL, json=request)
    response.raise_for_status()
    return response.json()


def offers_by_id(id, country='US'):
    request = get_offers_by_id(id, country)
    response = requests.post(_GRAPHQL_API_URL, json=request)
    response.raise_for_status()
    return response.json()
