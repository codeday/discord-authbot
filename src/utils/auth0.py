import os
from datetime import datetime, timedelta
from auth0.v3.authentication import GetToken
from auth0.v3.management import Auth0

cached_token = None


def get_auth0_token(domain=os.getenv('AUTH_DOMAIN'),
                    client_id=os.getenv('AUTH_CLIENT_ID'),
                    client_secret=os.getenv('AUTH_CLIENT_SECRET')):
    global cached_token
    cached_token
    if cached_token == None or cached_token['expires_at'] <= datetime.now():
        get_token = GetToken(domain)
        cached_token = get_token.client_credentials(client_id,
                                                    client_secret,
                                                    'https://{}/api/v2/'.format(domain))
        cached_token['expires_at'] = datetime.now() \
            + timedelta(seconds=(cached_token['expires_in'] - 60))
    return cached_token['access_token']


def lookup_user(user: int, domain=os.getenv('AUTH_DOMAIN'),):
    token = get_auth0_token(domain=domain)
    mgmt = Auth0(domain, token)
    return mgmt.users.list(q=f'user_metadata.discord_id:"{str(user)}"')['users']


def lookup_all(domain=os.getenv('AUTH_DOMAIN')):
    token = get_auth0_token(domain=domain)
    mgmt = Auth0(domain, token)
    return mgmt.users.list(q='user_metadata.discord_id=*')['users']
