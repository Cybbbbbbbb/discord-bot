import discord
from discord.ext import commands
from datetime import timedelta
import re


def parse_duration(text: str) -> timedelta | None:
    """Parse '10m', '2h', '1d' etc. into a timedelta."""
    match = re.fullmatch(r"(\d+)([smhd])", text.strip().lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    return {
        "s": timedelta(seconds=value),
        "m": timedelta(minutes=value),
        "h": timedelta(hours=value),
        "d": timedelta(days=value),
    }[unit]


class Moderation(commands.Cog):
    """Moderation commands."""

    def __init__(self, bot):
        self.bot = bot

    # ── Commands ──────────────────────────────────────────────────────────────

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason given"):
        """Kick a member.  Usage: !kick @user [reason]"""
        await member.kick(reason=reason)
        await ctx.send(f"👢 **{member}** was kicked. Reason: {reason}")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason given"):
        """Ban a member.  Usage: !ban @user [reason]"""
        await member.ban(reason=reason)
        await ctx.send(f"🔨 **{member}** was banned. Reason: {reason}")

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, user_tag: str):
        """Unban a user by tag (e.g. User#1234).  Usage: !unban User#1234"""
        banned = [entry async for entry in ctx.guild.bans()]
        name, _, discriminator = user_tag.partition("#")
        for entry in banned:
            if entry.user.name == name and (not discriminator or entry.user.discriminator == discriminator):
                await ctx.guild.unban(entry.user)
                await ctx.send(f"✅ **{entry.user}** has been unbanned.")
                return
        await ctx.send(f"❌ No banned user matching **{user_tag}** found.")

    @commands.command(name="timeout", aliases=["mute"])
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: str, *, reason: str = "No reason given"):
        """Timeout a member.  Usage: !timeout @user 10m [reason]  (s/m/h/d)"""
        delta = parse_duration(duration)
        if delta is None:
            await ctx.send("❌ Invalid duration. Use formats like `10m`, `2h`, `1d`.")
            return
        await member.timeout(delta, reason=reason)
        await ctx.send(f"🔇 **{member}** timed out for **{duration}**. Reason: {reason}")

    @commands.command(name="untimeout", aliases=["unmute"])
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member):
        """Remove a timeout.  Usage: !untimeout @user"""
        await member.timeout(None)
        await ctx.send(f"🔊 Removed timeout from **{member}**.")

    @commands.command(name="purge", aliases=["clear"])
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Delete N messages.  Usage: !purge 10"""
        if amount < 1 or amount > 200:
            await ctx.send("❌ Amount must be between 1 and 200.")
            return
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 includes the command message
        msg = await ctx.send(f"🗑️ Deleted **{len(deleted) - 1}** messages.")
        await msg.delete(delay=4)

    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        """Set channel slowmode.  Usage: !slowmode 5  (0 to disable)"""
        if seconds < 0 or seconds > 21600:
            await ctx.send("❌ Value must be between 0 and 21600 seconds.")
            return
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send("✅ Slowmode disabled.")
        else:
            await ctx.send(f"🐢 Slowmode set to **{seconds}s**.")

    @commands.command(name="warn")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason given"):
        """DM-warn a member.  Usage: !warn @user [reason]"""
        try:
            await member.send(
                f"⚠️ You have been warned in **{ctx.guild.name}**.\n"
                f"**Reason:** {reason}"
            )
            await ctx.send(f"⚠️ {member.mention} has been warned. (DM sent)")
        except discord.Forbidden:
            await ctx.send(f"⚠️ {member.mention} warned (couldn't DM — DMs are closed).")

    @commands.command(name="serverinfo")
    async def server_info(self, ctx):
        """Show server information."""
        g = ctx.guild
        embed = discord.Embed(title=g.name, color=discord.Color.blurple())
        embed.set_thumbnail(url=g.icon.url if g.icon else None)
        embed.add_field(name="Owner", value=g.owner.mention)
        embed.add_field(name="Members", value=g.member_count)
        embed.add_field(name="Channels", value=len(g.channels))
        embed.add_field(name="Roles", value=len(g.roles))
        embed.add_field(name="Created", value=discord.utils.format_dt(g.created_at, "D"))
        await ctx.send(embed=embed)

    @commands.command(name="userinfo")
    async def user_info(self, ctx, member: discord.Member = None):
        """Show info about a user.  Usage: !userinfo [@user]"""
        member = member or ctx.author
        embed = discord.Embed(title=str(member), color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Joined server", value=discord.utils.format_dt(member.joined_at, "D"))
        embed.add_field(name="Account created", value=discord.utils.format_dt(member.created_at, "D"))
        top_role = member.top_role.mention if member.top_role.name != "@everyone" else "None"
        embed.add_field(name="Top role", value=top_role)
        await ctx.send(embed=embed)

    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        """Lock the current channel (deny @everyone from sending)."""
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send("🔒 Channel locked.")

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        """Unlock the current channel."""
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send("🔓 Channel unlocked.")

    @commands.command(name="dm")
    async def dm(self, ctx, member: discord.Member, *, message: str):
        """DM a server member.  Usage: !dm @user your message here"""
        try:
            await member.send(f"📩 **Message from {ctx.author.display_name} in {ctx.guild.name}:**\n{message}")
            await ctx.send(f"✅ DM sent to {member.mention}.")
        except discord.Forbidden:
            await ctx.send(f"❌ Couldn't DM {member.mention} — they probably have DMs turned off.")


async def setup(bot):
    await bot.add_cog(Moderation(bot))
