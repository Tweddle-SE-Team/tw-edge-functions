from __future__ import print_function

import json
import logging
import re
import os

from datetime import datetime
from base64 import b64decode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

HOOK_URL = os.environ["SLACK_INCOMING_WEBHOOK"]

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    records = event['Records']
    attachments = []
    for record in records:
        subject = record['Sns']['Subject']
        message = json.loads(record['Sns']['Message'])
        eventType = message["eventType"]
        if eventType == "Bounce":
            event = message["bounce"]
            reason = event["bounceType"]
        elif eventType == "Complaint":
            event = message["complaint"]
            reason = event["complaintFeedbackType"]
        else:
            raise Exception("Neither bounce nor complaint")
        mail = message["mail"]
        timestamp = datetime.strptime(mail["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
        sourceMail = mail["source"]
        destinationMails = mail["destination"]
        attachments.append({
            "fallback": subject,
            "color": "#ff0000",
            "text": subject,
            "fields": [
                {
                    "title": "Type",
                    "value": eventType,
                    "short": True
                },
                {
                    "title": "Source",
                    "value": sourceMail,
                    "short": True
                },
                {
                    "title": "Destination",
                    "value": ",".join(destinationMails),
                    "short": True
                },
                {
                    "title": "Type",
                    "value": reason,
                    "short": True
                }
            ],
            "footer": "BlackSparkle",
            "footer_icon": "https://img.lovepik.com/element/40055/2358.png_1200.png",
            "ts": timestamp.timestamp()
        })

    slack_message = {
        "channel": "bounces-n-complaints",
        "username": "slackbot",
        "icon_emoji": ":female-farmer:",
        "attachments": attachments
    }

    req = Request(HOOK_URL, json.dumps(slack_message).encode('utf-8'))

    try:
        response = urlopen(req)
        response.read()
        logger.info("Message posted to %s", slack_message['channel'])
    except HTTPError as e:
        logger.error("Request failed: %d %s", e.code, e.reason)
    except URLError as e:
        logger.error("Server connection failed: %s", e.reason)
