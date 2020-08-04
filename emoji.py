import re
import shutil
from asyncio import TimeoutError as ReactionTimeout
from asyncio import sleep
from math import ceil
from os import remove
from random import choice
from random import randint
from re import sub

import dbl
import discord
import requests
from discord.ext import commands
from discord.ext.commands import has_permissions

from main import Colours
from main import CustomCommandError
from main import emoji_categories, browse_messages, emoji_list
from main import invite_message, numbers
from main import send_error
from main import send_warning
from main import time_warning_embed


conv = commands.EmojiConverter()
help_embed_test = discord.Embed()
help_embed_test.colour = Colours.base

pride_flags = {"gay": "https://discordemoji.com/assets/emoji/1429_gay_pride_heart.png",
               "bisexual": "https://discordemoji.com/assets/emoji/1210_bi_pride_heart.png",
               "pansexual": "https://discordemoji.com/assets/emoji/5264_Heart_Pan.png",
               "nonbinary": "https://discordemoji.com/assets/emoji/9084_nonbinary_pride_heart.png",
               "transgender": "https://discordemoji.com/assets/emoji/7574_Heart_Trans.png",
               "asexual": "https://discordemoji.com/assets/emoji/7949_Heart_ase.png",
               "lesbian": "https://discordemoji.com/assets/emoji/3347_lesbian_pride_heart.png"}

class VoteNotFound():
    pass


def setup(bot):
    bot.add_cog(Emoji(bot))


class Emoji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.token = "YOUR_DBL_TOKEN_HERE"

        self.bot_list = dbl.DBLClient(self.bot, self.token)

    async def verify_voter(self, user_id: int):
        try:
            response = await self.bot_list.get_user_vote(user_id)
            return response
        except commands.CommandInvokeError:
            pass

    async def update_server_count_top_gg(self, server_count: int):
        await self.bot_list.post_guild_count(server_count)
        await sleep(20)

    async def on_ready(self):
        self.bot.loop.create_task(self.update_server_count_top_gg(len(self.bot.guilds)))

    @commands.Cog.listener()
    async def install_emoji(self, ctx, emoji_json, success_message: str = None, author=None):
        """
        Function used by multiple commands to install an emoji.
        emoji_json requires the following format:
            emoji_json = {"title": str, "image": url}
        Where image is the URL to the image for the emoji.
        """
        if author is None:
            author = ctx.message.author
        response = requests.get(emoji_json["image"], stream=True)

        if response.status_code == 200:
            with open(f"./emojis/{emoji_json['title']}.gif", "wb") as img:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, img)
        else:
            raise Exception(f"Bad status code uploading {emoji_json['title']} received: {response.status_code}")

        with open(f"./emojis/{emoji_json['title']}.gif", "rb") as image:
            new_emoji = await ctx.message.guild.create_custom_emoji(name=emoji_json['title'], image=image.read())

            if success_message is not None:
                random_embed = discord.Embed(title=success_message)
                random_embed.colour = Colours.success
                random_embed.set_thumbnail(url=emoji_json["image"])
                random_embed.add_field(name="Emoji", value=f"`:{emoji_json['title']}:`")
                random_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)
                await ctx.message.channel.send(embed=random_embed)

    @commands.command(name="steal",
                      description="**Requires Nitro:** Steal an emoji that you have access to (i.e. via Nitro or Global Emotes),"
                                  " and add it to your "
                                  "server.",
                      usage=">steal`, `>steal [:emoji:]`, or `>steal [:emoji1:] [:emoji2:] [:emoji3:]",
                      aliases=["s", "new", "take"],
                      pass_context=True)
    @has_permissions(manage_emojis=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def steal(self, ctx, *args):
        """"Steal an emoji from another server."""
        # require vote
        if int(self.bot.user.id) == 719924856619139083:
            response = await self.verify_voter(ctx.message.author.id)

            if response == False:
                await send_error(ctx, "Please vote to use this command -- it's free, takes 30 seconds, and helps the bot keep"
                                      " going."
                                      "\n\n[Click here to vote!](https://top.gg/bot/719924856619139083/vote)\n\n"
                                      "**Important note:** votes can take a few minutes to register.", client=self.bot)
                return

        # no emoji provided; prompt for input
        if len(args) == 0:
            def check(message):
                return message.author == ctx.message.author and message.channel == ctx.message.channel

            try:
                get_emoji_embed = discord.Embed(
                    description="<a:typing:734095511732092958> Please **send the emoji** that you'd like to steal and add to this server (requires Nitro). "
                                "Waiting for your response...")
                get_emoji_msg = await ctx.send(embed=get_emoji_embed)

                get_name_reply = await self.bot.wait_for("message", timeout=30.0, check=check)

                args = get_name_reply.content.split()

            # took too long
            except ReactionTimeout:
                await self.wipe_browse_message(get_emoji_msg, custom_message="👋 You've been inactive for 30 seconds, so I've "
                                                                             "cancelled this steal")
                return

        # emoji provided
        if len(args) > 1:
            await ctx.message.add_reaction("🕒")
            await ctx.message.channel.send(embed=time_warning_embed)
        msg = ctx.message

        count = 0
        installed_emojis = []
        failed_emojis = []
        url = None

        # loop through emojis and install
        for emoji in args:
            try:
                emoji_id = args[count].split(":")[-1][:-1]
                emoji_name = args[count].split(":")[-2]

                # did post emoji, but format is wrong
                if emoji.startswith("<") is False: raise Exception

            # didn't post emoji
            except:
                await send_error(ctx,
                                 "```Something's not right with that emoji. Make sure that you post the emoji itself, "
                                 "not just its name (requires Nitro); "
                                 "you need to be able to see the emoji in the chat.```\n"
                                 "```If you don't have Discord Nitro, you can right click the"
                                 " emoji, get its URL (Copy Link), and upload it via the >upload command.```\n",
                                 client=self.bot)
                return

            # wrong list format
            if len(emoji) > 65:
                raise CustomCommandError("Lists of emojis should be split by a single space. See the expected format.")

            if emoji.startswith("<a"):  # animated
                url = f"https://cdn.discordapp.com/emojis/{emoji_id}.gif"
            else:  # static
                url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"

            # install
            try:
                await self.install_emoji(ctx, {"title": emoji_name, "image": url})
                installed_emojis.append(f"`:{emoji_name}:`")
            except Exception as err:
                failed_emojis.append(f"`:{emoji_name}:`")

            count += 1

            # wait
            if len(args) > 1:
                await sleep(3)

        steal_embed = discord.Embed(
            title=f"{len(installed_emojis)} emojis stolen" if len(installed_emojis) != 1 else f"1 emoji stolen")

        # only one emoji was uploaded
        if len(installed_emojis) == 1 and url:
            steal_embed.set_thumbnail(url=url)

        # no emojis uploaded
        if len(failed_emojis) > 0 and len(installed_emojis) == 0:
            raise CustomCommandError("All of your emojis failed to upload. Check that the server has free emoji slots.")

        # some uploaded, some failed
        elif len(failed_emojis) > 0 and len(installed_emojis) > 0:
            steal_embed.colour = Colours.warn

        # all uploaded
        elif len(installed_emojis) > 0 and len(failed_emojis) == 0:
            steal_embed.colour = Colours.success

        # other (should never happen)
        else:
            steal_embed.colour = Colours.success

        if len(installed_emojis) > 0:
            steal_embed.add_field(name="Uploaded", value=", ".join(installed_emojis))

        steal_embed.set_author(name=ctx.message.author.display_name, icon_url=ctx.message.author.avatar_url)
        steal_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)

        if len(failed_emojis) > 0:
            steal_embed.add_field(name="Failed to upload",
                                  value=f"{', '.join(failed_emojis)}\nEmojis usually fail when the server "
                                        f"has no emoji slots.")

        # send results
        await ctx.message.channel.send(embed=steal_embed)

    @commands.command(name="info",
                      description="Get information on an emoji.",
                      usage=">info [:emoji:]",
                      aliases=["?", "details", "d"],
                      pass_context=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def get_emoji_info(self, ctx, emoji: discord.Emoji):
        """Get information on an emoji."""

        # required to get user who made emoji
        try:
            emoji = await ctx.guild.fetch_emoji(emoji.id)
        except Exception:
            raise CustomCommandError(f"Couldn't find that emoji. Make sure it's one from this server ({ctx.guild.name}). ")

        # setup
        emoji_details_embed = discord.Embed(title=emoji.name, colour=Colours.base)
        emoji_details_embed.set_thumbnail(url=emoji.url)
        emoji_details_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)

        # fields
        emoji_details_embed.add_field(name="ID", value=emoji.id, inline=True)
        emoji_details_embed.add_field(name="Usage", value=f"`:{emoji.name}:`", inline=True)
        emoji_details_embed.add_field(name="Created at", value=emoji.created_at, inline=True)
        emoji_details_embed.add_field(name="Created by", value=emoji.user, inline=True)
        emoji_details_embed.add_field(name="URL", value=f"[Link]({emoji.url})", inline=True)
        emoji_details_embed.add_field(name="Animated", value=emoji.animated, inline=True)

        # send
        await ctx.channel.send(embed=emoji_details_embed)

    @commands.command(name="list",
                      description="Get a list of emojis from this guild.",
                      usage=">list [page number]",
                      aliases=["l"],
                      pass_context=True)
    async def list(self, ctx, page_number=None):
        """List all emojis in a server."""
        if page_number is None: page_number = 1
        try:
            page_number = int(page_number)
        except:
            raise CustomCommandError("Hmm... that page number isn't quite right. Make sure it's a number, not a string.")

        # setup
        emoji_list_embed = discord.Embed(colour=Colours.base)
        emoji_list_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)

        # fields
        emojis = []

        for emoji in ctx.guild.emojis:
            emojis.append(str(emoji))

        if page_number > ceil(len(emojis) / 10):
            raise CustomCommandError(f"That page number is too high. There are only {ceil(len(emojis) / 10)} pages of emojis in "
                                     f"this server.")

        emoji_list_embed.add_field(name="Emojis",
                                   value="".join(emojis[(page_number - 1) * 10:((page_number - 1) * 10) + 10]) if len(
                                       emojis) != 0 else "None")
        if page_number != ceil(len(emojis) / 10): emoji_list_embed.set_footer(
            text=f"Page {page_number} of {ceil(len(emojis) / 10)}")

        # send
        await ctx.channel.send(embed=emoji_list_embed)

    @commands.command(name="pfp",
                      description="Turn somebody's profile picture into an emoji.",
                      usage=">pfp [@User#1234]",
                      aliases=["avatar", "profilepic", "ava", "av"],
                      pass_context=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_emojis=True)
    async def pfp_avatar(self, ctx, emoji_author: discord.Member = None, name_for_emoji=None):
        """Convert an avatar to an emoji."""
        if emoji_author is None:
            emoji_author = ctx.message.author

        # remove special characters from username
        emoji_json = {"title": sub(r"[^\w]", "", emoji_author.display_name if name_for_emoji is None else name_for_emoji),
                      "image": str(emoji_author.avatar_url).replace("?size=1024", "?size=128")}

        # install
        await self.install_emoji(ctx, emoji_json, success_message=f"Emoji added from {emoji_author.display_name}'s avatar",
                                 author=ctx.message.author)

    @commands.command(name="emojify",
                      description="Turn a sentence into emojis.",
                      usage=">emojify [sentence]",
                      aliases=["letters", "e"],
                      pass_context=True)
    async def word_to_emojis(self, ctx, *args):
        """Write a sentence out in emojis."""
        msg_to_send = []

        # loop over each word and add it to the list
        for word in args:
            word_to_add = ""
            word = sub(r"[^\w]", "", word)  # remove special characters
            for char in word:
                if char in numbers:
                    word_to_add += numbers[char]
                else:
                    word_to_add += f":regional_indicator_{char.lower()}: "

            # if word is not blank after special characters removed, store it
            if word_to_add != "":
                msg_to_send.append(word_to_add)

        # too short
        if len(msg_to_send) == 0:
            raise CustomCommandError("You can't send an empty message. Make sure it includes some A-Z letters.")

        # too long
        elif len(":black_large_square: ".join(msg_to_send)) > 1999:
            raise CustomCommandError(f"Your message needs to be less than 2000 characters. Converted to emojis, your message is "
                                     f"{len(':black_large_square: '.join(msg_to_send))} characters long.")

        # just right
        await ctx.channel.send(":black_large_square: ".join(msg_to_send))

    @commands.command(name="upload",
                      description="Convert an image to an emoji.",
                      usage=">upload [url] [name for new emoji]",
                      aliases=["fromurl", "u", "url"],
                      pass_context=True)
    @has_permissions(manage_emojis=True)
    async def emoji_from_url(self, ctx, emoji_url=None, emoji_name=None):
        """Upload an emoji from an image or URL."""

        # no arguments provided
        if emoji_name is None and emoji_url is None:
            def check(message):
                return message.author == ctx.message.author and message.channel == ctx.message.channel

            # no arguments and no attachment
            if len(ctx.message.attachments) == 0:
                # ask for img
                get_img_embed = discord.Embed(description="<a:typing:734095511732092958> Please provide an **image** or **direct"
                                                          " image URL** to create an emoji from. Waiting for your response...")
                get_img_msg = await ctx.send(embed=get_img_embed)
                get_name_msg = get_img_msg

                try:
                    # wait for img
                    get_img_reply = await self.bot.wait_for("message", timeout=30.0, check=check)
                    if len(get_img_reply.attachments) > 0:
                        emoji_url = get_img_reply.attachments[0].url
                    else:
                        emoji_url = get_img_reply.content.rstrip()

                    try:
                        # get name
                        get_name_embed = discord.Embed(
                            description="<a:typing:734095511732092958> Please provide a **name** for this emoji. "
                                        "Waiting for your response...")
                        get_name_msg = await ctx.send(embed=get_name_embed)

                        get_name_reply = await self.bot.wait_for("message", timeout=30.0, check=check)

                        emoji_name = sub(r"[^\w]", "", get_name_reply.content)

                    # timeout
                    except ReactionTimeout:
                        await self.wipe_browse_message(get_img_msg,
                                                       custom_message="👋 You've been inactive for 30 seconds, so I've "
                                                                      "cancelled this upload.")
                        await self.wipe_browse_message(get_name_msg,
                                                       custom_message="👋 You've been inactive for 30 seconds, so I've "
                                                                      "cancelled this upload.")
                        return

                except ReactionTimeout:
                    await self.wipe_browse_message(get_img_msg, custom_message="👋 You've been inactive for 30 seconds, so I've "
                                                                               "cancelled this upload.")
                    return

            # no arguments, one attachment
            else:
                emoji_url = ctx.message.attachments[0].url

                try:
                    # get name
                    get_name_embed = discord.Embed(
                        description="<a:typing:734095511732092958> Please provide a **name** for this emoji. "
                                    "Waiting for your response...")
                    get_name_msg = await ctx.send(embed=get_name_embed)

                    get_name_reply = await self.bot.wait_for("message", timeout=30.0, check=check)

                    emoji_name = sub(r"[^\w]", "", get_name_reply.content)

                # timeout
                except ReactionTimeout:
                    await self.wipe_browse_message(get_name_msg,
                                                   custom_message="👋 You've been inactive for 30 seconds, so I've "
                                                                  "cancelled this upload.")
                    return

        # attachment image provided
        elif len(ctx.message.attachments) > 0:
            emoji_name = emoji_url
            emoji_url = ctx.message.attachments[0].url
        # both arguments
        elif emoji_url and emoji_name:
            pass
        # ???
        else:
            raise CustomCommandError("Invalid format. Here are your options:\n"
                                     "- >upload\n"
                                     "- >upload [url] [name for emoji]\n"
                                     "- Upload an image and set this as the accompanying comment: >upload")

        # upload emoji
        await self.install_emoji(ctx, {"title": emoji_name, "image": emoji_url}, "Emoji added from image",
                                 author=ctx.message.author)

    @commands.command(name="category",
                      description="Browse categories of emojis. You can search for your own stuff with `>search`.",
                      usage=">categories`, then `>category [category]",
                      aliases=["browser", "browse", "cg"],
                      pass_context=True)
    @has_permissions(manage_emojis=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def browse_emojis(self, ctx, category=None, page_count=0, author=None, msg_to_edit: discord.Message = None,
                            random_page=False, search_instead_of_browse=False, force=False, use_db=False):
        """An interactive browser to find and install emojis."""
        au = ctx.message.author if author is None else author
        # print([info for info in browse_messages.values()])
        # print(au)

        if search_instead_of_browse and force is False:
            # require vote
            if int(self.bot.user.id) == 719924856619139083:
                response = await self.verify_voter(ctx.message.author.id)

                if response == False:
                    await send_error(ctx,
                                     "Please vote to use this command -- it's free, takes 30 seconds, and helps the bot keep"
                                     " going."
                                     "\n\n[Click here to vote!](https://top.gg/bot/719924856619139083/vote)\n\n"
                                     "**Important note:** votes can take a few minutes to register.", client=self.bot)
                    return
        try:
            # remove user's active search(es)
            if au.id in [info["user"].id for info in browse_messages.values()] and force is False:
                for key in browse_messages.copy():
                    if browse_messages[key]["user"] == au:
                        conv = commands.MessageConverter()
                        wipe_msg = await conv.convert(ctx=ctx, argument=str(key))
                        await self.wipe_browse_message(wipe_msg,
                                                       custom_message="👋 You started a new search, so I've shut down this one.",
                                                       author=au)
        except:
            pass

        # create embed with author's name and avatar
        browse_embed = discord.Embed()
        browse_embed.colour = Colours.base
        browse_embed.set_author(name=ctx.message.author.display_name if author is None else author.display_name,
                                icon_url=ctx.message.author.avatar_url if author is None else author.avatar_url)

        # if no category selected, display list of categories
        if category is None:
            browse_embed.title = "Choose a category to browse"
            browse_embed.description = "If this isn't your style, you can search over 100,000 emojis using `>search` instead."
            formatted_categories = " ".join(categories := [f"`{category}`" for category in emoji_categories.keys()])
            browse_embed.add_field(name="Categories", value=formatted_categories)
            browse_embed.add_field(name="Usage", value=f"Browse a category: `>category {choice(categories)[1:-1]}` (for example)")
            await ctx.channel.send(embed=browse_embed)

        # if a category was selected, browse it
        else:
            # browsing NSFW requires NSFW channel
            try:
                if category.lower() == "nsfw" and ctx.channel.is_nsfw() is False:
                    raise CustomCommandError("Please do that in an NSFW channel!")
            except AttributeError:
                pass

            # a list of emojis in selected category
            if not search_instead_of_browse:
                try:
                    emoji_list_filtered = [json_item for json_item in emoji_list if
                                           json_item["category"] == emoji_categories[category.capitalize()]]
                except:
                    raise Exception(f"{category} is not a valid category, or there are no emojis in it.")

            else:
                emoji_list_filtered = [{"image": emoji.url, "description": str(emoji.name), "title": str(emoji.name)} for emoji in self.bot.emojis
                                       if category.lower().rstrip() in str(emoji.name).lower().rstrip()]

            # raise error if no emojis found
            if len(emoji_list_filtered) == 0:
                raise Exception(f"{category} is not a valid category, or there are no emojis in it.")

            # if there are some emojis in the category
            else:
                if random_page:
                    page_count = randint(1, len(emoji_list_filtered))
                elif page_count < 0:
                    page_count = len(emoji_list_filtered) + page_count
                elif page_count > len(emoji_list_filtered) - 1:
                    page_count = (len(emoji_list_filtered) - page_count)

                # emoji name
                browse_embed.add_field(name=f"Page {page_count + 1} / {len(emoji_list_filtered)}",
                                       value=f"{emoji_list_filtered[page_count]['description'].split()[0]}")

                # emoji preview
                browse_embed.set_thumbnail(url=emoji_list_filtered[page_count]["image"])

                # if message needs to be edited
                if msg_to_edit is not None:
                    await msg_to_edit.edit(embed=browse_embed)  # add new embed
                    browse_messages[msg_to_edit.id]["page no."] += 1  # increment page number

                    browse_messages[msg_to_edit.id] = {
                        "category": category,
                        "page no.": page_count,
                        "emoji": emoji_list_filtered[page_count],
                        "user": ctx.message.author if author is None else author,
                    }

                    # add new reactions
                    await msg_to_edit.add_reaction("⬅")
                    await msg_to_edit.add_reaction("✅")
                    await msg_to_edit.add_reaction("➡")
                    await msg_to_edit.add_reaction("🔀")

                    msg_id = msg_to_edit.id
                    wipe_msg = msg_to_edit

                # otherwise, post a new message
                else:
                    # send msg
                    embed_msg = await ctx.message.channel.send(embed=browse_embed)

                    # save message data
                    browse_messages[embed_msg.id] = {
                        "category": category,
                        "page no.": page_count,
                        "emoji": emoji_list_filtered[page_count],
                        "user": ctx.message.author if author is None else author,
                    }

                    # add control reactions
                    await embed_msg.add_reaction("⬅")
                    await embed_msg.add_reaction("✅")
                    await embed_msg.add_reaction("➡")
                    await embed_msg.add_reaction("🔀")

                    msg_id = embed_msg.id
                    wipe_msg = embed_msg

                def check(payload):
                    return payload.member == au and payload.message_id == msg_id

                try:
                    payload = await self.bot.wait_for("raw_reaction_add", timeout=30.0, check=check)
                    await self.process_browse_reaction(ctx, payload, search_instead_of_browse)
                except ReactionTimeout:
                    await self.wipe_browse_message(wipe_msg, author=ctx.message.author if author is None else author)
                except Exception as e:
                    await self.wipe_browse_message(wipe_msg,
                                                   custom_message="Something went wrong; closing this search.",
                                                   author=ctx.message.author if author is None else author)
                    raise e

    async def wipe_browse_message(self, message_to_edit, custom_message="👋 You've been inactive for 30 seconds,"
                                                                        " so I've shut down this browser.",
                                  author: discord.User = None):
        """Wipe a browser. For example, to close a browser after x seconds of inactivity."""
        try:
            await message_to_edit.clear_reactions()
        except:
            await message_to_edit.remove_reaction(member=self.bot.user, emoji="⬅")
            await message_to_edit.remove_reaction(member=self.bot.user, emoji="✅")
            await message_to_edit.remove_reaction(member=self.bot.user, emoji="➡")
            await message_to_edit.remove_reaction(member=self.bot.user, emoji="🔀")

        wiped_embed = discord.Embed(colour=Colours.fail)
        wiped_embed.add_field(name="Error", value=custom_message)
        if author: wiped_embed.set_author(name=author.display_name, icon_url=author.avatar_url)

        try:
            del browse_messages[message_to_edit.id]
        except:
            pass

        await message_to_edit.edit(embed=wiped_embed)

    async def process_browse_reaction(self, ctx, payload, search_instead_of_browse):
        converter = commands.MessageConverter()
        msg_to_edit = await converter.convert(ctx=ctx, argument=str(payload.message_id))

        try:
            await msg_to_edit.remove_reaction(member=payload.member, emoji=payload.emoji.name)
        except:
            raise CustomCommandError("Hey, I need the Manage Messages permission to do that.")

        # prev page
        if payload.emoji.name == "⬅":
            await self.browse_emojis(ctx=ctx,
                                     category=browse_messages[int(payload.message_id)]["category"],
                                     page_count=browse_messages[int(payload.message_id)]["page no."] - 1,
                                     author=browse_messages[int(payload.message_id)]["user"],
                                     msg_to_edit=msg_to_edit,
                                     force=True,
                                     search_instead_of_browse=search_instead_of_browse)

        # install emoji
        elif payload.emoji.name == "✅":
            ctx.message.author = browse_messages[int(payload.message_id)]["user"]
            await self.install_emoji(ctx, browse_messages[int(payload.message_id)]["emoji"],
                                     author=browse_messages[int(payload.message_id)]["user"],
                                     success_message="Emoji added from browser")

            await self.browse_emojis(ctx=ctx,
                                     category=browse_messages[int(payload.message_id)]["category"],
                                     page_count=browse_messages[int(payload.message_id)]["page no."],
                                     author=browse_messages[int(payload.message_id)]["user"],
                                     msg_to_edit=msg_to_edit,
                                     force=True,
                                     search_instead_of_browse=search_instead_of_browse)

        # next page
        elif payload.emoji.name == "➡":
            await self.browse_emojis(ctx=ctx,
                                     category=browse_messages[int(payload.message_id)]["category"],
                                     page_count=browse_messages[int(payload.message_id)]["page no."] + 1,
                                     author=browse_messages[int(payload.message_id)]["user"],
                                     msg_to_edit=msg_to_edit,
                                     force=True,
                                     search_instead_of_browse=search_instead_of_browse)

        # shuffle
        elif payload.emoji.name == "🔀":
            await self.browse_emojis(ctx=ctx,
                                     category=browse_messages[int(payload.message_id)]["category"],
                                     page_count=browse_messages[int(payload.message_id)]["page no."] - 1,
                                     author=browse_messages[int(payload.message_id)]["user"],
                                     msg_to_edit=msg_to_edit,
                                     random_page=True,
                                     force=True,
                                     search_instead_of_browse=search_instead_of_browse)

    @commands.command(name="categories",
                      description="View a list of categories.",
                      usage=">categories",
                      aliases=["cgs"],
                      pass_context=True)
    @has_permissions(manage_emojis=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def categories(self, ctx):
        """View a list of available emoji categories."""
        await self.browse_emojis(ctx)

    @commands.command(name="random",
                      description="Add a random emoji to your server.",
                      usage=">random` or `>random [name for emoji]",
                      aliases=["rand", "randomemoji"],
                      pass_context=True)
    @has_permissions(manage_emojis=True)
    async def random(self, ctx, name_for_emoji=None):
        """Install a random emoji."""

        # pick random emoji from cache of all emojis
        emoji = choice(self.bot.emojis)
        emoji_to_upload = {"title": emoji.name, "image": str(emoji.url)}

        # install
        if name_for_emoji is not None:
            emoji_to_upload["title"] = name_for_emoji
        try:
            await self.install_emoji(ctx, emoji_to_upload, success_message="Random emoji added")
        except:
            raise CustomCommandError("Random emoji failed to upload; check that the server has emoji slots available.")

    @commands.command(name="packs",
                      description="Get a list of emoji packs ready for you to download.",
                      usage=">packs",
                      pass_context=True)
    async def packs(self, ctx):
        """A list of emoji packs that can be downloaded."""
        response = requests.get("https://discordemoji.com/api/packs").json()
        packs_embed = discord.Embed(title=f"{len(response)} emoji packs available!")
        packs_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)
        packs_embed.colour = Colours.base

        pack_details = ""
        count = 0

        for pack in response:
            count += 1
            pack_details += f"\n`>pack {count}` -- view pack **\"{pack['name']}\"**"

        packs_embed.add_field(name="View", value=f"Type `>pack [number]` to view (example: `>pack 1`)!\n{pack_details}")

        await ctx.channel.send(embed=packs_embed)

    @commands.command(name="pack",
                      description="View a single emoji pack. Use `>packs` first!",
                      usage=">pack [number]",
                      pass_context=True)
    async def pack(self, ctx, pack_number=None):
        """View a specific emoji pack as listed by >packs."""

        # no number
        if pack_number is None:
            raise CustomCommandError("You need to include a pack number. You can view a list of packs by using >packs, or try "
                                     ">help packs!")

        # wrong number
        try:
            pack_number = int(pack_number)
        except ValueError:
            raise CustomCommandError("That's not a valid pack. Use >packs to see a list of available packs.")

        # get packs
        response = requests.get("https://discordemoji.com/api/packs").json()

        # wrong number
        try:
            pack = response[pack_number - 1]
        except IndexError:
            raise CustomCommandError("That's not a valid pack. Use >packs to see a list of available packs.")

        # fields
        single_pack_embed = discord.Embed(title=pack["name"])
        single_pack_embed.colour = Colours.base
        single_pack_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)
        single_pack_embed.add_field(name="Description", value=pack['description'], inline=False)
        single_pack_embed.add_field(name="Download", value=f"**Download:** {pack['download']}")
        single_pack_embed.set_image(url=pack["image"])

        # send
        await ctx.channel.send(embed=single_pack_embed)

    @commands.command(name="pride",
                      description="Add pride flags to your server.",
                      usage=">pride` or `>pride [flag]",
                      pass_context=True)
    @has_permissions(manage_emojis=True)
    async def pride(self, ctx, pride_flag=None):
        """Install a pride flag emoji."""

        # no flag provided; show list
        if pride_flag is None or pride_flag.lower() == "list":
            pride_flags_embed = discord.Embed(title="Flags")
            pride_flags_embed.colour = Colours.base
            pride_flags_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)
            pride_flags_embed.add_field(name="Available flags", value="\n".join(
                [f"`>pride {flag}` -- add the **{flag.capitalize()}** flag" for flag in pride_flags.keys()]))
            await ctx.message.channel.send(embed=pride_flags_embed)

        # flag not in list
        elif pride_flag.lower() not in pride_flags.keys():
            raise CustomCommandError("That isn't a valid flag. Try >pride or >pride list to see a list of flags.")

        # valid flag
        else:
            await self.install_emoji(ctx, {"title": pride_flag.lower() + "_heart", "image": pride_flags[pride_flag.lower()]},
                                     success_message="Added pride emoji")

    @commands.command(name="jumbo",
                      description="View an emoji in full size.",
                      usage=">jumbo :emoji:",
                      aliases=["j", "big", "size", "sizeup"],
                      pass_context=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_emojis=True)
    async def jumbo(self, ctx, emoji):
        """Send the full-size image of an emoji."""
        await send_warning(ctx, "This command is still in development; you might encounter some bugs.")

        # convert to emoji
        try:
            conv = commands.PartialEmojiConverter()
            emoji = await conv.convert(ctx=ctx, argument=emoji)
        except:
            raise CustomCommandError("This command requires that you submit a custom emoji. Use the emoji itself, "
                                     "not just its name.")

        emoji_int = emoji.id
        emoji_int = int(emoji_int)

        if emoji.animated:  # animated; get gif
            url = f"https://cdn.discordapp.com/emojis/{emoji_int}.gif"
        else:  # static; get png
            url = f"https://cdn.discordapp.com/emojis/{emoji_int}.png"

        jumbo_embed = discord.Embed(colour=Colours.success)
        jumbo_embed.set_image(url=url)

        # send
        await ctx.message.channel.send(embed=jumbo_embed)

    @commands.command(name="search",
                      description="Search for emojis.",
                      usage=">search [keyword]",
                      aliases=["find"],
                      pass_context=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_emojis=True)
    async def search(self, ctx, keyword):
        """Search the cache of emojis for a specific term."""
        await self.browse_emojis(ctx, category=keyword, search_instead_of_browse=True, use_db=True)

    @commands.command(name="link",
                      description="Get an emoji's URL.",
                      usage=">link [:emoji from this server:]",
                      aliases=["getlink"],
                      pass_context=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def link(self, ctx, emoji: discord.Emoji):
        """Get an emoji's URL."""
        link_embed = discord.Embed(colour=Colours.success)
        link_embed.add_field(name=emoji.name, value=emoji.url)
        link_embed.set_thumbnail(url=emoji.url)
        await ctx.send(embed=link_embed)

    @commands.command(name="clap",
                      description="👏YOUR👏MESSAGE👏HERE👏",
                      usage=">clap [message]",
                      aliases=["👏"],
                      pass_context=True)
    async def clap(self, ctx, *, args):
        """Replace spaces with the clap emoji."""
        if len(args) == 0:
            raise CustomCommandError("You need to submit a message.")
        clapped = "👏" + "👏".join(args.split()) + "👏"
        if (msg_length := len(clapped)) > 2000:
            raise CustomCommandError(f"Your message needs to be shorter than 2000 characters (current length: {msg_length}).")
        await ctx.message.channel.send(clapped)

    @commands.command(name="replace",
                      description="Use emojis from other servers for free. **Emoji Thief must be in the server that you"
                                  " want to use emojis from.**",
                      usage=">replace [:emoji from another server:]",
                      aliases=["r", "nqn", "nitro", "nitroify", "free"],
                      pass_context=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def convert(self, ctx, *msg):

        o_msg = list(msg)  # original message
        msg = list(msg)

        count = 0

        # find :unparsed emojis: in message
        for word in msg:
            word_results = re.search(r":(.*?):", word)
            if word_results is None:
                msg[count] = "-"

            count += 1

        count = 0
        # try to replace emojis with real emojis
        for word in msg:
            if word != "-":  # non-emoji words are replaced with "-"
                try:
                    word = word[1:-1]  # omit colons
                    emoji = await conv.convert(ctx=ctx, argument=word)
                    msg[count] = emoji
                    if emoji.animated:
                        msg[count] = f"<a:{msg[count].name}:{msg[count].id}>"
                    else:
                        msg[count] = f"<:{msg[count].name}:{msg[count].id}>"
                except:
                    msg[count] = o_msg[count]
            else:
                msg[count] = o_msg[count]
            count += 1

        # store avatar
        with open(f'./emojis/{ctx.message.author.id}.jpg', 'wb') as av:
            av.write(requests.get(ctx.message.author.avatar_url).content)

        # set up webhook - could be optimised by setting up the webhook on server join and using utils.get to find it
        with open(f'./emojis/{ctx.message.author.id}.jpg', 'rb') as av:
            try:
                wh = await ctx.message.channel.create_webhook(name=ctx.message.author.display_name,
                                                              avatar=av.read(),
                                                              reason=f"Replacing emojis from {ctx.message.author}")
            except:
                raise CustomCommandError("Hey, I need an extra permission for that. Ask a mod to give my role (@Emoji "
                                         "Thief) the Manage Webhooks permission!")

        # send on webhook
        await wh.send(" ".join(msg))
        try:
            await ctx.message.delete()
        except:
            raise CustomCommandError("Hey, I need an extra permission for that. Ask a mod to give my role (@Emoji "
                                     "Thief) the Manage Messages permission!")

        # del webhook
        await wh.delete()

        # del file
        remove(f'./emojis/{ctx.message.author.id}.jpg')



