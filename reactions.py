import discord
from discord.ext import commands
from main import CustomCommandError
from main import Colours

help_embed_categories = discord.Embed(title="Help")
help_embed_categories.colour = Colours.base

category_emojis = ["🔸", "🔸", "🔸", "🔸", "🔸"]
bot_commands = {}


def setup(bot):
    bot.add_cog(Reactions(bot))


async def send_reaction(ctx, image_url, action, *, target_user=None):
    try:
        conv = commands.UserConverter()
        user = await conv.convert(ctx=ctx, argument="".join(target_user))
        user = user.display_name
    except:
        user = target_user

    if target_user is None:
        react_embed = discord.Embed(colour=Colours.base,
                                    title=f"{ctx.message.author.display_name} {action} somebody in the chat!")
    else:
        react_embed = discord.Embed(colour=Colours.base,
                                    title=f"{ctx.message.author.display_name} {action} {user}!")

    react_embed.set_image(url=image_url)

    await ctx.send(embed=react_embed)


class Reactions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="slap",
                      description="Slap somebody in the chat.",
                      usage=">slap [user]",
                      aliases=["hit", "smack"],
                      pass_context=True)
    async def slap(self, ctx, *, target_user=None):
        await send_reaction(ctx, image_url="https://i.imgur.com/fm49srQ.gif", action="slaps", target_user=target_user)

    @commands.command(name="hug",
                      description="Hug somebody in the chat.",
                      usage=">hug [user]",
                      pass_context=True)
    async def hug(self, ctx, *, target_user=None):
        await send_reaction(ctx, image_url="https://i.postimg.cc/L4b5hVGH/tenor.gif", action="hugs", target_user=target_user)

    @commands.command(name="kiss",
                      description="Kiss somebody in the chat.",
                      usage=">kiss [user]",
                      pass_context=True)
    async def kiss(self, ctx, *, target_user=None):
        await send_reaction(ctx, image_url="https://i.postimg.cc/c1w14N7c/tenor-1.gif", action="kisses", target_user=target_user)







