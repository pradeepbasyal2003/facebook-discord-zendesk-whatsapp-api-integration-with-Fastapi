from google_auth_oauthlib.flow import Flow
import os

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # for local dev only
TOKEN_FILE = "token.json"

CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
REDIRECT_URI = 'http://localhost:8000/auth/callback'

flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)

def get_auth_url():
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    return auth_url

def fetch_token(code):
    flow.fetch_token(code=code)
    creds = flow.credentials
    with open(TOKEN_FILE, "w") as token:
        token.write(creds.to_json())

    return creds
