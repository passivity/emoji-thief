from random import choice
import discord
from discord.ext import commands
from main import send_error
from main import help_message, invite_message
from emoji import VoteNotFound
from main import CustomCommandError
from main import Colours
from main import mg, db, col


help_embed_categories = discord.Embed(title="Help")
help_embed_categories.colour = Colours.base

category_emojis = ["🔸", "🔸", "🔸", "🔸", "🔸"]
bot_commands = {}

economy_col = db["economy"]


def setup(bot):
    bot.add_cog(Developer(bot))


class Developer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="give",
                      description="Give somebody some Emoji Coins.",
                      usage=">give [user] [amount]",
                      aliases=["add"],
                      pass_context=True)
    async def give(self, ctx, user: discord.User, amount: int):
        if ctx.message.author.id == 554275447710548018:
            current_balance = economy_col.find_one({"id": str(user.id)})
            try:
                current_balance = current_balance["balance"]
            except:
                current_balance = 0

            economy_col.update_one({"id": str(user.id)}, {"$set": {"balance": current_balance + amount}}, upsert=True)

            success_embed = discord.Embed(colour=Colours.success)
            success_embed.add_field(name="Success!", value=f"<:EmojiCoins:732598961558388817> {user} now has `{amount}` more Emoji Coins.")
            await ctx.send(embed=success_embed)

    @commands.command(name="evaluate",
                      description="Evaluate Python code and run it.",
                      usage=">evaluate [code]",
                      aliases=["eval", "ev"],
                      pass_context=True)
    async def evaluate(self, ctx, *args):
        if ctx.message.author.id == 554275447710548018:
            eval_string = " ".join(args)
            print(eval_string)
            eval_result = eval(eval_string)
            eval_embed = discord.Embed(colour=Colours.base)
            eval_embed.add_field(name="Result", value=f"```py\n{eval_result}\n```")

            await ctx.send(embed=eval_embed)

    @commands.command(name="blacklist",
                      description="Blacklist a user from using the bot.",
                      usage=">blacklist [user]",
                      aliases=["bl"],
                      pass_context=True)
    async def blacklist(self, ctx, user: discord.User, *, reason):
        if ctx.message.author.id == 554275447710548018:
            col.insert_one({"id": str(user.id), "reason": reason})

            success_embed = discord.Embed(colour=Colours.success)
            success_embed.add_field(name="Success!", value=f"{user.mention} has been blacklisted.")
            await ctx.send(embed=success_embed)

    @commands.command(name="whitelist",
                      description="Whitelist a user from using the bot.",
                      usage=">whitelist [user]",
                      aliases=["wl"],
                      pass_context=True)
    async def whitelist(self, ctx, user: discord.User):
        if ctx.message.author.id == 554275447710548018:
            col.delete_one({"id": str(user.id)})

            success_embed = discord.Embed(colour=Colours.success)
            success_embed.add_field(name="Success!", value=f"{user.mention} has been whitelisted.")
            await ctx.send(embed=success_embed)







