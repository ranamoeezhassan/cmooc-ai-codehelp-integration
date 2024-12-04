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

    resp = sendInstructions("https://api.dartmouth.edu/api/jwt", dartmouth_api_key, None, None, None)

    # Our JWT token
    token = resp.json()["jwt"]

    if isTokenExpired(token, True):
        print("Token has expired. Please refresh the token.")
        exit()

    prompt, parameters = generateInstructions("How do you define a class in Python?", None)
    resp = sendInstructions("https://api.dartmouth.edu/api/ai/tgi/codellama-13b-instruct-hf/generate", None, token, prompt, parameters)
    # resp = sendInstructions("https://api.dartmouth.edu/api/ai/tgi/llama-3-8b-instruct/generate", None, token, prompt, parameters)
    json_resp = resp.json()
    print(f"GENERATED TEXT: {json_resp['generated_text']}")

    

def isTokenExpired(token, verbose):
    # Decode the JWT without verification to check the payload
    decoded = jwt.decode(token, options={"verify_signature": False})
    exp_timestamp = decoded["exp"] 
    exp_time = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

    if (verbose):
        print(f"Decoded JWT: {decoded}")
        print(f"Expiration Time: {exp_time}")
        print(f"Duration JWT is Valid: {(exp_time - datetime.now(timezone.utc)).total_seconds()/3600:.4f} hours")
        print(f"Is token expired? {exp_time < datetime.now(timezone.utc)}\n\n")
    
    return exp_time < datetime.now(timezone.utc)

def generateInstructions(prompt, parameters):
    prompt = f"<s> [INST] {prompt} [/INST]"
    if parameters == None:
        parameters = {
        "best_of": 1,
        "decoder_input_details": True,
        "details": True,
        "do_sample": True,
        "frequency_penalty": 0.1,
        "max_new_tokens": 500,
        "repetition_penalty": 1.03,
        "return_full_text": False,
        "seed": None,
        "stop": ["photographer"],
        "temperature": 0.5,
        # "top_tokens": [1, 2],
        # "top_tokens": [ {"id": 0, "logprob": -0.34, "special": False, "text": "test"}],
        "top_k": 10,
        "top_n_tokens": 5,
        "top_p": 0.95,
        "truncate": None,
        "typical_p": 0.95,
        "watermark": True
        }

    return prompt, parameters
    
def sendInstructions(apiURL, key, token, prompt, parameters):
    if (prompt == None and parameters == None):
        response = requests.post(
            apiURL,
            headers={"Authorization": key}
        )
    else:
        response = requests.post(
            apiURL,
            headers= {"accept": "application/json",
                      "Authorization": f"Bearer {token}",
                      "Content-Type": "application/json"},
            json= {"inputs": prompt,
                   "parameters": parameters}
        )

    if response.status_code != 200:
        print(f"Error: {response.status_code} : {response.text}")
        exit()
    else:
        try:
            json_response = response.json()
            print(f'Response from the model (JSON): {json_response}\n\n')
            return response
        except requests.exceptions.JSONDecodeError as e:
            print(f"Failed to decode JSON response: {str(e)}")
            print("Response content:", response.content)


if __name__ == "__main__":
    main() 