import requests
import os
from dotenv import load_dotenv

def get_access_token(username, password):
    response = requests.post(
        "http://127.0.0.1:5000/api/login",
        json={
            "username": username,
            "password": password
        }
    )
    # print("Raw response text with token:", response.text)
    response_data = response.json()
    return response_data["access_token"]

def submit_query(access_token, code, error, issue, context=None, task_instructions=None):
    data = {
        "code": code,
        "error": error,
        "issue": issue
    }
    if context is not None:
        data["context"] = context
    if task_instructions is not None:
        data["task_instructions"] = task_instructions

    response = requests.post(
        "http://127.0.0.1:5000/api/query",
        json=data,
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )
    # print("Raw response text for query:", response.text)
    return response

def get_query(access_token, query_id):
    response = requests.get(
        f"http://127.0.0.1:5000/api/query/{query_id}",
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )
    return response.json()

def get_contexts(access_token):
    response = requests.get(
        "http://127.0.0.1:5000/api/contexts",
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )
    return response.json()

def get_context(access_token, name):
    response = requests.get(
        f"http://127.0.0.1:5000/api/context/{name}",
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )
    return response.json()

def create_context(access_token, name, config=None, context_str=None):
    """Create a new context.
    
    Args:
        access_token (str): Authentication token
        name (str): Name of the context
        config (dict, optional): Configuration for the context
        context_str (str, optional): Context string for prompt generation
    """
    response = requests.post(
        "http://127.0.0.1:5000/api/context",
        json={
            "name": name,
            "config": config or {},
            "context_str": context_str or "Default context for C programming"  # Add default context string
        },
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )
    return response.json()

def delete_context(access_token: str, name: str):
    """Delete a context by name."""
    response = requests.delete(
        f"http://127.0.0.1:5000/api/context/{name}",
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )
    return response.json()


if __name__ == "__main__":
    load_dotenv()
    username = "ranamoeez"
    password = os.environ.get("ACCOUNT_PASSWORD")

    # Get token
    token = get_access_token(username, password)

    # Submit a query and print it
    # response = submit_query(token, code="def print(): yo", error="IndentationError", issue="Cant print stuff", context=None)
    # print(response.json())
    
    # List all contexts
    contexts = get_contexts(token)
    print("Available contexts:", contexts)
    
    # Get specific context
    context = get_context(token, "Writing and Compiling First Program")
    print("Context retreived by name:", context)
    
    # Create new context (if instructor)
    new_context = create_context(token, "new_context", {"tools": ["python", "flask"]})
    print("New context:", new_context)
    
    # Submit query with context
    response = submit_query(token, 
        code="def print(): yo", 
        error="IndentationError", 
        issue="Cant print stuff", 
        context="python"
    )
    print(response.json())