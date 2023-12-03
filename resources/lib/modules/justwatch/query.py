# -*- coding: utf-8 -*-

_GRAPHQL_SEARCH_QUERY = """
query GetSearchTitles(
  $searchTitlesFilter: TitleFilter!,
  $country: Country!,
  $language: Language!,
  $first: Int!,
  $filter: OfferFilter!,
) {
  popularTitles(
    country: $country
    filter: $searchTitlesFilter
    first: $first
    sortBy: POPULAR
    sortRandomSeed: 0
  ) {
    edges {
      ...SearchTitleGraphql
      __typename
    }
    __typename
  }
}

fragment SearchTitleGraphql on PopularTitlesEdge {
  node {
    id
    objectId
    objectType
    content(country: $country, language: $language) {
      title
      fullPath
      originalReleaseYear
      externalIds {
        imdbId
        tmdbId
        __typename
      }
    }
    offers(country: $country, platform: WEB, filter: $filter) {
      monetizationType
      presentationType
      standardWebURL
      package {
        id
        packageId
        clearName
        technicalName
        __typename
      }
      id
      __typename
    }
    __typename
  }
  __typename
}
"""

def prepare_search_request(title, object_types, years, country, language, count, best_only):
    """Prepare search request for JustWatch GraphQL API.
    Creates a "GetSearchTitles" GraphQL query.
    Country code should be two uppercase letters, however it will be auto-converted to uppercase.

    Args:
        title: title to search
        country: country to search for offers
        language: language of responses
        count: how many responses should be returned
        best_only: return only best offers if True, return all offers if False

    Returns:
        JSON/dict with GraphQL POST body
    """
    return {
        "operationName": "GetSearchTitles",
        "variables": {
            "first": count,
            "searchTitlesFilter": {"searchQuery": title, "objectTypes": object_types, "releaseYear": years},
            "language": language,
            "country": country.upper(),
            "filter": {"bestOnly": best_only, "monetizationTypes": ["FLATRATE", "FREE", "ADS"]},
        },
        "query": _GRAPHQL_SEARCH_QUERY,
    }

##########################################################################################################################################

_GRAPHQL_NODEID_QUERY = """
        fragment Episode on Episode {
            __typename
            id
            # JustWatch seems to need a language for the seasonNumber and
            # episodeNumber, but the language also doesn't seem to have any
            # effect on them. So this uses a syntactically valid but nonexistent
            # language.
            content(country: $country, language: "qa-INVALID") {
                seasonNumber
                episodeNumber
            }
            offers(country: $country, platform: WEB) {
                monetizationType
                presentationType
                standardWebURL
                package {
                    id
                    packageId
                    clearName
                    technicalName
                }
            }
        }

        fragment Season on Season {
            __typename
            id
            content(country: $country, language: "qa-INVALID") {
                seasonNumber
            }
            episodes {
                ...Episode
            }
        }

        fragment Show on Show {
            __typename
            id
            seasons {
                ...Season
            }
        }

        fragment Movie on Movie {
            __typename
            id
            offers(country: $country, platform: WEB) {
                monetizationType
                presentationType
                standardWebURL
                package {
                    id
                    packageId
                    clearName
                    technicalName
                }
            }
        }

        fragment Node on Node {
            __typename
            id
            ...Episode
            ...Season
            ...Show
            ...Movie
        }

        query GetNodeById($nodeId: ID!, $country: Country!) {
            node(id: $nodeId) {
                ...Node
            }
        }

        query GetNodeByUrlPath($urlPath: String!, $country: Country!) {
            urlV2(fullPath: $urlPath) {
                node {
                    ...Node
                }
            }
        }
        """

def get_node_by_id(id, country):
    return {
        "operationName": "GetNodeById",
        "variables": {"nodeId": id, "country": country.upper()},
        "query": _GRAPHQL_NODEID_QUERY,
    }

##########################################################################################################################################

_GRAPHQL_OFFERS_QUERY = """
query GetTitleOffers(
    $nodeId: ID!,
    $country: Country!,
    $language: Language!,
    $filterFlatrate: OfferFilter!,
    $platform: Platform! = WEB
) {
    node(id: $nodeId) {
        id
        __typename
        ... on MovieOrShowOrSeasonOrEpisode {
                offerCount(
                    country: $country,
                    platform: $platform
                )
                flatrate: offers(
                    country: $country,
                    platform: $platform,
                    filter: $filterFlatrate
                ) {
                    ...TitleOffer
                    __typename
                  }
                free: offers(
                    country: $country,
                    platform: $platform,
                    filter: $filterFree
                ) {
                    ...TitleOffer
                    __typename
                  }
            __typename
            }
        }
    }


fragment TitleOffer on Offer {
    id
    presentationType
    monetizationType
    package {
        id
        packageId
        clearName
        technicalName
        __typename
    }
    standardWebURL
    deeplinkRoku: deeplinkURL(platform: ROKU_OS)
    __typename
}
"""

def get_offers_by_id(id, country):
    return {
        "operationName": "GetTitleOffers",
        "variables": {"nodeId": id, "country": country, "bestOnly": False},
        "query": _GRAPHQL_OFFERS_QUERY,
    }



