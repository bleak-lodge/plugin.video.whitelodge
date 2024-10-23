# -*- coding: utf-8 -*-

"""
        query fn($id: ID!, $first: Int!, $paginationToken: ID, $EXTRA_PARAMS) {
            list(id: $id) {
                items(first: $first, after: $paginationToken, sort: { by: CREATED_DATE, order: DESC }) {
                    titles: edges {
                        node {
                            item {
                                ...Title
                            }
                        }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
        }
"""

_GRAPHQL_LIST_QUERY = """
        query fn($first: Int!, $EXTRA_PARAMS) {
                    fanPicksTitles(first: $first) {
                        titles: edges {
                            node {
                                ...Title
                            }
                        }
                    }
                }


        fragment Title on Title {
            id
            titleType {
                id
            }
            titleText {
                text
            }
            originalTitleText {
                text
            }
            primaryImage {
                url
                width
                height
                type
            }
            releaseYear {
                year
            }
            releaseDate {
                day
                month
                year
            }
            ratingsSummary {
                aggregateRating
                voteCount
            }
            certificate {
                rating
            }
            runtime {
                seconds
            }
            plot {
                plotText {
                    plainText
                }
            }
            genres {
                genres(limit: 5) {
                    text
                }
            }
            primaryVideos(first: 100) {
                edges {
                    node {
                        id
                    }
                }
            }
            principalCredits {
                category {
                    text
                }
                credits {
                    name {
                        id
                        nameText {
                            text
                        }
                        primaryImage {
                            url
                            width
                            height
                            type
                        }
                    }
                    ... on Cast {
                        characters {
                            name
                        }
                    }
                }
            }
            countriesOfOrigin {
                countries(limit: 5) {
                    text
                }
            }
            companyCredits(first: 1) {
                edges {
                    node {
                        company {
                            companyText {
                                text
                            }
                        }
                        category {
                            text
                        }
                    }
                }
            }
            taglines(first: 1) {
                edges {
                    node {
                        text
                    }
                }
            },
            episodes {
                isOngoing
                seasons {
                    number
                }
            }
            isAdult
        }

    """

def get_imdb_list(id):
    return {
        'operationName': 'fn',
        'query': _GRAPHQL_LIST_QUERY,
    }


def get_imdb_trailers(imdb_id):
    _GRAPHQL_TRAILERS_QUERY = '''query (
            $id: ID!
        ) {
            title(
                id: $id
            ) {
                titleText {
                    text
                }
                primaryVideos(first: 100) {
                    edges {
                        node {
                            id
                            name {
                                value
                            }
                            contentType {
                                displayName {
                                    value
                                }
                            }
                            description {
                                value
                            }
                            thumbnail {
                                url
                            }
                            primaryTitle {
                                id
                            }
                        }
                    }
                }
            }
        }
        '''

    variables = {'id': imdb_id}
    return {'query': _GRAPHQL_TRAILERS_QUERY, 'variables': variables}

