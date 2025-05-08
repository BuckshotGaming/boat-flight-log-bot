
import discord
from discord.ext import commands
import json
import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
ACCESS_KEY = os.environ.get("ACCESS_KEY")
CONFIG_FILE = "config.json"
log_channel_id = None

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Load config on startup
def load_config():
    global log_channel_id
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            log_channel_id = data.get("log_channel_id")

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump({"log_channel_id": log_channel_id}, f)

@bot.event
async def on_ready():
    load_config()
    print(f"✅ Bot is online as {bot.user}")
    threading.Thread(target=run_http_server, daemon=True).start()

@bot.command()
async def setchannel(ctx):
    global log_channel_id
    log_channel_id = ctx.channel.id
    save_config()
    await ctx.send(f"✅ Log channel set to {ctx.channel.mention}")

@bot.command()
async def testlog(ctx):
    if log_channel_id is None:
        await ctx.send("❗ Log channel not set. Use !setchannel first.")
        return

    channel = bot.get_channel(log_channel_id)
    embed = discord.Embed(title="✈️ Test Flight Log", color=0x00ff00)
    embed.add_field(name="Pilot", value=ctx.author.display_name, inline=True)
    embed.add_field(name="Aircraft", value="Cessna 172", inline=True)
    embed.add_field(name="Departure", value="CYVR", inline=True)
    embed.add_field(name="Arrival", value="KLAX", inline=True)
    embed.add_field(name="Duration", value="2h 35m", inline=True)
    await channel.send(embed=embed)

async def post_flight_log(data):
    if log_channel_id is None:
        print("❗ Log channel not set.")
        return
    channel = bot.get_channel(log_channel_id)
    if not channel:
        print("❗ Channel not found.")
        return

    embed = discord.Embed(title="✈️ Flight Completed!", color=0x00ff00)
    embed.add_field(name="Pilot", value=data.get("pilot", "Unknown"), inline=True)
    embed.add_field(name="Aircraft", value=data.get("aircraft", "Unknown"), inline=True)
    embed.add_field(name="Departure", value=data.get("departure", "???"), inline=True)
    embed.add_field(name="Arrival", value=data.get("arrival", "???"), inline=True)
    embed.add_field(name="Duration", value=data.get("duration", "??"), inline=True)
    embed.set_footer(text="Logged by Boat Flight Log Bot")
    await channel.send(embed=embed)

class LogRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/log":
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                if data.get("access_key") != ACCESS_KEY:
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b"Forbidden")
                    return
                asyncio.run_coroutine_threadsafe(post_flight_log(data), bot.loop)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Log received")
            except Exception as e:
                print("❗ Error:", e)
                self.send_response(400)
                self.end_headers()

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('', port), LogRequestHandler)
    print(f"🌐 Listening on port {port} for /log")
    server.serve_forever()

bot.run(TOKEN)
