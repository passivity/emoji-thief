from asyncio import sleep, TimeoutError
from re import sub

import discord
from discord.ext import commands
from discord.ext.commands import has_permissions

from main import Colours
from main import CustomCommandError
from main import invite_message
from main import time_warning_embed

help_embed_test = discord.Embed()
help_embed_test.colour = Colours.base


class Management(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_confirmation(self, ctx, timeout=30.0, thumbnail_url=None, required_msgs=("yes", "y"), title="Are you sure?",
                               message="Type `yes` to confirm, or anything else to cancel."):
        """Get confirmation of a moderation action."""
        # confirmation embed
        confirm_embed = discord.Embed(colour=Colours.warn)
        if thumbnail_url is not None:
            confirm_embed.set_thumbnail(url=thumbnail_url)
        confirm_embed.add_field(name=title, value=message)
        confirm_embed.set_footer(text=f"This will time out after {int(timeout)} seconds.")
        confirm_embed.set_author(name=ctx.message.author.display_name, icon_url=ctx.message.author.avatar_url)

        # send confirm embed
        embed_message_to_edit = await ctx.send(embed=confirm_embed)

        def check(message):
            return message.author == ctx.message.author

        # wait for response
        try:
            reply = await self.bot.wait_for("message", timeout=(timeout := 30.0), check=check)

            if reply.content.lower().rstrip() in required_msgs:
                return embed_message_to_edit, True  # confirmed
            else:
                cancel_embed = discord.Embed(colour=Colours.fail)
                cancel_embed.add_field(name="Deletion cancelled", value=f"{ctx.message.author.display_name} didn't type `yes`.")

                await embed_message_to_edit.edit(embed=cancel_embed)

                return embed_message_to_edit, False  # cancelled

        # timeout
        except TimeoutError:
            timeout_embed = discord.Embed(colour=Colours.fail)
            timeout_embed.add_field(name="Deletion cancelled",
                                    value=f"{ctx.message.author.display_name} took more than {int(timeout)} seconds to respond.")

            await embed_message_to_edit.edit(embed=timeout_embed)

            return embed_message_to_edit, False  # cancelled

    @commands.command(name="rename",
                      description="Rename an emoji.",
                      usage=">rename [:emoji:] [new name]",
                      aliases=["re", "name"],
                      pass_context=True)
    @has_permissions(manage_emojis=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rename_emoji(self, ctx, emoji_to_rename: discord.Emoji, *args):
        """Rename an emoji."""

        # no emoji
        if emoji_to_rename.guild != ctx.message.guild: raise CustomCommandError("Couldn't find that emoji in this server.")

        old_name = emoji_to_rename.name
        args = list(args)

        # remove symbols and replace spaces with underscore
        new_name = "_".join([sub(r"[^\w]", "", word.replace("\"", "")) for word in args])

        if new_name == "":
            raise Exception

        # rename
        await emoji_to_rename.edit(name=new_name)

        # fields
        rename_embed = discord.Embed(title="Emoji renamed")
        rename_embed.colour = discord.Color(3066993)
        rename_embed.set_thumbnail(url=emoji_to_rename.url)
        rename_embed.add_field(name="Details", value=f"`:{old_name}:` -> `:{new_name}:`")
        rename_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)

        # send
        await ctx.message.channel.send(embed=rename_embed)

    @commands.command(name="delete",
                      description="Delete an emoji",
                      usage=">delete [:emoji:]",
                      aliases=["remove", "del", "deleteemoji", "delemoji"],
                      pass_context=True)
    @has_permissions(manage_emojis=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def delete_emoji(self, ctx, emoji_to_delete: discord.Emoji):
        """Delete an emoji."""

        # no emoji
        if emoji_to_delete.guild != ctx.message.guild: raise CustomCommandError("Couldn't find that emoji in this server.")

        # get confirmation
        msg_to_edit, result = await self.get_confirmation(ctx, thumbnail_url=emoji_to_delete.url)

        if result is True:
            # delete embed
            delete_embed = discord.Embed(title="Emoji deleted")
            delete_embed.colour = discord.Color(3066993)
            delete_embed.set_thumbnail(url=emoji_to_delete.url)
            delete_embed.add_field(name="Emoji", value=f"`:{emoji_to_delete.name}:`")
            delete_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)

            await emoji_to_delete.delete(reason=f"Deleted by {ctx.message.author.display_name}")
            await msg_to_edit.edit(embed=delete_embed)

    @commands.command(name="purge",
                      description="Mass delete emojis, or emojis uploaded by a certain person.",
                      usage=">purge [number of emojis to delete]` or `>purge [number of emojis to delete] [person who uploaded them]",
                      pass_context=True)
    @has_permissions(manage_emojis=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def purge_emojis(self, ctx, emojis_to_delete: int, emoji_author: discord.Member = None):
        """Delete many emojis."""

        # get confirmation
        msg_to_edit, result = await self.get_confirmation(ctx, message=f"**This will delete {emojis_to_delete} emojis.** Type "
                                                                       f"`yes` to confirm, or anything else to cancel.")

        if result is True:

            await ctx.message.add_reaction("🕒")
            await ctx.message.channel.send(embed=time_warning_embed)

            # list of emojis, newest first
            emoji_list = await ctx.message.guild.fetch_emojis()
            emoji_list = reversed(emoji_list)

            deleted_emojis = 0
            deleted_emojis_names = []

            emoji_author_id = emoji_author.id if emoji_author is not None else None

            # delete emojis
            for emoji in emoji_list:
                # emoji_author is None if no user was specified; delete all emojis instead
                if emoji.user.id == emoji_author_id or emoji_author is None:
                    deleted_emojis += 1
                    if deleted_emojis > emojis_to_delete:
                        break

                    # print deleted emojis to channel
                    deleted_emojis_names.append("`:" + emoji.name + ":`")
                    await sleep(3)
                    await emoji.delete(reason=f">purge; {ctx.message.author}")

            # "anyone" makes more sense in embed (below)
            if emoji_author is None:
                emoji_author = "anyone"

            # send success message to channel
            purge_embed = discord.Embed(title=f"{len(deleted_emojis_names)} emojis uploaded by {emoji_author} purged" if len(
                deleted_emojis_names) != 1 else f"{len(deleted_emojis_names)} emoji uploaded by {emoji_author} purged")
            purge_embed.colour = Colours.success
            purge_embed.add_field(name="Deleted emojis",
                                  value=", ".join(deleted_emojis_names) if len(deleted_emojis_names) != 0 else "None")
            purge_embed.set_author(name=ctx.message.author.display_name, icon_url=ctx.message.author.avatar_url)
            purge_embed.set_footer(text=invite_message, icon_url=self.bot.user.avatar_url)
            await ctx.channel.send(embed=purge_embed)

    @commands.command(name="rolelock",
                      description="Lock an emoji so that it can only be used by users with a certain role.",
                      usage=">rolelock [add/remove] [:emoji:] [@role]",
                      aliases=["lock", "rl"],
                      pass_context=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_emojis=True, manage_roles=True)
    async def role_lock(self, ctx, option: str, emoji: discord.Emoji, role: discord.Role):
        """Lock an emoji to a role."""

        # no emoji
        if emoji.guild != ctx.message.guild: raise CustomCommandError("Couldn't find that emoji in this server.")

        original_roles = emoji.roles

        role_lock_embed = discord.Embed(title=f"Emoji role lock: `:{emoji.name}:`", colour=Colours.success)

        # remove a rolelock
        if option.lower() in ["d", "r", "-", "remove", "del", "delete"]:
            if role in original_roles:
                original_roles.remove(role)
            else:
                raise CustomCommandError("There's no role lock in place for that role."
                                         " If you meant to add a lock, use >rolelock add.")

            role_lock_embed.add_field(name="Removed lock", value=f"You removed the lock for `@{role.name}`. You can view the"
                                                                 f" remaining role locks with `>locks`.")

        # add a rolelock
        elif option.lower() in ["a", "add", "append", "new", "+"]:
            if role not in original_roles:
                original_roles.append(role)
            else:
                raise CustomCommandError("There's already a role lock in place for that role.")
            role_lock_embed.add_field(name="Added lock", value=f"Now **only** users with the `@{role.name}` role can use this"
                                                               f" emoji.")

        else:
            raise CustomCommandError(f"Invalid option \"{option}\". Acceptable options are: add, remove.")

        role_lock_embed.set_thumbnail(url=emoji.url)

        # edit emoji
        await emoji.edit(roles=original_roles)

        # send embed
        await ctx.message.channel.send(embed=role_lock_embed)

    @commands.command(name="rolelocks",
                      description="View a list of role locks in place for an emoji.",
                      usage=">rolelocks [:emoji:]",
                      aliases=["locks", "rls"],
                      pass_context=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_emojis=True, manage_roles=True)
    async def view_role_locks(self, ctx, emoji: discord.Emoji):
        """View the current role locks on an emoji."""
        if emoji.guild != ctx.message.guild: raise CustomCommandError("Couldn't find that emoji in this server.")

        role_lock_list_embed = discord.Embed(title=f"Role locks for `:{emoji.name}:`", colour=Colours.base)
        role_lock_list_embed.set_thumbnail(url=emoji.url)
        role_lock_list_embed.add_field(name="Role locks", value=f"Only users with one of the following roles can use this emoji:"
                                                                f"\n`{'`, `'.join([role.name for role in emoji.roles])}`" if
                                       len(emoji.roles) > 0 else "None -- everybody can use this emoji.")

        await ctx.message.channel.send(embed=role_lock_list_embed)


def setup(bot):
    bot.add_cog(Management(bot))
