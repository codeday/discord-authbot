from discord.ext import commands


class _DefaultRepr:
    def __repr__(self):
        return '<default-help-command>'


_default = _DefaultRepr()


class SuperBot(commands.Bot):
    def __init__(self, command_prefix, help_command=_default, description=None, **options):
        super(SuperBot, self).__init__(command_prefix, help_command, description, **options)

    def process_commands(self, message):
        ctx = await self.get_context(message)
        await self.invoke(ctx)
