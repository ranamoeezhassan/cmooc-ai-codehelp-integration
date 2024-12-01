"""
name: connectAPI.py

description: TODO

Rana Moeez Hassan
Winter 2024
"""

import requests
import jwt
from datetime import datetime, timezone
import os
from dotenv import find_dotenv, load_dotenv

def main():
    load_dotenv(find_dotenv())
    dartmouth_api_key = os.environ["DARTMOUTH_API_KEY"]

    resp = requests.post("https://api.dartmouth.edu/api/jwt", headers={"Authorization": dartmouth_api_key})
    print(f'JSON that we get: {resp.json()}\n\n')

    # Our JWT token
    token = resp.json()["jwt"]

    # # Decode the JWT without verification to check the payload
    decoded = jwt.decode(token, options={"verify_signature": False})
    print(f"Decoded JWT: {decoded}\n\n")
    exp_timestamp = decoded["exp"] 
    exp_time = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

    print("Expiration Time:", exp_time)
    # Will be useful in the jupyter notebook
    print("Is token expired?", exp_time < datetime.now(timezone.utc))

if __name__ == "__main__":
    main() 