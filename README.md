# Discord Bot

A Python bot built with discord.py featuring role management, music playback, and moderation.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> **Music playback also requires FFmpeg.**
> - **Windows:** Download from https://ffmpeg.org/download.html and add to PATH
> - **macOS:** `brew install ffmpeg`
> - **Linux:** `sudo apt install ffmpeg`

### 2. Create a Discord application

1. Go to https://discord.com/developers/applications
2. Click **New Application** → give it a name
3. Go to **Bot** → click **Add Bot**
4. Under **Privileged Gateway Intents**, enable:
   - **Server Members Intent**
   - **Message Content Intent**
5. Copy the **Token**

### 3. Configure the bot

```bash
cp .env.example .env
# then edit .env and paste your token
```

### 4. Invite the bot to your server

In the Developer Portal go to **OAuth2 → URL Generator**:
- Scopes: `bot`
- Bot Permissions: `Administrator` (or choose granularly)

Open the generated URL and add the bot to your server.

### 5. Run

```bash
python bot.py
```

---

## Commands

### 🎵 Music

| Command | Description |
|---|---|
| `!play <song/URL>` | Play a song or add to queue |
| `!pause` | Pause playback |
| `!resume` | Resume playback |
| `!skip` | Skip the current song |
| `!stop` | Stop and clear queue |
| `!queue` | Show the queue |
| `!np` | Show what's playing |
| `!volume <0-100>` | Set volume |
| `!loop` | Toggle song loop |
| `!remove <#>` | Remove from queue |
| `!join` / `!leave` | Join / leave voice |

### 🎭 Roles

| Command | Description |
|---|---|
| `!giverole @user Role` | Give a role (mod) |
| `!takerole @user Role` | Remove a role (mod) |
| `!createrole Role` | Create a role (mod) |
| `!delrole Role` | Delete a role (mod) |
| `!roles` | List all roles |
| `!myroles` | Your current roles |
| `!iam Role` | Self-assign a role |

### 🔨 Moderation

| Command | Description |
|---|---|
| `!kick @user [reason]` | Kick a member |
| `!ban @user [reason]` | Ban a member |
| `!unban User#1234` | Unban a user |
| `!timeout @user 10m` | Timeout (s/m/h/d) |
| `!untimeout @user` | Remove timeout |
| `!warn @user [reason]` | Warn via DM |
| `!purge <n>` | Delete N messages |
| `!slowmode <seconds>` | Set slowmode |
| `!lock` / `!unlock` | Lock/unlock channel |
| `!serverinfo` | Server info |
| `!userinfo [@user]` | User info |

---

## Adding More Commands

Each feature lives in its own file in `cogs/`. To add a new cog:

1. Create `cogs/mycog.py`:

```python
import discord
from discord.ext import commands

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="hello")
    async def hello(self, ctx):
        await ctx.send("Hello!")

async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

2. Add one line to `bot.py` in the `main()` function:

```python
await bot.load_extension("cogs.mycog")
```

That's it!
