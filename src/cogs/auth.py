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
        self.role_student = int(os.getenv('ROLE_STUDENT'))
        self.role_volunteer = int(os.getenv('ROLE_VOLUNTEER'))
        self.pronoun_role_color = int(os.getenv('PRONOUN_ROLE_COLOR', '10070710'))
        self.alert_channel = int(os.getenv('ALERT_CHANNEL'))

    @commands.command(name='check-clear', hidden=True)
    @commands.has_any_role('Global Staff')
    async def check_clear(self, ctx, user):
        """Lookup a discord users clear account"""
        user = id_from_mention(user)
        results = lookup_user(user)
        await ctx.send(json.dumps(results, indent=2, sort_keys=True))

    @commands.command(name='update')
    async def update(self, ctx: commands.context.Context, user):
        """Updates a discord user"""
        if type(user) != int:
            user = id_from_mention(user)
        results = lookup_user(user)
        if len(results) == 1:
            account = results[0]
            user = ctx.guild.get_member(int(account['user_metadata']['discord_id']))
            if user:  # ensure user is in server
                await self.update_user(ctx, account, user)
            await ctx.message.add_reaction('👌')
        elif len(results) == 0:
            await ctx.send('''No CodeDay account is linked to that user!''')
            await ctx.send('''More than one CodeDay account is linked to your discord.
This should not be possible, please contact an admin''')
        else:
            pass

    async def update_user(self, ctx: commands.context.Context, account, user):
        await user.edit(nick=account['name'])
        if account['user_metadata']['accept_tos']:
            await user.add_roles(ctx.guild.get_role(self.role_student))
        if 'volunteer' in account['user_metadata']:
            if account['user_metadata']['volunteer']:
                await user.add_roles(ctx.guild.get_role(self.role_volunteer))
        if account['user_metadata']['pronoun'] != 'unspecified':
            pronoun_roles = [role for role in ctx.guild.roles if role.color.value == self.pronoun_role_color]
            role = next((role for role in pronoun_roles if role.name == account['user_metadata']['pronoun']),
                        None)
            if role is None:
                role = await ctx.guild.create_role(
                    name=account['user_metadata']['pronoun'],
                    color=Color(self.pronoun_role_color)
                )
                m = await ctx.guild.get_channel(self.alert_channel).send(
                    f'''Alert: New pronoun role created, {role.mention} \
for user <@{account["user_metadata"]["discord_id"]}>
Please react with ✅ to approve, 🚫 to delete the role, 🔨 to delete the role and ban the user''')
                await m.add_reaction('✅')
                await m.add_reaction('🚫')
                await m.add_reaction('🔨')
            for r in pronoun_roles:
                if r in user.roles:
                    await user.remove_roles(r)
            await user.add_roles(role)

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
                        role = self.bot.get_guild(payload.guild_id).get_role(msg.raw_role_mentions[0])
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
                        role = self.bot.get_guild(payload.guild_id).get_role(msg.raw_role_mentions[0])
                        if len(msg.mentions) == 1:
                            user = msg.mentions[0]
                            msgs = [
                                await msg.channel.send(f'Are you sure you would like to delete the role {role.mention}, \
and ban the user <@{user.id}>?')]
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
                                    msgs.append(
                                        await msg.channel.send(f'Ok, I will not delete the role or ban the user.'))
                                elif str(reaction.emoji) == '✅':
                                    await role.delete(reason=f'Pronoun role deletion requested by <@{payload.user_id}>')
                                    await user.ban(reason=f'Pronoun role ban requested by <@{payload.user_id}>')
                                    await msg.edit(content=msg.content.replace('Alert: ', '', 0))
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
