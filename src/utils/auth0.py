import os

from auth0.v3.management import Auth0
from auth0.v3.authentication import GetToken


def lookup_user(user: int,
                domain=os.getenv('AUTH_DOMAIN'),
                client_id=os.getenv('AUTH_CLIENT_ID'),
                client_secret=os.getenv('AUTH_CLIENT_SECRET')):
    get_token = GetToken(domain)
    token = get_token.client_credentials(client_id,
                                         client_secret,
                                         'https://{}/api/v2/'.format(domain))['access_token']
    mgmt = Auth0(domain, token)
    return mgmt.users.list(q=f'user_metadata.discord_id:"{str(user)}"')['users']
