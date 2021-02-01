import logging
import sys
import traceback
from os import getenv

import discord
from raygun4py import raygunprovider

from services.gqlservice import GQLService
from utils.SuperBot import SuperBot
from utils.user import update_user

logging.basicConfig(level=logging.INFO)
welcome_channel_id = int(getenv('WELCOME_CHANNEL', 756583187307823224))


def handle_exception(exc_type, exc_value, exc_traceback):
    cl = raygunprovider.RaygunSender(getenv("RAYGUN_TOKEN"))
    cl.send_exception(exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception
BOT_TOKEN = getenv('BOT_TOKEN')
intents = discord.Intents(messages=True, guilds=True, members=True, reactions=True)
bot = SuperBot(command_prefix='a~', intents=intents)

initial_cogs = ['cogs.auth', 'cogs.listen']
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
    userInfo = await GQLService.get_user_from_discord_id(member.id)
    await update_user(bot, userInfo)
    if not userInfo(member.id):
        if member.dm_channel is None:
            await member.create_dm()
        await member.dm_channel.send(
            '''Hello, human! Welcome to the CodeDay Discord server!
To gain full access, you MUST link your Discord account to a CodeDay account using the link below:
https://discord0.codeday.org

We are glad you are joining our community! If you have any questions or need to speak with a staff member, reply to this message and we will be in touch shortly.
''')
    welcome_channel = bot.get_channel(welcome_channel_id)
    await welcome_channel.send('👋')


@bot.event
async def on_message(message):
    if type(message.channel) == discord.channel.DMChannel and message.author is not message.channel.me:
        welcome_channel = bot.get_channel(welcome_channel_id)
        await welcome_channel.send(f'''<@{message.author.id}> just sent me a message:
----
{message.content}
----
<@&756583313006788699>''')
        await message.channel.send(
            "I've forwarded your message to CodeDay staff, they will respond as fast as possible!")
    else:
        await bot.process_commands(message)

bot.run(BOT_TOKEN, bot=True, reconnect=True)
