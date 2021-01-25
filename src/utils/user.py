import functools
import operator
from os import getenv

import discord
from discord import Color
from emoji import get_emoji_regexp


def get_emoji(self, em):
    em_regex = get_emoji_regexp()
    em_split_emoji = em_regex.split(em)
    em_split_whitespace = [substr.split() for substr in em_split_emoji]
    em_split = functools.reduce(operator.concat, em_split_whitespace)
    return [x for x in em_split if em_regex.match(x)]


async def update_username(bot, userInfo):
    guild = bot.get_guild(int(getenv("GUILD_ID", 689213562740277361)))
    user = (guild.get_member(int(userInfo["discordId"])))
    if not userInfo["badges"]:
        await user.edit(nick=f"{userInfo['name']}")
        return
    displayed_badges = [badge["details"]["emoji"] for badge in
                        [badge_data for badge_data in userInfo["badges"] if badge_data["displayed"] is True]]
    print(displayed_badges)
    await user.edit(nick=f"{userInfo['name']} {''.join(displayed_badges)}")


async def update_roles(bot, userInfo):
    role_linked = int(getenv('ROLE_LINKED'))
    pronoun_role_color = int(
        getenv('PRONOUN_ROLE_COLOR', '10070710'))
    alert_channel = int(getenv('ALERT_CHANNEL', 689216590297694211))
    auth0_roles = getenv('AUTH0_ROLES')

    guild = bot.get_guild(int(getenv("GUILD_ID", 689213562740277361)))
    user = (guild.get_member(int(userInfo["discordId"])))
    all_pronoun_roles = [role for role in guild.roles if role.color.value == pronoun_role_color]
    auth0_role_map = dict(r.split(':') for r in auth0_roles.split(';'))
    desired_roles = [guild.get_role(role_linked)]
    remove_roles = []
    auth0_desired_roles = [auth0_role_map[r['id']]
                           for r in userInfo['roles']
                           if r['id'] in auth0_role_map]
    desired_roles.extend([guild.get_role(int(r))
                          for r in auth0_desired_roles])
    remove_roles.extend([guild.get_role(int(r))
                         for r in auth0_role_map.values()
                         if r not in auth0_desired_roles])

    if userInfo['pronoun'] != 'unspecified':
        desired_pronoun_role = next(
            (role for role in all_pronoun_roles if role.name ==
             userInfo['pronoun']),
            None
        )
        if desired_pronoun_role is None:
            desired_pronoun_role = await guild.create_role(
                name=userInfo['pronoun'],
                color=Color(pronoun_role_color)
            )
            m = await guild.get_channel(alert_channel).send(
                f'''Alert: New pronoun role created, {desired_pronoun_role.mention} \
    for user <@{userInfo["discordId"]}>
    Please react with ✅ to approve, 🚫 to delete the role, 🔨 to delete the role and ban the user''')
            await m.add_reaction('✅')
            await m.add_reaction('🚫')
            await m.add_reaction('🔨')

        for r in all_pronoun_roles:
            if r in user.roles and r != desired_pronoun_role:
                remove_roles.append(r)
        desired_roles.append(desired_pronoun_role)

    await user.remove_roles(*remove_roles)
    await user.add_roles(*desired_roles)
