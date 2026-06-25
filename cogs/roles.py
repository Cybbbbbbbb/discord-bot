import discord
from discord.ext import commands


class Roles(commands.Cog):
    """Role management commands."""

    def __init__(self, bot):
        self.bot = bot

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _get_or_create_role(self, guild: discord.Guild, name: str, **kwargs) -> discord.Role:
        role = discord.utils.get(guild.roles, name=name)
        if role is None:
            role = await guild.create_role(name=name, **kwargs)
        return role

    # ── Commands ─────────────────────────────────────────────────────────────

    @commands.command(name="giverole", aliases=["gr"])
    @commands.has_permissions(manage_roles=True)
    async def give_role(self, ctx, member: discord.Member, *, role_name: str):
        """Give a role to a member.  Usage: !giverole @user RoleName"""
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role is None:
            await ctx.send(f"❌ Role **{role_name}** not found. Create it first or check the name.")
            return
        if role in member.roles:
            await ctx.send(f"ℹ️ {member.mention} already has **{role_name}**.")
            return
        await member.add_roles(role)
        await ctx.send(f"✅ Gave **{role_name}** to {member.mention}.")

    @commands.command(name="takerole", aliases=["tr"])
    @commands.has_permissions(manage_roles=True)
    async def take_role(self, ctx, member: discord.Member, *, role_name: str):
        """Remove a role from a member.  Usage: !takerole @user RoleName"""
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role is None:
            await ctx.send(f"❌ Role **{role_name}** not found.")
            return
        if role not in member.roles:
            await ctx.send(f"ℹ️ {member.mention} doesn't have **{role_name}**.")
            return
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed **{role_name}** from {member.mention}.")

    @commands.command(name="createrole", aliases=["cr"])
    @commands.has_permissions(manage_roles=True)
    async def create_role(self, ctx, *, role_name: str):
        """Create a new role.  Usage: !createrole RoleName"""
        existing = discord.utils.get(ctx.guild.roles, name=role_name)
        if existing:
            await ctx.send(f"ℹ️ Role **{role_name}** already exists.")
            return
        role = await ctx.guild.create_role(name=role_name)
        await ctx.send(f"✅ Created role **{role.name}**.")

    @commands.command(name="delrole", aliases=["dr"])
    @commands.has_permissions(manage_roles=True)
    async def delete_role(self, ctx, *, role_name: str):
        """Delete a role.  Usage: !delrole RoleName"""
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role is None:
            await ctx.send(f"❌ Role **{role_name}** not found.")
            return
        await role.delete()
        await ctx.send(f"🗑️ Deleted role **{role_name}**.")

    @commands.command(name="roles")
    async def list_roles(self, ctx):
        """List all roles in the server."""
        roles = [r.mention for r in reversed(ctx.guild.roles) if r.name != "@everyone"]
        if not roles:
            await ctx.send("No roles found.")
            return
        embed = discord.Embed(
            title=f"Roles in {ctx.guild.name}",
            description="\n".join(roles),
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    @commands.command(name="myroles")
    async def my_roles(self, ctx):
        """Show your current roles."""
        roles = [r.mention for r in ctx.author.roles if r.name != "@everyone"]
        embed = discord.Embed(
            title=f"Roles for {ctx.author.display_name}",
            description="\n".join(roles) if roles else "None",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # ── Self-assign roles (reaction / command based) ─────────────────────────

    @commands.command(name="iam")
    async def self_assign(self, ctx, *, role_name: str):
        """Self-assign a role (if it's allowed).  Usage: !iam RoleName
        
        Admins: add the role name to SELF_ASSIGN_ROLES in this file to allow it.
        """
        SELF_ASSIGN_ROLES = ["Gaming", "Music", "Art", "Announcements"]  # edit freely

        if role_name not in SELF_ASSIGN_ROLES:
            await ctx.send(
                f"❌ **{role_name}** isn't self-assignable. "
                f"Available: {', '.join(SELF_ASSIGN_ROLES)}"
            )
            return
        role = await self._get_or_create_role(ctx.guild, role_name, mentionable=True)
        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
            await ctx.send(f"✅ Removed **{role_name}** from you.")
        else:
            await ctx.author.add_roles(role)
            await ctx.send(f"✅ Gave you **{role_name}**.")


async def setup(bot):
    await bot.add_cog(Roles(bot))
