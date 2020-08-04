from random import choice
import discord
from discord.ext import commands
from main import send_error
from main import help_message, invite_message
from emoji import VoteNotFound
from main import CustomCommandError
from main import Colours
from main import numbers

help_embed_categories = discord.Embed(title="Help")
help_embed_categories.colour = Colours.base

category_emojis = ["🔸", "🔸", "🔸", "🔸", "🔸", "🔸"]
dev_cogs = ["developer"]
bot_commands = {}


def setup(bot):
    bot.remove_command("help")
    bot.add_cog(Information(bot))


class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # a list of all commands

    async def create_help_embed(self, ctx, help_category):
        """Create a help embed based on the specified parameter."""

        # create embed
        help_embed = discord.Embed(title=f"Help for {help_category.capitalize()}", colour=Colours.base)
        help_embed.set_footer(text=help_message, icon_url=self.bot.user.avatar_url)

        # if parameter is a category, list all commands in the category
        if help_category.capitalize() in self.bot.cogs:
            if help_category.lower() in dev_cogs and ctx.message.author.id != 554275447710548018:
                return
            else:
                help_embed.add_field(name="Commands",
                                     value=f"`{'` `'.join(sorted([command.name for command in commands.Cog.get_commands(self.bot.cogs[help_category.capitalize()])]))}`\n\n"
                                           f"Type `>help [command]` (e.g. `>help {choice(commands.Cog.get_commands(self.bot.cogs[help_category.capitalize()])).name}`)"
                                           f" for specific help on a command.")

        # not a category
        elif help_category.lower() in [command.name for command in self.bot.commands]:

            # add -- if they exist -- details of selected command (parameter) to embed
            for key, value in bot_commands[help_category.lower()].items():
                if len(value) > 0:
                    help_embed.add_field(name=key, value=value, inline=False)

        # doesnt exist
        else:
            raise CustomCommandError(f"Couldn't find the command \"{help_category}\". You can view a list of commands with >help.")

        # return the help embed
        return help_embed

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Listen for errors and send an error message."""

        # send specific cool-down message
        if isinstance(error, CustomCommandError):
            await send_error(ctx, str(error.__cause__), client=self.bot)
        if isinstance(error, commands.CommandOnCooldown):
            await send_error(ctx, f"That command is on cooldown. Try again in {round(error.retry_after)} seconds.", client=self.bot)
        elif isinstance(error, VoteNotFound):
            await send_error(ctx, "**Vote**\nPlease vote for the bot to use this command! It's free and helps development.\n\n"
                                  "[Link to vote on top.gg](https://top.gg/bot/719924856619139083/vote)\n\n"
                                  "Votes can take a couple of minutes to register.", client=self.bot)
        # miscellaneous errors
        else:
            error = error.__cause__ if error.__cause__ is not None else error
            # if command has a list of common errors (main.py), send it + expected format
            await send_error(ctx, f"```\n{error}```", extra_info={"name": "Expected format", "value": ctx.command.usage}, client=self.bot)

    @commands.command(name="poll",
                      description="Make an emoji poll.",
                      usage=">poll [\"poll title\"] [\"option1\"] [\"option2\"] [\"option3\"]",
                      pass_context=True)
    async def poll(self, ctx, *args):
        """Make a poll."""

        yes_no_poll = False

        # no args
        if len(args) == 0:
            raise CustomCommandError("You need to include a title, and some options.")
        # one arg; yes/no poll
        elif len(args) == 1:
            yes_no_poll = True
        # too many args
        elif len(args) > 10:
            raise CustomCommandError("Too many options.")

        poll_embed = discord.Embed(colour=Colours.base, title=f"Poll: {args[0]}")
        poll_embed.set_footer(text="Vote by reacting!")

        desc = ""
        reactions_to_add = []
        count = 0

        # add poll options
        for poll_option in args[1:]:
            desc += f"{list(numbers.values())[count]}  {poll_option}\n"
            reactions_to_add.append(list(numbers.values())[count])

            count += 1

        # add yes/no
        if yes_no_poll:
            desc += f"1️⃣  Yes\n" \
                    f"2️⃣  No"
            reactions_to_add = ["1️⃣", "2️⃣"]
        poll_embed.description = desc

        # send poll
        poll = await ctx.send(embed=poll_embed)

        # react with possible options
        for emoji in reactions_to_add:
            await poll.add_reaction(emoji)

    @commands.command(name="invite",
                      description="Generate an invite link to bring Emoji Thief to your own server.",
                      usage=">invite",
                      pass_context=True)
    async def invite(self, ctx):
        """Send an invite link so that the user can invite the bot."""

        await ctx.message.add_reaction("🧡")

        invite_embed = discord.Embed()
        invite_embed.colour = Colours.base
        invite_embed.add_field(name="Invite link",
                               value="[Click here!]("
                                     "https://discord.com/oauth2/authorize?client_id=719924856619139083&permissions=1611000896"
                                     "&scope=bot)")
        invite_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)

        await ctx.channel.send(embed=invite_embed)

    @commands.command(name="stats",
                      description="Get some basic stats about what Emoji Thief is up to.",
                      usage=">stats",
                      aliases=["statistics", "st"],
                      pass_context=True)
    async def stats(self, ctx):
        """Display some simple stats about the bot's status."""
        stats_embed = discord.Embed(title="Stats for Emoji Thief")
        stats_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)
        stats_embed.colour = Colours.base
        stats_embed.add_field(name="Members",
                              value=f"{sum(guild.member_count for guild in self.bot.guilds)}")
        stats_embed.add_field(name="Servers",
                              value=f"{len(self.bot.guilds)}")
        stats_embed.add_field(name="Emojis",
                              value=f"{len(self.bot.emojis)}")
        await ctx.channel.send(embed=stats_embed)

    @commands.command(name="help",
                      description="Get help on a certain category or command.",
                      usage=">help`, `>help [category]`, or `>help [command]",
                      aliases=["h", "wtf", "commands"],
                      pass_context=True)
    async def help(self, ctx, help_category=None):
        """Send the help message specified in on_ready."""
        if help_category is None:
            help_embed_categories = discord.Embed(title=f"Help", colour=Colours.base)
            help_embed_categories.set_footer(text=help_message, icon_url=self.bot.user.avatar_url)
            count = 0
            help_embed_categories.add_field(name="What's new?",
                                            value="🔸 Easily create emoji-based polls with `>poll`! Type `>help poll` to "
                                                  "get started.",
                                            inline=False)

            # add categories
            for category in self.bot.cogs:
                if category.lower() not in dev_cogs:
                    help_embed_categories.add_field(name="\u200b",
                                                    value=f"**{category_emojis[count]} {category}**\n"
                                                          f"`>help {category.lower()}`\n",
                                                    inline=True)
                    count += 1
                else:
                    if ctx.message.author.id == 554275447710548018:
                        help_embed_categories.add_field(name="\u200b",
                                                        value=f"**{category_emojis[count]} {category}**\n"
                                                              f"`>help {category.lower()}`\n",
                                                        inline=True)
                        count += 1

            # add whitespace
            while count % 3 != 0:
                help_embed_categories.add_field(name="\u200b",
                                                value="\u200b",
                                                inline=True)
                count += 1

            await ctx.channel.send(embed=help_embed_categories)
        else:
            help_embed = await self.create_help_embed(ctx, help_category)
            if help_embed is not None:
                await ctx.channel.send(embed=help_embed)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Send a message on guild join."""
        join_embed = discord.Embed(title="Hi!")
        join_embed.colour = Colours.base
        join_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)
        join_embed.add_field(name="\u200b",
                             value=f"Hi, **{guild.name}**! I'm Emoji Thief: a bot to easily manage your "
                                   f"server's emojis. My prefix is `>`!\n\n"
                                   f"To get started, why not try typing `>help`?\n"
                                   f"If you like this bot, feel free to `>invite` it to your server!\n\n"
                                   f"**Commands:** {' '.join(sorted([f'`{command}`' for command in self.bot.commands if command not in commands.Cog.get_commands(self.bot.cogs['Developer'])]))}")

        # send to the first channel the bot can type in
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(embed=join_embed)
                break

    @commands.command(name="vote",
                      description="The easiest way to support the bot.",
                      usage=">vote",
                      aliases=["v", "uv", "upvote"],
                      pass_context=True)
    async def vote(self, ctx):
        """Send a vote link."""

        await ctx.message.add_reaction("🧡")

        vote_embed = discord.Embed()
        vote_embed.colour = Colours.base
        vote_embed.add_field(name="Vote link",
                             value="[Click here!]("
                                   "https://top.gg/bot/719924856619139083/vote)\n\nYou can upvote every 12 hours.")
        vote_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)

        await ctx.channel.send(embed=vote_embed)

    @commands.command(name="shard",
                      description="Information on the current shard.",
                      usage=">shard",
                      pass_context=True)
    async def shard(self, ctx):
        """Shard information."""

        shard_embed = discord.Embed(colour=Colours.base, title="Shard information")
        shard_embed.add_field(name=f"<:online2:730348682460790784> Shard {ctx.message.guild.shard_id + 1} of {len(self.bot.latencies)}",
                              value=f"**Ping:** {int(self.bot.latencies[ctx.message.guild.shard_id][1] * 1000)}ms")
        await ctx.send(embed=shard_embed)

    @commands.command(name="ping",
                      description="Pong.",
                      usage=">ping",
                      pass_context=True)
    async def shard(self, ctx):
        """Ping information."""

        shard_embed = discord.Embed(colour=Colours.base, title="Pong!")
        shard_embed.add_field(
            name=f"<:online2:730348682460790784> Shard {ctx.message.guild.shard_id + 1} of {len(self.bot.latencies)}",
            value=f"**Ping:** {int(self.bot.latencies[ctx.message.guild.shard_id][1] * 1000)}ms")
        await ctx.send(embed=shard_embed)

    @commands.command(name="shards",
                      description="Information on all shards.",
                      usage=">shards",
                      pass_context=True)
    async def shards(self, ctx):
        """Shard information of all shards."""

        shard_embed = discord.Embed(colour=Colours.base, title="Shard information")
        for shard_id in range(0, len(self.bot.latencies)):
            shard_embed.add_field(
                name=f"<:online2:730348682460790784> Shard {shard_id + 1} of {len(self.bot.latencies)}"
                     + " (you!)" if shard_id == ctx.message.guild.shard_id else
                f"<:online2:730348682460790784> Shard {shard_id + 1} of {len(self.bot.latencies)}",
                value=f"**Ping:** {int(self.bot.latencies[ctx.message.guild.shard_id][1] * 1000)}ms",
                inline=True)
        await ctx.send(embed=shard_embed)

    @commands.Cog.listener()
    async def on_ready(self):
        """Generate a list of commands for use with >help."""
        global bot_commands

        bot_commands = {
            command.name: {
                "Usage": f"`{command.usage}`" if command.usage is not None else "",
                "Description": command.description,
                "Aliases": f"`{'`, `'.join(command.aliases)}`" if len(command.aliases) > 0 else ""
            } for command in self.bot.commands}







