import asyncio
import logging
from os import getenv

import discord
from discord.ext import commands
from raygun4py import raygunprovider

from services.gqlservice import GQLService
from utils.user import update_user


class AuthCommands(commands.Cog, name="Authentication"):
    """A cog where all the authentication commands live"""

    def __init__(self, bot):
        self.bot = bot
        self.alert_channel = int(getenv('ALERT_CHANNEL', 689216590297694211))

    @commands.command(name='updatee')
    async def updatee(self, ctx: commands.context.Context, member: discord.Member):
        user_info = await GQLService.get_user_from_discord_id(member.id)
        await update_user(self.bot, user_info)
        await ctx.message.add_reaction('👌')

    @commands.command(name='update_alll')
    async def update_alll(self, ctx: commands.context.Context, printDebugMessages: str = ""):
        debug = False
        if printDebugMessages.lower() == "true":
            debug = True
        await ctx.message.add_reaction('⌛')
        # await self.bot.request_offline_members(ctx.guild)
        await ctx.guild.chunk()
        member_count = len(ctx.guild.members)
        status_message = await ctx.send(f'Found {member_count} users to update')
        await status_message.edit(
            content=f'Updating all users: {0}/{member_count} (this message will update every 3 users)')
        updated_count = 0
        for index, member in enumerate(ctx.guild.members):
            user_info = await GQLService.get_user_from_discord_id(member.id)
            # update status message every 3 members to help rate limiting
            if index % 3 == 0:
                await status_message.edit(
                    content=f'Updating all users: {index + 1}/{member_count} (this message will update every 3 users)')
            if user_info:
                await update_user(self.bot, user_info)
                if debug:
                    logging.info(f"updated user {user_info['username']}")
            updated_count += 1
        await status_message.edit(content=f'update_all complete! {updated_count} users updated!')
        await ctx.message.clear_reaction('⌛')
        await ctx.message.add_reaction('👌')

    @commands.Cog.listener("on_raw_reaction_add")
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
