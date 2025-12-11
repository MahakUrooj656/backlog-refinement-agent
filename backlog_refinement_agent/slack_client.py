from typing import Union
import json
import requests
from .config import settings



def post_summary_to_slack(message: str):
    payload = {
        "text": message
    }
    try:
        response = requests.post(settings.slack.webhook_url, json=payload)
        response.raise_for_status()
        print("Slack webhook message posted successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message to Slack via webhook: {e}")
