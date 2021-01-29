# discord-authbot
Linking CodeDay accounts to discord accounts

###Environmental Variables:
* Required
  * AUTH0_ROLES (role map format "<auth0_role_id1>:<discord_role_id1>;<auth0_role_id2>:<discord_role_id2>...")
  * GQL_ACCOUNT_SECRET (gql account secret)
  * RAYGUN_TOKEN (required for raygun error handling)
* Optional (mostly for development)
  * ALERT_CHANNEL (#moderation channel id)
  * AUTH_CHANNEL (#authentication channel id)
  * ROLE_LINKED ("Community Member" role id)
  * WELCOME_CHANNEL_ID (#welcome-committee channel id)
  * GUILD_ID (discord server id)
  * GRAPHQL_URL (CodeDay GraphQL url)
