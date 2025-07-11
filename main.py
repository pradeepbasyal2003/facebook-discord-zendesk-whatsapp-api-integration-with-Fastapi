from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from gmail_auth import get_auth_url, fetch_token
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import requests,asyncio,os,logging,httpx
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from discord_bot import start_discord_bot
load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()
user_credentials = {}



#for facebook and whatsapp
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID" )

""" 
tokens from env for zendesk

"""
ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL")
ZENDESK_API_TOKEN = os.getenv("ZENDESK_API_TOKEN")
ZENDESK_DOMAIN = os.getenv("ZENDESK_DOMAIN")
ZENDESK_CUSTOM_FIELD_USER_PHONE_NUMBER = os.getenv("ZENDESK_CUSTOM_FIELD_USER_PHONE_NUMBER")


""" 
tokens from evn for slack
"""
SLACK_VERIFICATION_TOKEN = os.getenv("SLACK_VERIFICATION_TOKEN")
APP_TOKEN =os.getenv("APP_TOKEN")
SLACK_SIGINING_SECRET = os.getenv('SLACK_SIGINING_SECRET')
SLACK_API_URL = "https://slack.com/api"
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
# print(SLACK_BOT_TOKEN)

##startup discord bot when the app starts
@app.on_event("startup")
async def startup_event():
    # Start Discord bot in background task
    asyncio.create_task(start_discord_bot())

@app.get("/webhook/meta")
async def verify_fb_token(request: Request):
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params["hub.challenge"])
    return "Verification failed"

@app.post("/webhook/meta")
async def receive_message(request:Request):
    data = await request.json()   
    logger.info("message received",data)
    if data.get("object") == "page":     
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if "message" in messaging_event:
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"].get("text", "")

                    
                    reply_text = f"you sent: {message_text}"

                    # Send reply
                    send_facebook_message(sender_id, reply_text)

        return {"status": "ok"}
    
    elif data.get("object") == "whatsapp_business_account":
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                if messages:
                    for message in messages:
                        from_number = message["from"]
                        msg_text = message["text"]["body"]
                        reply_text = f"you said: {msg_text}"
                        subject = f"Ticket request from {from_number}"
                        logger.info(f"user number = {from_number}")
                        await create_zendesk_ticket(subject,msg_text,from_number)
                        # send_whatsapp_message(from_number, reply_text)   #this is used to send the use a message back
                     
                        
                        

def send_facebook_message(recipient_id, text):
    url = f"https://graph.facebook.com/v17.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    print("Sent:", response.text)    
    
    
    
async def send_whatsapp_message(to, message):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        logger.info("📤 WhatsApp API response: %s - %s", response.status_code, response.text)




#zendesk api integration
async def create_zendesk_ticket(subject, message, user_id):
    auth = (f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN)
    headers = {"Content-Type": "application/json"}
    payload = {
        "ticket": {
            "subject": subject,
            "comment": {
                "body": message
            },
            "custom_fields": [
                {
                    "id": ZENDESK_CUSTOM_FIELD_USER_PHONE_NUMBER,
                    "value": str(user_id)
                }
            ],
            "tags": ["whatsapp"]
        }
    }
    logger.info(f"payload for creating ticket : {payload}")
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://{ZENDESK_DOMAIN}.zendesk.com/api/v2/tickets.json",
            auth=auth,
            headers=headers,
            json=payload
        )


@app.post("/webhook/zendesk")
async def zendesk_webhook(request: Request):
    payload = await request.json()
    logging.info(f"Zendesk webhook payload: {payload}")

    try:
        event_type = payload.get("type")
        detail = payload.get("detail", {})
        comment_data = payload.get("event", {}).get("comment", {})

        if event_type == "zen:event-type:ticket.comment_added":
            is_public = comment_data.get("is_public", False)

            # Only handle public agent replies
            if is_public:
                message_text = comment_data.get("body", "")
                custom_fields = detail.get("custom_fields", [])
                user_number = None

                for field in custom_fields:
                    if field["id"] == ZENDESK_CUSTOM_FIELD_USER_PHONE_NUMBER:
                        user_number = field["value"]
                        break

                if not user_number:
                    return {"error": "Phone number not found"}
                logger.info("sending message to whatsapp back")
                await send_whatsapp_message(user_number, message_text)
                return {"status": "message_sent"}

        return {"status": "ignored"}

    except Exception as e:
        logging.exception("Error processing Zendesk webhook")
        return {"error": str(e)}
    
@app.get("/tickets")
async def get_tickets():
    url = f"https://{ZENDESK_DOMAIN}.zendesk.com/api/v2/tickets.json"
    auth = HTTPBasicAuth(f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN)

    while url:
        response = requests.get(url, auth=auth)
        if response.status_code != 200:
            print(f"Error fetching tickets: {response.status_code} - {response.text}")
            break

        data = response.json()
        tickets = data.get("tickets", [])
        for ticket in tickets:
            print(f"ID: {ticket['id']} | Subject: {ticket['subject']} | Status: {ticket['status']}")
        url = data.get("next_page")
        return {"tickets":tickets}
        # Pagination: get the next page, if available
        

@app.get("/tickets/{ticket_id}")
async def get_ticket_by_id(ticket_id:int):
    url = f"https://{ZENDESK_DOMAIN}.zendesk.com/api/v2/tickets/{ticket_id}.json"
    auth = HTTPBasicAuth(f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN)
    
    while url:
        response = requests.get(url, auth=auth)
        if response.status_code != 200:
            print(f"Error fetching tickets: {response.status_code} - {response.text}")
            break

        ticket = response.json()
        
        return  ticket.get("ticket",{})      

#for discord

@app.post("/api/receive-discord-message")
async def receive_discord_message(request: Request):
    data = await request.json()
    print("Received from Discord:", data)
    
    return {"status": "ok"}





#for slack
slack_headers = {
    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    "Content-Type": "application/json"
}

async def send_message(channel: str, text: str):
    async with httpx.AsyncClient() as client:
        return await client.post(f"{SLACK_API_URL}/chat.postMessage", json={
            "channel": channel,
            "text": text
        }, headers=slack_headers)
        
        
@app.get("/channels")
async def api_get_channels():
    async with httpx.AsyncClient() as client:
        print("SLACK_BOT_TOKEN:", SLACK_BOT_TOKEN)
        res = await client.get(f"{SLACK_API_URL}/conversations.list", headers=slack_headers)
        print("Slack response status:", res.status_code)
        print("Slack raw response text:", res.text)

        try:
            data = res.json()
        except Exception as e:
            print("Failed to decode JSON:", e)
            return {"error": "Invalid JSON from Slack"}

        if not data.get("ok"):
            print("Slack API error:", data.get("error"))
            return {"error": data.get("error")}

        return {"channels": data.get("channels", [])}
    
    
    
##
## Gmail OAuth2 Authentication and read mails
##

@app.get("/auth/login")
def login():
    url = get_auth_url()
    return RedirectResponse(url)

@app.get("/auth/callback")
def callback(request: Request):
    code = request.query_params.get("code")
    creds = fetch_token(code)
    user_credentials["token"] = creds
    return {"message": "Authorization successful!"}

@app.get("/gmail/messages")
def list_messages():
    
    creds = Credentials.from_authorized_user_file("token.json")
    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(userId='me',).execute()
    messages = results.get("messages", [])
    return {"messages": messages}


@app.get("/gmail/messages/{message_id}")
def get_message(message_id:str):
    creds = Credentials.from_authorized_user_file("token.json")
    if not creds:
        return {"error": "User not authenticated"}
    
    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().get(userId="me",id=message_id).execute()
    return {"message": results}     