import discord
import requests
import os

from dotenv import load_dotenv

load_dotenv()  

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Important to read messages!
BOT_TOKEN = os.getenv("BOT_TOKEN")


#connection to discord bot that listens for messages or actions
client = discord.Client(intents=intents)



@client.event
async def on_ready():
    print(f'Bot is online as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    print(f"📨 Received message in #{message.channel.name}: {message.content}")
    await message.channel.send(f"hello {message.author.name} i have received your message")

    # Send message to your app's backend
    payload = {
        "author": str(message.author),
        "content": message.content,
        "channel": str(message.channel),
    }
    print(f"📨 Received message in #{message.channel.name}: {message.content}")
    # requests.post("http://localhost:8000/api/receive-discord-message", json=payload)
    
    print(f"message sent to the channel")
    
@client.event
async def on_typing(channel,user,when):
     
    await channel.send(f"type fast bro. you taking a lot of time {user.name}")
    
@client.event
async def on_message_delete(message):
    await message.channel.send(f"{message.author} just deleted {message.content} 😂 😂 🤣")
    print("delete message sent")

@client.event
async def on_error(event, *args, **kwargs):
    print(f"⚠️There was some upforseen Error in event: {event}")
    
    
async def start_discord_bot():
    await client.start(BOT_TOKEN)
