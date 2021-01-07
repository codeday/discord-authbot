import asyncio
import functools
import logging
import operator
import os
import re

import discord
from auth0.v3.management import Auth0
from discord import Color
from discord.ext import commands
from emoji import get_emoji_regexp
from raygun4py import raygunprovider

from utils import badge
from utils.auth0 import lookup_user, add_badge, get_auth0_token, add_roles
from utils.person import id_from_mention

logging.basicConfig(level=logging.INFO)


class AuthCommands(commands.Cog, name="Authentication"):
    """A cog where all the authentication commands live"""

    def __init__(self, bot):
        self.bot = bot
        self.role_linked = int(os.getenv('ROLE_LINKED'))
        self.pronoun_role_color = int(
            os.getenv('PRONOUN_ROLE_COLOR', '10070710'))
        self.alert_channel = int(os.getenv('ALERT_CHANNEL'))
        self.auth0_roles = os.getenv('AUTH0_ROLES')

    def get_emoji(self, em):
        em_regex = get_emoji_regexp()
        em_split_emoji = em_regex.split(em)
        em_split_whitespace = [substr.split() for substr in em_split_emoji]
        em_split = functools.reduce(operator.concat, em_split_whitespace)
        return [x for x in em_split if em_regex.match(x)]

    @commands.command(name='account', hidden=True)
    @commands.has_any_role('Employee')
    async def check_clear(self, ctx, user):
        """Lookup a discord users CodeDay account"""
        user = id_from_mention(user)
        results = lookup_user(user)
        if (len(results) == 0):
            await ctx.send('Not linked')
        else:
            await ctx.send(
                f"[{results[0]['username']}](https://manage.auth0.com/dashboard/us/srnd/users/{results[0]['user_id']})")

    @commands.command(name='add_badge', hidden=True)
    @commands.has_any_role('Employee')
    async def award_badge(self, ctx, user, emoji, expiresUTC, title='Badge', description='Badge'):
        user = id_from_mention(user)
        add_badge(user, emoji, expiresUTC, title, description)
        await self.update(ctx, user)

    @commands.command(name='update')
    async def update(self, ctx: commands.context.Context, user):
        """Updates a discord user"""
        if type(user) != int:
            user = id_from_mention(user)
        results = lookup_user(user)
        if len(results) == 1:
            account = results[0]
            user = ctx.guild.get_member(
                int(account['user_metadata']['discord_id']))
            if user:  # ensure user is in server
                debug = await self.update_user(ctx, account, user)
                # await ctx.channel.send(debug)
            await ctx.message.add_reaction('👌')
        elif len(results) == 0:
            await ctx.send('''No CodeDay account is linked to that user!''')
        else:
            await ctx.send(f'''More than one CodeDay account is linked to that user, this shouldn't have happened! 
            Please investigate the following users in auth0: {[account["user_id"] for account in results]}
            cc <@352212467033833475>''')

    @commands.command(name='update_all')
    async def update_all(self, ctx: commands.context.Context):
        token = get_auth0_token(domain=os.getenv('AUTH_DOMAIN'))
        mgmt = Auth0(domain=os.getenv('AUTH_DOMAIN'), token=token)
        idx = 0
        updated_count = 0
        total = mgmt.users.list(q='user_metadata.discord_id=*')['total']
        status_message = await ctx.send(f'Found {total} users to update')
        while updated_count < total:
            results = mgmt.users.list(q='user_metadata.discord_id=*', page=idx)
            users = add_roles(mgmt, results['users'])
            start = results['start']
            total = results['total']  # Just in case of created/deleted accounts during execution
            await status_message.edit(content=f'Updating all users: {start}/{total}')
            for user in users:
                updated_count += 1
                try:
                    await self.update_user(ctx,
                                           user,
                                           ctx.guild.get_member(int(user['user_metadata']['discord_id'])))
                except:
                    cl = raygunprovider.RaygunSender(os.getenv("RAYGUN_TOKEN"))
                    cl.send_exception()
            idx += 1
        await status_message.edit(content=f'update_all complete! {updated_count} users updated!')
        await ctx.message.add_reaction('👌')

    def de_emojify(self, text):
        regrex_pattern = re.compile(pattern="["
                                            u"\U0001F600-\U0001F64F"  # emoticons
                                            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                            u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                            "]+", flags=re.UNICODE)
        return regrex_pattern.sub(r'', text).replace("✔", "")

    async def update_user(self, ctx: commands.context.Context, account, user: discord.Member):
        # old_badges = self.get_emoji(user.nick)

        # Calculate initial information:
        all_pronoun_roles = [
            role for role in ctx.guild.roles if role.color.value == self.pronoun_role_color]
        auth0_role_map = dict(r.split(':')
                              for r in self.auth0_roles.split(';'))

        # Calculate desired nickname:
        desired_nick = f"{account['given_name']} {account['family_name'][0].upper()}"
        if 'display_name_format' in account['user_metadata']:
            desired_nick = account['name']
        elif 'volunteer' in account['user_metadata']:
            desired_nick = f"{account['given_name']} {account['family_name']}"
        desired_nick += ' '  # add spacer between name and badge
        desired_nick = self.de_emojify(desired_nick)

        # new_badges = []
        for b in badge.get_badges_by_discord_id(account['user_metadata']['discord_id']):
            if b is not None:
                if 'emoji' in b['details']:
                    desired_nick += b['details']['emoji']
        #         if (not(b['details']['emoji'] in old_badges) and 'earnMessage' in b['details']
        #                 and len(self.get_emoji(b['details']['emoji'])) > 0):
        #             new_badges.append(b['details']['earnMessage'])

        desired_nick = desired_nick.strip()

        # Calculate desired roles:
        desired_roles = [ctx.guild.get_role(self.role_linked)]
        remove_roles = []

        # - Add roles for auth0 roles
        auth0_desired_roles = [auth0_role_map[r['id']]
                               for r in account['roles']
                               if r['id'] in auth0_role_map]
        desired_roles.extend([ctx.guild.get_role(int(r))
                              for r in auth0_desired_roles])
        remove_roles.extend([ctx.guild.get_role(int(r))
                             for r in auth0_role_map.values()
                             if r not in auth0_desired_roles])

        # -- Add pronoun role
        if account['user_metadata']['pronoun'] != 'unspecified':
            desired_pronoun_role = next(
                (role for role in all_pronoun_roles if role.name ==
                 account['user_metadata']['pronoun']),
                None
            )
            if desired_pronoun_role is None:
                desired_pronoun_role = await ctx.guild.create_role(
                    name=account['user_metadata']['pronoun'],
                    color=Color(self.pronoun_role_color)
                )
                m = await ctx.guild.get_channel(self.alert_channel).send(
                    f'''Alert: New pronoun role created, {desired_pronoun_role.mention} \
for user <@{account["user_metadata"]["discord_id"]}>
Please react with ✅ to approve, 🚫 to delete the role, 🔨 to delete the role and ban the user''')
                await m.add_reaction('✅')
                await m.add_reaction('🚫')
                await m.add_reaction('🔨')

            for r in all_pronoun_roles:
                if r in user.roles and r != desired_pronoun_role:
                    remove_roles.append(r)
            desired_roles.append(desired_pronoun_role)
        try:
            await user.edit(nick=desired_nick)
        except discord.Forbidden:
            if user.nick != desired_nick:
                if user.dm_channel is None:
                    await user.create_dm()
                await user.dm_channel.send(f'''
                Hi there! I was trying to update your nickname, but it looks like you outrank me 😢
Would you mind setting your nickname to the following?
`{desired_nick}`''')
        await user.remove_roles(*remove_roles)
        await user.add_roles(*desired_roles)

        #        for new_badge_msg in new_badges:
        #            await user.send(new_badge_msg)

        return f"Nickname: {desired_nick}\nAdd roles: {[n.name for n in desired_roles]}\nRemove roles: {[n.name for n in remove_roles]}"

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if (
                payload.channel_id == self.alert_channel
                and payload.user_id != self.bot.user.id
        ):
            msg = await self.bot.get_guild(payload.guild_id).get_channel(payload.channel_id).fetch_message(
                payload.message_id)
            if (
                    msg.author.id == self.bot.user.id
                    and msg.content.startswith('Alert: New pronoun role created,')
            ):
                if payload.emoji.name == '✅':
                    await (await msg.channel.send('Ok, the role has been approved')).delete(delay=5)
                    await msg.delete(delay=5)
                elif payload.emoji.name == '🚫':
                    if len(msg.raw_role_mentions) == 1:
                        role = self.bot.get_guild(payload.guild_id).get_role(
                            msg.raw_role_mentions[0])
                        msgs = [
                            await msg.channel.send(f'Are you sure you would like to delete the role {role.mention}?')]
                        await msgs[0].add_reaction('🚫')
                        await msgs[0].add_reaction('✅')

                        def check(reaction, user):
                            return user.id == payload.user_id and (
                                str(reaction.emoji) == '🚫' or str(reaction.emoji) == '✅')

                        try:
                            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                        except asyncio.TimeoutError:
                            await msgs[0].delete()
                        else:
                            if str(reaction.emoji) == '🚫':
                                msgs.append(await msg.channel.send(f'Ok, I will not delete the role'))
                            elif str(reaction.emoji) == '✅':
                                await role.delete(reason=f'Pronoun role deletion triggered by <@{payload.user_id}>')
                                await msg.edit(content=msg.content.replace('Alert: ', '', 1))
                                await msg.channel.send('Ok, I have deleted the role.')
                        for msg in msgs:
                            await msg.delete(delay=5)
                    else:
                        await msg.channel.send('''There was an error with the amount of roles mentioned in the message.
                                Please complete required actions manually''')
                elif payload.emoji.name == '🔨':
                    if len(msg.raw_role_mentions) == 1:
                        role = self.bot.get_guild(payload.guild_id).get_role(
                            msg.raw_role_mentions[0])
                        if len(msg.mentions) == 1:
                            user = msg.mentions[0]
                            msgs = [
                                await msg.channel.send(f'Are you sure you would like to delete the role {role.mention}, \
and ban the user <@{user.id}>?')]
                            await msgs[0].add_reaction('🚫')
                            await msgs[0].add_reaction('✅')

                            def check(reaction, u):
                                return u.id == payload.user_id and (
                                    str(reaction.emoji) == '🚫' or str(reaction.emoji) == '✅')

                            try:
                                reaction, u = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                            except asyncio.TimeoutError:
                                await msgs[0].delete()
                            else:
                                if str(reaction.emoji) == '🚫':
                                    msgs.append(
                                        await msg.channel.send(f'Ok, I will not delete the role or ban the user.'))
                                elif str(reaction.emoji) == '✅':
                                    await role.delete(reason=f'Pronoun role deletion requested by <@{payload.user_id}>')
                                    await user.ban(reason=f'Pronoun role ban requested by <@{payload.user_id}>')
                                    await msg.edit(content=msg.content.replace('Alert: ', '', 1))
                                    await msg.channel.send('Ok, I have deleted the role and banned the user')
                            for msg in msgs:
                                await msg.delete(delay=5)
                        else:
                            await msg.channel.send('''There was an error with the amount of users mentioned in the message.
Please complete required actions manually''')
                    else:
                        await msg.channel.send('''There was an error with the amount of roles mentioned in the message.
                        Please complete required actions manually''')


def setup(bot):
    bot.add_cog(AuthCommands(bot))
