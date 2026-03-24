import os
import boto3
from dotenv import load_dotenv

load_dotenv()

client = boto3.client(
    "bedrock-runtime",
    region_name=os.getenv("AWS_REGION"),
)

response = client.converse(
    modelId="global.amazon.nova-2-lite-v1:0",
    messages=[
        {
            "role": "user",
            "content": [{"text": "Say hello in one short sentence."}],
        }
    ],
)

print(response["output"]["message"]["content"][0]["text"])
