from random import choice, randint
import discord
from discord.ext import commands
from main import send_error
from main import help_message, invite_message
from emoji import VoteNotFound
from main import CustomCommandError
from main import Colours
from main import mg, db
from asyncio import TimeoutError

help_embed_categories = discord.Embed(title="Help")
help_embed_categories.colour = Colours.base

category_emojis = ["🔸", "🔸", "🔸", "🔸", "🔸", "🔸"]
bot_commands = {}

economy_col = db["economy"]

products = {"Special role in the support server (discord.gg/wzG9Y8s)": 15}


def setup(bot):
    bot.add_cog(Economy(bot))


def get_emoji(user_id, amount):
    user_inventory = economy_col.find_one({"id": str(user_id)})
    try:
        balance = int(user_inventory["balance"])
    except:
        balance = 0

    return "\n<:greentick:732614555439464531>" if balance >= amount else "\n<:redtick:732614344583544955>"


async def get_balance(user_id):
    user_inventory = economy_col.find_one({"id": str(user_id)})
    try:
        balance = int(user_inventory["balance"])
    except:
        balance = 0

    return balance


async def take_money(user_id, amount):
    current_balance = economy_col.find_one({"id": str(user_id)})
    try:
        current_balance = current_balance["balance"]
    except:
        current_balance = 0

    economy_col.update_one({"id": str(user_id)}, {"$set": {"balance": current_balance - amount}}, upsert=True)


async def give_money(user_id, amount):
    current_balance = economy_col.find_one({"id": str(user_id)})
    try:
        current_balance = current_balance["balance"]
    except:
        current_balance = 0

    economy_col.update_one({"id": str(user_id)}, {"$set": {"balance": current_balance + amount}}, upsert=True)


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="balance",
                      description="View your balance.",
                      usage=">balance",
                      aliases=["bal"],
                      pass_context=True)
    async def balance(self, ctx):
        balance = await get_balance(ctx.message.author.id)

        inventory_embed = discord.Embed(colour=Colours.base)
        inventory_embed.add_field(name="Balance",
                                  value=f"<:EmojiCoins:732598961558388817> You have **{balance}** Emoji Coins.\n\n"
                                        f"You can get more Coins by using the bot, and can redeem them using `>shop` or "
                                        f"`>redeem`.")

        await ctx.send(embed=inventory_embed)

    @commands.command(name="shop",
                      description="Redeem your Emoji Coins for cool things.",
                      usage=">shop",
                      aliases=["buy", "redeem"],
                      pass_context=True)
    async def shop(self, ctx):
        balance = await get_balance(ctx.message.author.id)

        shop_embed = discord.Embed(colour=Colours.base, title="Shop")
        shop_embed.add_field(name="Balance", value=f"<:EmojiCoins:732598961558388817> {balance}", inline=False)
        shop_embed.add_field(name=f"Hey!",
                             value="This is still in development. If you have ideas for things you could buy, please suggest "
                                   "them in the support server: `discord.gg/wzG9Y8s`",
                             inline=False)

        await ctx.send(embed=shop_embed)

        def check(message):
            return message.author == ctx.message.author

        try:
            reply = await self.bot.wait_for("message", timeout=(timeout := 30.0), check=check)

        except TimeoutError:
            pass

    @commands.command(name="rank",
                      description="View the Emoji Coins leaderboard for this server.",
                      usage=">rank",
                      aliases=["lb", "richest", "leaderboard"],
                      pass_context=True)
    async def rank(self, ctx, ranks_to_show: int = 5):
        user_ranks = economy_col.find()
        user_ranks = user_ranks.sort([("balance", -1), ("id", 1)])

        rank_embed = discord.Embed(colour=Colours.base, title=f"Leaderboard for {ctx.message.guild}")

        count = 0
        conv = commands.UserConverter()
        ranks = []
        users = []
        balances = []
        do_add_author, author_count, author_balance = None, None, None
        guild = self.bot.get_guild(ctx.message.guild.id)

        for item in user_ranks:

            if guild.get_member(int(item["id"])) is not None:
                try:
                    count += 1
                    user = await conv.convert(ctx=ctx, argument=str(item["id"]))
                except:
                    continue
                if count <= ranks_to_show:
                    ranks.append(f"{count}.")
                    users.append(str(user))
                    balances.append(f"<:EmojiCoins:732598961558388817> {item['balance']}")
                if str(user.id) == str(ctx.message.author.id):
                    do_add_author = True
                    author_count = count
                    author_balance = item["balance"]

        if str(ctx.message.author) not in users and do_add_author:
            ranks.append("**...**")
            users.append("\u200b")
            balances.append("\u200b")
            ranks.append(f"{author_count}.")
            users.append(f"**{ctx.message.author}**")
            balances.append(f"<:EmojiCoins:732598961558388817> {author_balance}")

        count = 0
        for username in users:
            if username == str(ctx.message.author):
                ranks[count] = f"**{ranks[count]}**"
                users[count] = f"**{users[count]}**"
                balances[count] = f"**{balances[count]}**"

            count += 1

        rank_embed.add_field(name="#", value="\n".join(ranks), inline=True)
        rank_embed.add_field(name="User", value="\n".join(users), inline=True)
        rank_embed.add_field(name="Balance", value="\n".join(balances), inline=True)
        await ctx.send(embed=rank_embed)
