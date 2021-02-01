
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.websockets import WebsocketsTransport
import time
from jwt import encode
from os import getenv

class GQLService:
    @staticmethod
    def make_token():
        secret = getenv("GQL_ACCOUNT_SECRET")
        message = {
            "exp": int(time.time()) + (60*60*24*5),
            "scopes": "read:users",
        }
        return encode(message, secret, algorithm='HS256')

    @staticmethod
    def make_query(query, with_fragments=True):
        if not with_fragments:
            return gql(query)

        fragments = """
            fragment UserSubscriptionInformation on AccountSubscriptionUser {
              id
              username
              picture
              name
              discordId
              pronoun
              roles {
                id
                name
              }
              badges {
                id
                displayed
                order
                details {
                  emoji
                }
              }
              bio
            }
                """
        return gql(query + "\n" + fragments)

    @staticmethod
    async def query_http(query, variable_values=None, with_fragments=True):
        transport = AIOHTTPTransport(
            url="https://graph.codeday.org/",
            headers={"authorization": f"Bearer {GQLService.make_token()}"})
        client = Client(transport=transport, fetch_schema_from_transport=True)
        return await client.execute_async(GQLService.make_query(query, with_fragments=with_fragments), variable_values=variable_values)

    @staticmethod
    async def subscribe_ws(query, variable_values=None, with_fragments=True):
        token = GQLService.make_token()
        transport = WebsocketsTransport(
            url='ws://graph.codeday.org/subscriptions',
            init_payload={'authorization': 'Bearer ' + token}
        )
        session = Client(transport=transport, fetch_schema_from_transport=True)
        async for result in session.subscribe_async(GQLService.make_query(query, with_fragments=with_fragments),
                                                    variable_values=variable_values):
            yield result

    @staticmethod
    async def get_user_from_discord_id(discord_id):
        query = """
            query getUserFromDiscordId($id: String!) {
              account {
                getUser(where: {discordId: $id}, fresh: true) {
                  id
                  username
                  picture
                  name
                  discordId
                  pronoun
                  roles {
                    id
                    name
                  }
                  badges {
                    id
                    displayed
                    order
                    details {
                      emoji
                    }
                  }
                  bio
                }
              }
            }
        """
        params = {"id": str(discord_id)}
        result = await GQLService.query_http(query, variable_values=params, with_fragments=False)
        return result["account"]["getUser"]

    @staticmethod
    async def get_user_from_username(username):
        query = """
            query getUserFromUsername($username: String!) {
              account {
                getUser(where: {username: $username}, fresh: true) {
                  id
                  username
                  picture
                  name
                  discordId
                  pronoun
                  roles {
                    id
                    name
                  }
                  badges {
                    id
                    displayed
                    order
                    details {
                      emoji
                    }
                  }
                  bio
                }
              }
            }
        """
        params = {"username": str(username)}
        result = await GQLService.query_http(query, variable_values=params)
        return result["account"]["getUser"]

    @staticmethod
    async def user_update_listener():
        query = """
            subscription {
              userUpdate {
                  ...UserSubscriptionInformation
              }
            }
        """

        async for result in GQLService.subscribe_ws(query):
            yield result["userUpdate"]

    @staticmethod
    async def user_badge_update_listener():
        query = """
            subscription {
              userBadgeUpdate {
                  type
                  user {...UserSubscriptionInformation}
                  badge {
                  id
                  details {
                    name
                    emoji
                    earnMessage
                  }
                }
              }
            }
        """

        async for result in GQLService.subscribe_ws(query):
            yield result["userBadgeUpdate"]

    @staticmethod
    async def user_displayed_badges_update_listener():
        query = """
            subscription {
              userDisplayedBadgesUpdate {
                  ...UserSubscriptionInformation
              }
            }
        """

        async for result in GQLService.subscribe_ws(query):
            yield result["userDisplayedBadgesUpdate"]

    @staticmethod
    async def user_profile_picture_update_listener():
        query = """
            subscription {
              userProfilePictureUpdate {
                  ...UserSubscriptionInformation
              }
            }
        """

        async for result in GQLService.subscribe_ws(query):
            yield result["userProfilePictureUpdate"]

    @staticmethod
    async def user_role_update_listener():
        query = """
                subscription {
                  userRoleUpdate {
                      ...UserSubscriptionInformation
                  }
                }
            """

        async for result in GQLService.subscribe_ws(query):
            yield result["userRoleUpdate"]