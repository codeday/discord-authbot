from os import getenv
import logging
from discord.ext import commands
import traceback

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = getenv('BOT_TOKEN')
bot = commands.Bot(command_prefix='a!')

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

bot.run(BOT_TOKEN, bot=True, reconnect=True)
