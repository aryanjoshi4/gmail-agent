from dotenv import load_dotenv
import os
import openai
load_dotenv()
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
 
openai.api_key = os.getenv("OPENAI_API_KEY")



