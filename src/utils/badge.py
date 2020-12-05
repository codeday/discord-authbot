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
              id
              name
              description
              emoji
              earnMessage
            }
          }
        }
      }
    }
    '''
    r = requests.post(graphql_url, json={'query': query})
    badges = json.loads(r.text)['data']['account']['getUser']['badges']
    return badges or []


def get_badges_by_username(username):
    """returns a list of json objects containing badge details"""
    query = '''
    {
      account {
        getUser(where: {username: "''' + str(username) + '''"}, fresh: true) {
          badges {
            details {
              id
              name
              description
              emoji
              earnMessage
            }
          }
        }
      }
    }
    '''
    r = requests.post(graphql_url, json={'query': query})
    badges = json.loads(r.text)['data']['account']['getUser']['badges']
    return badges


def username_from_discord_id(discord_id):
    query = '''
    {
      account {
        getUser(where: {discordId: "''' + discord_id + '''"}, fresh: true) {
          username
          }
        }
      }
    '''
    r = requests.post(graphql_url, json={'query': query})
    username = json.loads(r.text)['data']['account']['getUser']['username']
    return username


def grant_badge_by_username(badge_id, username, token):
    query = '''
    mutation {
      account {
        grantBadge(username:"''' + username + '''", badge:{id: "''' + badge_id + '''"})
      }
    }
    '''
    r = requests.post(graphql_url, json={'query': query}, headers={
                      'Authorization': f'Bearer {token}'})
    return get_badges_by_username(username)


def grant_badge_by_discord_id(badge_id, discord_id, token):
    username = username_from_discord_id(discord_id)
    return grant_badge_by_username(badge_id, username, token)
