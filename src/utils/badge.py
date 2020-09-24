import json
import os

import requests

graphql_url = os.getenv('GRAPHQL_URL', 'https://graph.codeday.org')


def get_badges():
    """returns a list of all badges in contentful"""
    query = '''
    {
      cms {
        badges(limit:null) {
          items {
            id,
            name,
            description,
            emoji
          }
          }
        }
    }
    '''
    r = requests.post(graphql_url, json={'query': query})
    badges = json.loads(r.text)['data']['cms']['badges']['items']
    return badges


def get_badges_by_discord_id(discord_id):
    """returns a list of json objects containing badge details"""
    query = '''
    {
      account {
        getUser(where: {discordId: "''' + str(discord_id) + '''"}, fresh: true) {
          badges {
            details {
              id,
              name,
              description,
              emoji
            }
          }
        }
      }
    }
    '''
    r = requests.post(graphql_url, json={'query': query})
    badges = json.loads(r.text)['data']['account']['getUser']['badges']
    return badges


print(get_badges())
print(get_badges_by_discord_id(486018241244954635))
