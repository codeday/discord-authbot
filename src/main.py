import logging
import sys
import traceback
from os import getenv

import discord
from discord import Color
from raygun4py import raygunprovider

from utils import badge
from utils.SuperBot import SuperBot
from utils.auth0 import lookup_user
from utils.person import id_from_mention, de_emojify

logging.basicConfig(level=logging.INFO)
welcome_channel_id = getenv('WELCOME_CHANNEL_ID', '756583187307823224')


def handle_exception(exc_type, exc_value, exc_traceback):
    cl = raygunprovider.RaygunSender(getenv("RAYGUN_TOKEN"))
    cl.send_exception(exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception
BOT_TOKEN = getenv('BOT_TOKEN')
bot = SuperBot(command_prefix='a~')

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
            '''Hello, human! Welcome to the CodeDay Discord server!
To gain full access, you MUST link your Discord account to a CodeDay account using the link below:
https://discord0.codeday.org

We are glad you are joining our community! If you have any questions or need to speak with a staff member, reply to this message and we will be in touch shortly.
''')
    else:
        auth0_roles = getenv('AUTH0_ROLES')
        results = lookup_user(member.id)
        account = results[0]
        role_linked = int(getenv('ROLE_LINKED'))
        pronoun_role_color = int(
            getenv('PRONOUN_ROLE_COLOR', '10070710'))
        alert_channel = int(getenv('ALERT_CHANNEL'))
        # old_badges = self.get_emoji(user.nick)

        # Calculate initial information:
        all_pronoun_roles = [
            role for role in member.guild.roles if role.color.value == pronoun_role_color]
        auth0_role_map = dict(r.split(':')
                              for r in auth0_roles.split(';'))

        # Calculate desired nickname:
        desired_nick = f"{account['given_name']} {account['family_name'][0].upper()}"
        if 'display_name_format' in account['user_metadata']:
            desired_nick = account['name']
        elif 'volunteer' in account['user_metadata']:
            desired_nick = f"{account['given_name']} {account['family_name']}"
        desired_nick += ' '  # add spacer between name and badge
        desired_nick = de_emojify(desired_nick)

        # new_badges = []
        for b in badge.get_badges_by_discord_id(account['user_metadata']['discord_id']):
            if b is not None:
                if 'emoji' in b['details']:
                    desired_nick += b['details']['emoji']
        #         if (not(b['details']['emoji'] in old_badges) and 'earnMessage' in b['details']
        #                 and len(self.get_emoji(b['details']['emoji'])) > 0):
        #             new_badges.append(b['details']['earnMessage'])

        desired_nick = desired_nick.strip()

        # Calculate desired roles:
        desired_roles = [member.guild.get_role(role_linked)]
        remove_roles = []

        # - Add roles for auth0 roles
        auth0_desired_roles = [auth0_role_map[r['id']]
                               for r in account['roles']
                               if r['id'] in auth0_role_map]
        desired_roles.extend([member.guild.get_role(int(r))
                              for r in auth0_desired_roles])
        remove_roles.extend([member.guild.get_role(int(r))
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
                desired_pronoun_role = await member.guild.create_role(
                    name=account['user_metadata']['pronoun'],
                    color=Color(pronoun_role_color)
                )
                m = await member.guild.get_channel(alert_channel).send(
                    f'''Alert: New pronoun role created, {desired_pronoun_role.mention} \
        for user <@{account["user_metadata"]["discord_id"]}>
        Please react with ✅ to approve, 🚫 to delete the role, 🔨 to delete the role and ban the user''')
                await m.add_reaction('✅')
                await m.add_reaction('🚫')
                await m.add_reaction('🔨')

            for r in all_pronoun_roles:
                if r in member.roles and r != desired_pronoun_role:
                    remove_roles.append(r)
            desired_roles.append(desired_pronoun_role)
        try:
            await member.edit(nick=desired_nick)
        except discord.Forbidden:
            if member.nick != desired_nick:
                if member.dm_channel is None:
                    await member.create_dm()
                await member.dm_channel.send(f'''
                        Hi there! I was trying to update your nickname, but it looks like you outrank me 😢
        Would you mind setting your nickname to the following?
        `{desired_nick}`''')
        await member.remove_roles(*remove_roles)
        await member.add_roles(*desired_roles)

        #        for new_badge_msg in new_badges:
        #            await user.send(new_badge_msg)

        return f"Nickname: {desired_nick}\nAdd roles: {[n.name for n in desired_roles]}\nRemove roles: {[n.name for n in remove_roles]}"
    welcome_channel = bot.get_channel(int(welcome_channel_id))
    await welcome_channel.send('👋')


@bot.event
async def on_message(message):
    if type(message.channel) == discord.channel.DMChannel and message.author is not message.channel.me:
        welcome_channel = bot.get_channel(int(welcome_channel_id))
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
