import os
from utils.auth0 import lookup_user
from utils.person import id_from_mention


from discord.ext import commands


class AuthCommands(commands.Cog, name="Authentication"):
    """A cog where all the authentication commands live"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='check-clear', hidden=True)
    @commands.has_any_role('Global Staff')
    async def check_clear(self, ctx, user):
        user = id_from_mention(user)
        results = lookup_user(user)
        if len(results) == 1:
            user = results[0]
            await ctx.send(str(user))
        else:
            await ctx.send('')


def setup(bot):
    bot.add_cog(AuthCommands(bot))