import json
import datetime
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    message = event['messages']
    bot_response_message = "Try again!"
    
    if message is not None or len(message) > 0:
        data = message[0]['unstructured']['text']
        client = boto3.client('lex-runtime')
        bot_response = client.post_text(botName='Dining', botAlias='Dining', userId='test', inputText= data)
        
        bot_response_message = bot_response['message']
        
    response = {
        'messages': [
            {
                "type":"unstructured",
                "unstructured": {
                    "id":"1",
                    "text": bot_response_message,
                    "timestamp": str(datetime.datetime.now().timestamp())
                }
            }
            ]
    }
    
    return response