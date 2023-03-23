from os import getenv

import discord
from discord import Color
import random

async def update_username(bot, user_info):
    if user_info and "discordId" in user_info.keys():
        guild = bot.get_guild(int(getenv("GUILD_ID", 689213562740277361)))
        user = (guild.get_member(int(user_info["discordId"])))
        # fish = ['🐟','🎣','🐠','🐡','🍣','🦑','🦐','🦈','🐬','🐳','🐋','🦞','🦀']
        # a relic of times past, kept for sentimentality
        desired_nick = user_info['name']
        if user_info["badges"]:
            if 'displayedBadges' in user_info:
                displayed_badges = [badge["details"]["emoji"] for badge in user_info["displayedBadges"]]
            else:
                displayed_badges = [badge["details"]["emoji"] for badge in
                                    [badge_data for badge_data in user_info["badges"] if
                                     badge_data["displayed"] is True]]
            desired_nick = f"{user_info['name']} {''.join(displayed_badges)}"
        try:
            if not user.nick == desired_nick:
                try:
                    await user.edit(nick=desired_nick)
                except discord.HTTPException:
                    desired_nick = desired_nick[:32]
                    await user.edit(nick=desired_nick)
                    if user.dm_channel is None:
                        await user.create_dm()
                    await user.dm_channel.send(
                        f'''Hi there! I was trying to update your nickname, but it looks like your name is over 32 characters (Discord limitation).
I have cut it down to 32 characters which looks like this.
> `{desired_nick}`

Try changing your name format or abbreviate your name at https://account.codeday.org/ if you dislike this.
''')
        except discord.Forbidden:
            if user.nick != desired_nick:
                try:
                    if user.dm_channel is None:
                        await user.create_dm()
                    await user.dm_channel.send(f'''
                    Hi there! I was trying to update your nickname, but it looks like you outrank me 😢
    Would you mind setting your nickname to the following?
    > `{desired_nick}`''')
                except discord.Forbidden:
                    pass
        return f"Nickname: {desired_nick}"


async def update_roles(bot, user_info):
    if user_info and "discordId" in user_info.keys():
        role_linked = int(getenv('ROLE_LINKED', 714577449408659567))
        pronoun_role_color = int(
            getenv('PRONOUN_ROLE_COLOR', '10070710'))
        alert_channel = int(getenv('ALERT_CHANNEL', 689216590297694211))
        auth0_roles = 'rol_EVSfhWpeWSyLBXoy:719942215912259636;rol_llN0357VXrEoIxoj:712062910897061979;rol_QNjEAkl1VA7WM3Dq:689215241996730417;rol_Z10C6Hfr4bfqYa4r:696842277234147369;rol_FQQIo5K2aJWdXBmF:693537313841610843;rol_YazTjd70s8kqJ3Y2:689217196479610940;rol_bs8jL5GZlfGb8u1u:689587112420311113;rol_0ycGdcN2hV3K7Rx2:808759328659210251;rol_yCjTFASCHeLch9ke:808759422448173109;rol_cU5c8wlFVbSh6I2w:821204803719004241;rol_txwNqj6PbUiC6tTl:847218249573072928;rol_P81H9q32JJj42vYU:851913592013193237;rol_n8WLMY9GfIupEHkY:1085353238821339217;rol_TDhVLYbjhE273TtY:902651117022875648;rol_uymT3SApJRUEP5Pn:906584505022816317;rol_yxlnIt5J97UvMdzY:908392924461539338;rol_TPBCpOZ81TMuQJ3I:908392756563554314;rol_6r3pPwtQKZwK3mj3:908392975548166164;rol_BtKPT7sRB4ztcvtd:908392949677695018;rol_Hc6xXfPtu6jU3rVz:908393001011798016;rol_VQFms05O5ozk6dL6:908776991266857021;rol_cU5c8wlFVbSh6I2w:1088572114631655494'

        guild = bot.get_guild(int(getenv("GUILD_ID", 689213562740277361)))
        user = (guild.get_member(int(user_info["discordId"])))
        all_pronoun_roles = [role for role in guild.roles if role.color.value == pronoun_role_color]
        auth0_role_map = dict(r.split(':') for r in auth0_roles.split(';'))
        desired_roles = [guild.get_role(role_linked)]
        remove_roles = []
        auth0_desired_roles = [auth0_role_map[r['id']]
                               for r in user_info['roles']
                               if r['id'] in auth0_role_map]
        desired_roles.extend([guild.get_role(int(r))
                              for r in auth0_desired_roles])
        remove_roles.extend([guild.get_role(int(r))
                             for r in auth0_role_map.values()
                             if r not in auth0_desired_roles])

        if user_info['pronoun'] != 'unspecified':
            desired_pronoun_role = next(
                (role for role in all_pronoun_roles if role.name ==
                 user_info['pronoun']),
                None
            )
            if desired_pronoun_role is None:
                desired_pronoun_role = await guild.create_role(
                    name=user_info['pronoun'],
                    color=Color(pronoun_role_color)
                )
                m = await guild.get_channel(alert_channel).send(
                    f'''Alert: New pronoun role created, {desired_pronoun_role.mention} \
        for user <@{user_info["discordId"]}>
        Please react with ✅ to approve, 🚫 to delete the role, 🔨 to delete the role and ban the user''')
                await m.add_reaction('✅')
                await m.add_reaction('🚫')
                await m.add_reaction('🔨')

            for r in all_pronoun_roles:
                if r in user.roles and r != desired_pronoun_role:
                    remove_roles.append(r)
            desired_roles.append(desired_pronoun_role)

        for i in desired_roles:
            if i not in user.roles:
                await user.add_roles(*[role for role in desired_roles if role])
                break
        for i in user.roles:
            if i in remove_roles:
                await user.remove_roles(*[role for role in remove_roles if role])
                break
        # return f"Add roles: {[n.name for n in desired_roles]}\nRemove roles: {[n.name for n in remove_roles]}"
        return ""


async def unlink_user(bot, discordId):
    guild = bot.get_guild(int(getenv("GUILD_ID", 689213562740277361)))
    member = guild.get_member(int(discordId))
    if member:
        await member.edit(nick=member.name, roles=[])
        return True
    return False


async def update_user(bot, user):
    await update_username(bot, user)
    await update_roles(bot, user)
