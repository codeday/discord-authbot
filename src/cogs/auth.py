import json
import os

from discord.ext import commands

from utils.auth0 import lookup_user
from utils.person import id_from_mention


class AuthCommands(commands.Cog, name="Authentication"):
    """A cog where all the authentication commands live"""

    def __init__(self, bot):
        self.bot = bot
        self.role_student = int(os.getenv('ROLE_STUDENT'))
        self.role_volunteer = int(os.getenv('ROLE_VOLUNTEER'))

    @commands.command(name='check-clear', hidden=True)
    @commands.has_any_role('Global Staff')
    async def check_clear(self, ctx, user):
        """Lookup a discord users clear account"""
        user = id_from_mention(user)
        results = lookup_user(user)
        await ctx.send(json.dumps(results, indent=2, sort_keys=True))

    @commands.command(name='update')
    async def update_user(self, ctx, user):
        """Updates a discord user"""
        user = id_from_mention(user)
        results = lookup_user(user)
        if len(results) == 1:
            account = results[0]
            user = ctx.guild.get_member(int(account['user_metadata']['discord_id']))
            if user:  # ensure user is in server
                await user.edit(nick=account['name'])
                if account['user_metadata']['accept_tos']:
                    await user.add_roles(ctx.guild.get_role(self.role_student))
                if account['user_metadata']['volunteer']:
                    await user.add_roles(ctx.guild.get_role(self.role_volunteer))
            await ctx.message.add_reaction('👌')
        elif len(results) == 0:
            await ctx.send('''No CodeDay account is linked to that user!''')
        else:
            await ctx.send('''More than one CodeDay account is linked to your discord.
This should not be possible, please contact an admin''')


def setup(bot):
    bot.add_cog(AuthCommands(bot))
