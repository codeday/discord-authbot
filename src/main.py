import logging
import traceback
from os import getenv

from discord.ext import commands

from utils.auth0 import lookup_user

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = getenv('BOT_TOKEN')
bot = commands.Bot(command_prefix='a~')

initial_cogs = ['cogs.auth']
for cog in initial_cogs:
    try:
        bot.load_extension(cog)
        logging.info(f'Successfully loaded extension {cog}')
    except Exception as e:
        logging.exception(
            f'Failed to load extension {cog}.', exc_info=traceback.format_exc())


@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))


@bot.event
async def on_member_join(member):
    if not lookup_user(member.id):
        if member.dm_channel is None:
            await member.create_dm()
        await member.dm_channel.send(
            '''Hello, Human! Welcome to the CodeDay discord server!
Please authenticate with your CodeDay account by clicking the following link:
https://discord0.codeday.xyz
'''
        )


bot.run(BOT_TOKEN, bot=True, reconnect=True)
