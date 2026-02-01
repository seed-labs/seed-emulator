import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("MIMO_API_KEY")
if not api_key:
    print("Error: MIMO_API_KEY environment variable is not set.")
    sys.exit(1)

print(f"Using API Key: {api_key[:4]}...{api_key[-4:]}")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.xiaomimimo.com/v1"
)

try:
    print("Testing OpenAI API connectivity...")
    completion = client.chat.completions.create(
        model="mimo-v2-flash",
        messages=[
            {
                "role": "system",
                "content": "You are MiMo, an AI assistant developed by Xiaomi."
            },
            {
                "role": "user",
                "content": "please introduce yourself"
            }
        ],
        max_completion_tokens=1024,
        temperature=0.3,
        top_p=0.95,
        stream=False
    )
    print("Success! Response:")
    print(completion.choices[0].message.content)

except Exception as e:
    print(f"Error calling API: {e}")
    sys.exit(1)
