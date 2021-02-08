import logging
from os import getenv

from discord.ext import commands

from services.gqlservice import GQLService
from utils.subscriptions import subscribe
from utils.user import update_username, update_roles, update_user


class ListenCog(commands.Cog, name="Listen"):
    """Listen to showcase api for team updates"""

    def __init__(self, bot):
        self.bot = bot
        self.guild_id = int(getenv("GUILD_ID", 689213562740277361))
        self.auth_channel = int(getenv('AUTH_CHANNEL', 697888673664073808))

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.guild_id)
        self.on_user_update.start(self)
        logging.info(f'Started user update listener')
        self.on_user_badge_update.start(self)
        logging.info(f'Started badge update listener')
        self.on_user_displayed_badges_update.start(self)
        logging.info(f'Started displayed badge update listener')
        self.on_user_role_update.start(self)
        logging.info(f'Started role update listener')

    def cog_unload(self):
        self.on_user_update.stop()
        self.on_user_badge_update.stop()
        self.on_user_displayed_badges_update.stop()
        self.on_user_role_update.stop()

    @subscribe(GQLService.user_update_listener)
    async def on_user_update(self, user_info):
        await update_user(self.bot, user_info)
        if user_info:
            await self.guild.get_channel(self.auth_channel).send(f"<@{user_info['discordId']}> updated.")

    @subscribe(GQLService.user_badge_update_listener)
    async def on_user_badge_update(self, data):
        guild = self.bot.get_guild(self.guild_id)
        if data["type"] == "grant":
            user = (guild.get_member(int(data["user"]["discordId"])))
            dm_channel = await user.create_dm()
            await dm_channel.send(data["badge"]["details"]["earnMessage"])
        await update_user(self.bot, data["user"])

    @subscribe(GQLService.user_displayed_badges_update_listener)
    async def on_user_displayed_badges_update(self, user_info):
        await update_username(self.bot, user_info)
        if user_info:
            await self.guild.get_channel(self.auth_channel).send(f"<@{user_info['discordId']}> badges updated.")

    @subscribe(GQLService.user_role_update_listener)
    async def on_user_role_update(self, user_info):
        await update_roles(self.bot, user_info)
        if user_info:
            await self.guild.get_channel(self.auth_channel).send(f"<@{user_info['discordId']}> roles updated.")


def setup(bot):
    bot.add_cog(ListenCog(bot))
