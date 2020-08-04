from asyncio import sleep

import dbl
import discord
import requests
from discord.ext import commands
from random import randint

import pymongo

import emoji

full_command_list = []


class InvalidCommandFormat(Exception):
    pass


class CustomCommandError(Exception):
    pass


class States:
    OK = '[\033[94m-\033[0m]'
    SUCCESS = '[\033[92m+\033[0m]'
    WARNING = '[\033[93m?\033[0m]'
    FAIL = '[\033[91m!\033[0m]'


class Colours:
    base = discord.Color(16760412)
    success = discord.Color(3066993)
    fail = discord.Color(15742004)
    warn = discord.Color(16707936)


time_warning_embed = discord.Embed(colour=Colours.warn)
time_warning_embed.add_field(name="Warning!", value="Due to Discord rate limits, this command waits a few seconds between each "
                                                    "emoji, so this might take a while. I'll let you know when it's done.")

emoji_list = requests.get(f"https://discordemoji.com/api/").json()

command_counter = {}

browse_messages = {}
bot = commands.AutoShardedBot(command_prefix=">", max_messsages=1)
bot.remove_command("help")
help_embed = discord.Embed()
help_embed.colour = Colours.base

help_embed_test = discord.Embed()
help_embed_test.colour = Colours.base

invite_message = "Like this bot? Please >vote for it!"
help_message = "Need more help? Join the support server: discord.gg/wzG9Y8s"


numbers = {
    "1": "1️⃣",
    "2": "2️⃣",
    "3": "3️⃣",
    "4": "4️⃣",
    "5": "5️⃣",
    "6": "6️⃣",
    "7": "7️⃣",
    "8": "8️⃣",
    "9": "9️⃣",
    "0": "0️⃣"
}


emoji_categories = {
    "Original": 1,
    "Tv": 2,
    "Meme": 3,
    "Anime": 4,
    "Celebrity": 5,
    "Blobs": 6,
    "Thinking": 7,
    "Animated": 8,
    "Nsfw": 9,
    "Gaming": 10,
    "Letters": 11,
    "Other": 12,
    "Pepe": 13,
    "Logos": 14
}

startup_extensions = ["emoji", "management", "info", "developer", "reactions", "economy"]

mg = pymongo.MongoClient("mongodb://localhost:27017/")
db = mg["emoji-thief"]
col = db["blacklist"]


@bot.event
async def on_message(message):
    global full_command_list

    try:
        if message.content.split()[0].startswith(">"):
            # print(col.find_one({"id": str(message.author.id)}))
            if bl := col.find_one({"id": str(message.author.id)}):
                if message.content.split()[0][1:] in full_command_list:
                    ctx = bot.get_channel(message.channel.id)
                    await send_error(ctx, f"You're blacklisted. Reason: `{bl['reason'] if bl['reason'] else 'unspecified'}`")
            else:
                if message.content.split()[0][1:] in full_command_list:
                    if randint(1, randint(1, 35)) == 1:
                        await give_money(message.author.id, randint(1, 3))
                    await bot.process_commands(message)
    except:
        pass


async def send_error(ctx, err, extra_info=None, client=bot):
    """Send an error message to s specified channel; extra_info will add more detail."""
    error_embed = discord.Embed(title="Something went wrong!")
    error_embed.colour = Colours.fail
    if type(ctx) == discord.Message:
        error_embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
    else:
        try:
            error_embed.set_author(name=ctx.message.author.display_name, icon_url=ctx.message.author.avatar_url)
        except:
            pass

    error_embed.add_field(name="Error", value=f"{err}")
    if extra_info is not None:
        error_embed.add_field(name=extra_info["name"], value=f"`{extra_info['value']}`", inline=False)
    error_embed.set_footer(text=help_message, icon_url=client.user.avatar_url)
    await ctx.send(embed=error_embed)


async def send_warning(ctx, message):
    """Send a warning in the chat."""
    warning_embed = discord.Embed(colour=Colours.warn)
    warning_embed.add_field(name="Warning!",
                            value=message)
    await ctx.message.channel.send(embed=warning_embed)


@bot.event
async def on_ready():
    """Run setup stuff that only needs to happen once."""
    global help_embed, help_embed_categories, full_command_list

    full_command_list += [command.name for command in bot.commands]

    alias_list = [alias for alias in [command.aliases for command in bot.commands]]
    for aliases in alias_list:
        for single_alias in aliases:
            full_command_list.append(single_alias)

    help_embed.colour = Colours.base

    await bot.change_presence(activity=discord.Game(name=f"just updated!"))
    try:
        print(f"Serving {sum(guild.member_count for guild in bot.guilds)} users in {len(bot.guilds)} servers!")
    except:
        pass

    while 1:
        try:
            await sleep(20)
            await bot.change_presence(activity=discord.Game(name=f">help | {len(bot.guilds)} servers"))
            await bot_list.post_guild_count(shard_count=len(bot.latencies))

        except Exception as err:
            print(f"Fail: {err}")
            continue

			
if __name__ == "__main__":
    # startup_extensions = ["emoji", "management", "info", "developer", "reactions", "economy"]

    for extension in startup_extensions:
        try:
            bot.load_extension(extension)
        except Exception as err:
            print(err)

    dbl_token = "YOUR_DBL_TOKEN_HERE"

    bot_list = dbl.DBLClient(bot, dbl_token)

    from economy import give_money
    print(discord.__version__)

	bot.run("YOUR_TOKEN_HERE")



