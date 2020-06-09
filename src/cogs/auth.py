import asyncio
import json
import os

import discord
from discord import Color
from discord.ext import commands

from utils.auth0 import lookup_user
from utils.person import id_from_mention


class AuthCommands(commands.Cog, name="Authentication"):
    """A cog where all the authentication commands live"""

    def __init__(self, bot):
        self.bot = bot
        self.role_linked = int(os.getenv('ROLE_LINKED'))
        self.pronoun_role_color = int(
            os.getenv('PRONOUN_ROLE_COLOR', '10070710'))
        self.alert_channel = int(os.getenv('ALERT_CHANNEL'))
        self.auth0_roles = os.getenv('AUTH0_ROLES')

    @commands.command(name='account', hidden=True)
    @commands.has_any_role('Global Staff')
    async def check_clear(self, ctx, user):
        """Lookup a discord users CodeDay account"""
        user = id_from_mention(user)
        results = lookup_user(user)
        if (len(results) == 0):
            await ctx.send('Not linked')
        else:
            await ctx.send(f"[{results[0]['username']}](https://manage.auth0.com/dashboard/us/srnd/users/{results[0]['user_id']})")

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
                await ctx.channel.send(debug)
            await ctx.message.add_reaction('👌')
        elif len(results) == 0:
            await ctx.send('''No CodeDay account is linked to that user!''')
        else:
            pass

    @commands.command(name='update_all')
    async def update_all(self, ctx: commands.context.Context):
        await ctx.message.add_reaction('⌛')
        print(f'updating {len(ctx.guild.members)} users')
        for user in ctx.guild.members:
            results = lookup_user(user.id)
            if len(results) == 1:
                account = results[0]
                try:
                    await self.update_user(ctx, account, user)
                except Exception as e:
                    print(e)
        await ctx.message.clear_reaction('⌛')
        await ctx.message.add_reaction('👌')

    async def update_user(self, ctx: commands.context.Context, account, user):
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

        await user.edit(nick=desired_nick)
        await user.remove_roles(*remove_roles)
        await user.add_roles(*desired_roles)

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
