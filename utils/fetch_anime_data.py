import requests

def fetch_anime_results(anime_name):
    query = '''
    query ($search: String) {
        Page(page: 1, perPage: 10) {
            pageInfo {
                total
                currentPage
                lastPage
                hasNextPage
            }
            media(search: $search, type: ANIME, sort:[POPULARITY_DESC]) {
                title {
                    romaji
                    english
                }
                averageScore
                popularity
                season
                seasonYear
                status
                genres
                coverImage {
                    extraLarge
                }
                episodes
                isAdult
                nextAiringEpisode {
                    airingAt
                    timeUntilAiring
                    episode
                }
            }
        }
    }
    '''
    variables = {
    'search': anime_name
    }
    url = 'https://graphql.anilist.co'
    try:
      response = requests.post(url, json={'query': query, 'variables': variables})
      return response.json()['data']['Page']['media']
    except:
      return 'Error'