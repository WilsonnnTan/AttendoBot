import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from utils.GoogleForm import get_ids, get_GForm_data, POST_Request_to_GForm, extract_google_form_url
from utils.database import check_hadir


load_dotenv(override=True)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_FORM_VIEW_URL, GOOGLE_FORM_POST_URL = extract_google_form_url(os.getenv("GOOGLE_FORM_URL"))

# Get Entry ID of each field from GOOGLE FORM
entry_IDs = list(get_ids(get_GForm_data(GOOGLE_FORM_VIEW_URL)))

# Enable message content intent
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance with prefix and intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Event: Bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def hadir(ctx):
    user = ctx.author
    user_data = {}
    if entry_IDs[0] not in user_data:
        user_data["entry." + str(entry_IDs[0])] = user.display_name
    
    if check_hadir(user.id):
        POST_Request_to_GForm(GOOGLE_FORM_POST_URL, user_data)
        await ctx.send(f"{user.mention} hadir! ✅")

# Run the bot
bot.run(DISCORD_TOKEN)