from os import getenv

import discord
from discord.ext import commands, tasks

from services.gqlservice import GQLService
from utils.subscriptions import subscribe
from utils.user import update_username, update_roles


class ListenCog(commands.Cog, name="Listen"):
    """Listen to showcase api for team updates"""

    def __init__(self, bot):
        self.bot = bot
        self.guild_id = int(getenv("GUILD_ID", 689213562740277361))

    @commands.Cog.listener()
    async def on_ready(self):
        self.on_user_update.start(self)
        self.on_user_badge_update.start(self)
        self.on_user_displayed_badges_update.start(self)
        self.on_user_role_update.start(self)

    def cog_unload(self):
        self.on_user_update.stop()
        self.on_user_badge_update.stop()
        self.on_user_displayed_badges_update.stop()
        self.on_user_role_update.stop()

    @subscribe(GQLService.user_update_listener)
    async def on_user_update(self, userInfo):
        await update_username(self.bot, userInfo)
        await update_roles(self.bot, userInfo)
        guild = self.bot.get_guild(self.guild_id)
        channel = discord.utils.get(guild.channels, name="subscription-log")
        await channel.send("userUpdate")

    @subscribe(GQLService.user_badge_update_listener)
    async def on_user_badge_update(self, data):
        guild = self.bot.get_guild(self.guild_id)
        if data["type"] == "grant":
            user = (guild.get_member(int(data["user"]["discordId"])))
            dm_channel = await user.create_dm()
            await dm_channel.send(data["badge"]["details"]["earnMessage"])
            # channel = discord.utils.get(guild.channels, name="subscription-log")
            # await channel.send("userBadgeUpdate")

    @subscribe(GQLService.user_displayed_badges_update_listener)
    async def on_user_displayed_badges_update(self, userInfo):
        await update_username(self.bot, userInfo)
        guild = self.bot.get_guild(self.guild_id)
        channel = discord.utils.get(guild.channels, name="subscription-log")
        await channel.send("userDisplayedBadgesUpdate")

    @subscribe(GQLService.user_role_update_listener)
    async def on_user_role_update(self, userInfo):
        guild = self.bot.get_guild(self.guild_id)
        await update_roles(self.bot, userInfo)
        channel = discord.utils.get(guild.channels, name="subscription-log")
        await channel.send("userRoleUpdate")


def setup(bot):
    bot.add_cog(ListenCog(bot))
