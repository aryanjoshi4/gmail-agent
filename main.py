from dotenv import load_dotenv
import os
from openai import OpenAI
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
MAX_EMAILS = 200; 

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def gmail_authenticate (): 
    email_tag = input("Enter an identifier for this Gmail account (e.g., personal, school, work): ").strip().lower()
    token_file = f"token_{email_tag}.json" 

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def get_messages(service, num_messages):
    results = service.users().messages().list(
        userId="me", labelIds=["INBOX"], maxResults=num_messages
    ).execute()
    return results.get("messages", [])

def classify_email(subject, snippet):
    prompt = (
        "Classify this email as Work, School, or Personal.\n"
        f"Subject: {subject}\nBody: {snippet}\n\n"
        "Respond with only one word: Work, School, or Personal."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        category = response.choices[0].message.content.strip().capitalize()
        return category
    
    except Exception as e:
        print(f"⚠️  OpenAI API error: {e}")
        return "Unclassified"

def get_or_create_label(service, label_name):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"].lower() == label_name.lower():
            return label["id"]

    new_label = service.users().labels().create(
        userId="me", body={"name": label_name}
    ).execute()
    return new_label["id"]

def apply_label(service, msg_id, label_id):
    service.users().messages().modify(
        userId="me", id=msg_id, body={"addLabelIds": [label_id]}
    ).execute()


def main():
    """Main program to authenticate, fetch, classify, and label emails."""
    print("Authenticating with Gmail...")
    service = gmail_authenticate()

    try:
        n = int(input(f"How many recent emails to sort? (1–{MAX_EMAILS}): "))
    except ValueError:
        n = 10
    n = min(max(n, 1), MAX_EMAILS)

    messages = get_messages(service, n)
    if not messages:
        print("No emails found.")
        return

    label_ids = {name: get_or_create_label(service, name) for name in ["Work", "School", "Personal"]}
    counts = {name: 0 for name in label_ids}

    print(f"\nSorting {len(messages)} emails...\n")

    for msg in messages:
        data = service.users().messages().get(userId="me", id=msg["id"]).execute()
        headers = data["payload"]["headers"]

        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(No Subject)")
        snippet = data.get("snippet", "")

        category = classify_email(subject, snippet)

        if category in label_ids:
            apply_label(service, msg["id"], label_ids[category])
            counts[category] += 1
            print(f"✉️  {subject[:60]}... → {category}")
        else:
            print(f"⚠️  Could not classify: {subject}")

    print("\nSummary:")
    for k, v in counts.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
