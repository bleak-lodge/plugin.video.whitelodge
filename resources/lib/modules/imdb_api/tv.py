# -*- coding: utf-8 -*-

import requests
import datetime

now = datetime.datetime.now()

_GRAPHQL_IMDB_API_URL = 'https://graphql.imdb.com'
_GRAPHQL_IMDB_API_URL2 = 'https://graphql.prod.api.imdb.a2z.com/'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Referer': 'https://www.imdb.com/',
    'Origin': 'https://www.imdb.com',
    'Content-Type': 'application/json',
    'Accept-Language': 'en-US',
    'x-imdb-client-name': 'imdb-web-next',
    'x-imdb-user-language': 'en-US'
}
session = requests.Session()
session.headers.update(headers)


edges = """{
            edges {
              node {
                title {
                  id
                  titleText { text }
                  releaseYear { year }
                  releaseDate {
                    year
                    month
                    day
                  }
                  ratingsSummary {
                    aggregateRating
                    voteCount
                  }
                  plot { plotText { plainText } }
                  primaryImage { url }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
    """

def get_most_popular_tv(first, after, params):
    query = """
        query GetMostPopularTv($first: Int!, $after: String, $endDate: Date!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] },
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Reality-TV", "Game-Show"] },
              releaseDateConstraint: { releaseDateRange: { end: $endDate }}
            }
            sort: { sortBy: POPULARITY, sortOrder: ASC }
          ) %s
        }
    """ % edges

    endDate = now.strftime('%Y-%m-%d')

    request = {'query': query, 'variables': {'first': first, 'after': after, 'endDate': endDate}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()['data']['advancedTitleSearch']


def get_most_voted_tv(first, after, params):
    query = """
        query GetMostVotedTv($first: Int!, $after: String) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] },
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Reality-TV", "Game-Show"] }
            }
            sort: { sortBy: USER_RATING_COUNT, sortOrder: DESC }
          ) %s
        }
    """ % edges

    request = {'query': query, 'variables': {'first': first, 'after': after}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()['data']['advancedTitleSearch']


def get_top_rated_tv(first, after, params):
    query = """
        query GetTopRatedTv($first: Int!, $after: String) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] },
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Reality-TV", "Game-Show"] },
              userRatingsConstraint: { ratingsCountRange: { min: 10000 } }
            }
            sort: { sortBy: USER_RATING, sortOrder: DESC }
          ) %s
        }
    """ % edges

    request = {'query': query, 'variables': {'first': first, 'after': after}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()['data']['advancedTitleSearch']


def get_premier_tv(first, after, params):
    query = """
        query GetPremierTv($first: Int!, $after: String, $endDate: Date!, $startDate: Date!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] },
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Reality-TV", "Game-Show"] },
              languageConstraint: { allLanguages: ["en"] },
              releaseDateConstraint: { releaseDateRange: { start: $startDate, end: $endDate }},
              userRatingsConstraint: { ratingsCountRange: { min: 50 } }
            }
            sort: { sortBy: RELEASE_DATE, sortOrder: DESC }
          ) %s
        }
    """ % edges

    startDate = (now - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
    endDate = now.strftime('%Y-%m-%d')

    request = {'query': query, 'variables': {'first': first, 'after': after, 'startDate': startDate, 'endDate': endDate}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()['data']['advancedTitleSearch']


