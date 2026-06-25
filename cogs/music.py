import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
from collections import deque

YTDL_SEARCH_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "extract_flat": True,
    "source_address": "0.0.0.0",
}

YTDL_STREAM_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

ytdl_search = yt_dlp.YoutubeDL(YTDL_SEARCH_OPTIONS)
ytdl_stream = yt_dlp.YoutubeDL(YTDL_STREAM_OPTIONS)


class Track:
    def __init__(self, source_url: str, title: str, webpage_url: str, requester: discord.Member):
        self.source_url = source_url
        self.title = title
        self.webpage_url = webpage_url
        self.requester = requester

    @classmethod
    async def from_url(cls, url: str, requester: discord.Member, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: ytdl_stream.extract_info(url, download=False)
        )
        if "entries" in data:
            data = data["entries"][0]
        return cls(
            source_url=data["url"],
            title=data.get("title", "Unknown"),
            webpage_url=data.get("webpage_url", url),
            requester=requester,
        )


class GuildPlayer:
    def __init__(self):
        self.queue: deque[Track] = deque()
        self.current: Track | None = None
        self.loop: bool = False
        self.volume: float = 0.5


class SearchView(discord.ui.View):
    """Buttons for picking a search result."""

    def __init__(self, results: list[dict], requester: discord.Member, cog):
        super().__init__(timeout=30)
        self.results = results
        self.requester = requester
        self.cog = cog
        self.chosen: dict | None = None

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        for i, entry in enumerate(results[:5]):
            btn = discord.ui.Button(
                label=entry["title"][:60],
                emoji=emojis[i],
                style=discord.ButtonStyle.secondary,
                custom_id=str(i)
            )
            btn.callback = self._make_callback(i)
            self.add_item(btn)

    def _make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.requester:
                await interaction.response.send_message("❌ Only the person who searched can pick.", ephemeral=True)
                return
            self.chosen = self.results[index]
            self.stop()
            await interaction.response.defer()
        return callback


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}

    def get_player(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer()
        return self.players[guild_id]

    def _play_next(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        vc = interaction.guild.voice_client

        if not vc or not vc.is_connected():
            return

        if player.loop and player.current:
            track = player.current
        elif player.queue:
            track = player.queue.popleft()
            player.current = track
        else:
            player.current = None
            asyncio.run_coroutine_threadsafe(
                interaction.channel.send("✅ Queue finished!"), self.bot.loop
            )
            return

        source = discord.FFmpegPCMAudio(track.source_url, **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=player.volume)
        vc.play(source, after=lambda e: self._play_next(interaction))

        asyncio.run_coroutine_threadsafe(
            interaction.channel.send(embed=self._now_playing_embed(track)), self.bot.loop
        )

    def _now_playing_embed(self, track: Track) -> discord.Embed:
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"[{track.title}]({track.webpage_url})",
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Requested by {track.requester.display_name}")
        return embed

    async def _play_track(self, interaction: discord.Interaction, url: str):
        """Fetch and play/queue a track by URL."""
        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
        elif vc.channel != interaction.user.voice.channel:
            await vc.move_to(interaction.user.voice.channel)

        track = await Track.from_url(url, interaction.user, loop=self.bot.loop)
        player = self.get_player(interaction.guild_id)

        if vc.is_playing() or vc.is_paused():
            player.queue.append(track)
            await interaction.channel.send(
                f"📋 Added to queue (position **{len(player.queue)}**): **{track.title}**"
            )
        else:
            player.current = track
            source = discord.FFmpegPCMAudio(track.source_url, **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=player.volume)
            vc.play(source, after=lambda e: self._play_next(interaction))
            await interaction.channel.send(embed=self._now_playing_embed(track))

    # ── Slash Commands ────────────────────────────────────────────────────────

    @app_commands.command(name="play", description="Search for a song and pick from results")
    @app_commands.describe(song="Song name or YouTube URL")
    async def play(self, interaction: discord.Interaction, song: str):
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Join a voice channel first.", ephemeral=True)
            return

        # If it's a direct URL, play immediately
        if song.startswith("http"):
            await interaction.response.defer()
            await self._play_track(interaction, song)
            return

        await interaction.response.defer()

        # Search YouTube for 5 results
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(
                None,
                lambda: ytdl_search.extract_info(f"ytsearch5:{song}", download=False)
            )
        except Exception:
            await interaction.followup.send("❌ Search failed. Try pasting a YouTube URL instead.")
            return

        entries = data.get("entries", [])
        if not entries:
            await interaction.followup.send("❌ No results found.")
            return

        # Clean up entries
        results = []
        for e in entries[:5]:
            url = e.get("url") or e.get("webpage_url", "")
            if not url.startswith("http"):
                url = f"https://www.youtube.com/watch?v={url}"
            results.append({"title": e.get("title", "Unknown")[:80], "url": url})

        # Build embed with results list
        lines = [f"{['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣'][i]} {r['title']}" for i, r in enumerate(results)]
        embed = discord.Embed(
            title=f"🔎 Results for: {song}",
            description="\n".join(lines),
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Pick a song below • expires in 30s")

        view = SearchView(results, interaction.user, self)
        msg = await interaction.followup.send(embed=embed, view=view)

        await view.wait()

        if view.chosen is None:
            await msg.edit(content="⏰ Search expired.", embed=None, view=None)
            return

        await msg.edit(content=f"✅ Selected: **{view.chosen['title']}**", embed=None, view=None)
        await self._play_track(interaction, view.chosen["url"])

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ Skipped.")
        else:
            await interaction.response.send_message("❌ Nothing to skip.", ephemeral=True)

    @app_commands.command(name="pause", description="Pause the current song")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Paused.")
        else:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)

    @app_commands.command(name="resume", description="Resume playback")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed.")
        else:
            await interaction.response.send_message("❌ Nothing is paused.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop playback and clear the queue")
    async def stop(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        player.queue.clear()
        player.current = None
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
        await interaction.response.send_message("⏹️ Stopped and queue cleared.")

    @app_commands.command(name="leave", description="Leave the voice channel")
    async def leave(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        player.queue.clear()
        player.current = None
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("👋 Left the voice channel.")
        else:
            await interaction.response.send_message("❌ I'm not in a voice channel.", ephemeral=True)

    @app_commands.command(name="queue", description="Show the current queue")
    async def show_queue(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if not player.current and not player.queue:
            await interaction.response.send_message("📋 Queue is empty.")
            return

        lines = []
        if player.current:
            lines.append(f"🎵 **Now playing:** [{player.current.title}]({player.current.webpage_url})")
        for i, track in enumerate(player.queue, 1):
            lines.append(f"`{i}.` [{track.title}]({track.webpage_url})")

        embed = discord.Embed(
            title="📋 Queue",
            description="\n".join(lines),
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Loop: {'on' if player.loop else 'off'} • Volume: {int(player.volume * 100)}%")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="np", description="Show what's currently playing")
    async def now_playing(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if player.current:
            await interaction.response.send_message(embed=self._now_playing_embed(player.current))
        else:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)

    @app_commands.command(name="volume", description="Set volume (0-100)")
    @app_commands.describe(level="Volume level between 0 and 100")
    async def volume(self, interaction: discord.Interaction, level: int):
        if not 0 <= level <= 100:
            await interaction.response.send_message("❌ Volume must be between 0 and 100.", ephemeral=True)
            return
        player = self.get_player(interaction.guild_id)
        player.volume = level / 100
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = player.volume
        await interaction.response.send_message(f"🔊 Volume set to **{level}%**.")

    @app_commands.command(name="loop", description="Toggle looping the current song")
    async def loop(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        player.loop = not player.loop
        state = "🔁 on" if player.loop else "➡️ off"
        await interaction.response.send_message(f"Loop is now **{state}**.")


async def setup(bot):
    await bot.add_cog(Music(bot))
