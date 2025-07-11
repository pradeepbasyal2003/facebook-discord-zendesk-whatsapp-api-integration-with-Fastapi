import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
CHANNEL_ID = "C092SJS9G9L"

# Initialize client
client = WebClient(token=SLACK_BOT_TOKEN)

def test_auth():
    """Test if the bot token works"""
    try:
        response = client.auth_test()
        print("✅ Auth Test Passed")
        print(f"Bot user: {response['user']}, Team: {response['team']}")
    except SlackApiError as e:
        print(f"❌ Auth Test Failed: {e.response['error']}")

def list_channels():
    """List all public channels"""
    try:
        response = client.conversations_list()
        print("✅ Channels:")
        for channel in response['channels']:
            print(f"- {channel['name']} (ID: {channel['id']})")
    except SlackApiError as e:
        print(f"❌ Failed to list channels: {e.response['error']}")

def send_message():
    """Send a message to a channel"""
    try:
        response = client.chat_postMessage(
            channel=CHANNEL_ID,
            text="Hello from Slack bot via Web API 👋"
        )
        print("✅ Message sent")
    except SlackApiError as e:
        print(f"❌ Failed to send message: {e.response['error']}")

if __name__ == "__main__":
    test_auth()
    list_channels()
    send_message()
