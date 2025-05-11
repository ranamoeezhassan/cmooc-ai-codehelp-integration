import requests
import os
from dotenv import load_dotenv
from urllib3 import Retry

def get_access_token(username, password):
    """Get access token from API with improved error handling."""
    try:
        response = requests.post(
            "http://127.0.0.1:5000/api/login",
            json={
                "username": username,
                "password": password
            }
        )
        # Ensure the request was successful
        response.raise_for_status()
        
        try:
            response_data = response.json()
        except requests.exceptions.JSONDecodeError:
            print(f"Failed to decode JSON response. Raw response: {response.text}")
            raise ValueError("Invalid JSON response from server")
            
        if "access_token" not in response_data:
            raise ValueError("No access token in response")
        
        print("Response data: ", response_data)
            
        return response_data["access_token"]
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure the Flask app is running.")
        print("Try: flask --app codehelp run")
        raise
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response content: {response.text}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

def submit_query(access_token: str, code: str, error: str, issue: str, context=None, task_instructions=None):
    """Submit a query with improved error handling and debugging."""
    data = {
        "code": code,
        "error": error,
        "issue": issue
    }
    if context is not None:
        data["context"] = context
    if task_instructions is not None:
        data["task_instructions"] = task_instructions

    try:
        # Print debug information
        print("\nSubmitting query...")
        print("Data payload:", data)
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Make the request with increased timeout and retries
        session = requests.Session()

        response = session.post(
            "http://127.0.0.1:5000/api/query",
            json=data,
            headers=headers,
            timeout=60
        )
        
        # Check if response is valid
        if response.status_code == 200:
            print("Query submitted successfully!")
            return response
        else:
            print(f"Error submitting query. Status code: {response.status_code}")
            print(f"Response text: {response.text}")
            response.raise_for_status()

    except requests.exceptions.ConnectionError as e:
        print("\nConnection Error:")
        print("Could not connect to server. Make sure:")
        print("1. The Flask server is running (flask --app codehelp run)")
        print("2. The server is accessible at http://127.0.0.1:5000")
        print(f"Detailed error: {e}")
        raise
        
    except requests.exceptions.Timeout:
        print("\nTimeout Error:")
        print("The request took too long to complete.")
        print("Try increasing the timeout value or check server load.")
        raise
        
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Response content: {e.response.text}")
        raise

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


def switch_to_class(token, class_id):
    """Switch to a specific class context"""
    response = requests.post(  # Using the correct endpoint
        f"http://127.0.0.1:5000/api/classes/switch/{class_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        print(f"Error switching class: {response.json()}")
        raise ValueError(f"Failed to switch class: {response.json().get('error')}")
        
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
    # contexts = get_contexts(token)
    # print("Available contexts:", contexts)
    
    # # Get specific context
    # context = get_context(token, "Writing and Compiling First Program")
    # print("Context retreived by name:", context)
    
    # # Create new context (if instructor)
    # new_context = create_context(token, "new_context", {"tools": ["python", "flask"]})
    # print("New context:", new_context)
    
    # # Submit query with context
    # response = submit_query(token, 
    #     code="def print(): yo", 
    #     error="IndentationError", 
    #     issue="Cant print stuff", 
    #     context="python"
    # )
    # print(response.json())
    switch_to_class(token, 1)

    print("==============================================\n")
    print("TESTING QUERIES SENT BY ADMIN ON TEST CLASS\n")
    # 1. Testing Python programming without loops
    submit_query(
        access_token=token,
        code="def sum_list(numbers):\n    total = 0\n    for n in numbers:\n        total += n\n    return total",
        error="",
        issue="How can I sum a list without using loops?",
        task_instructions={
            "tools": "Python",
            "details": "Write a function to sum all numbers in a list without using loops",
            "avoid": "loops\r\nfor\r\nwhile",
            "name": "recursive_sum"
        }
    )

    # 2. Testing C programming with specific requirements
    submit_query(
        access_token=token,
        code="void reverse(int arr[]) {\n    for(int i=0; i<len; i++) {\n        // stuck here\n    }\n}",
        error="",
        issue="How to reverse array without loops?",
        task_instructions={
            "tools": "C",
            "details": "Write a function to reverse an array in-place using recursion",
            "avoid": "Do not use loops or additional arrays",
            "name": "array_reverse"
        }
    )

    # 3. Mixed language question about algorithms
    submit_query(
        access_token=token,
        code="def binary_search(arr, target):\n    pass",
        error="",
        issue="How to implement binary search in both C and Python?",
        task_instructions={
            "tools": "C\r\nPython",
            "details": "Implement binary search algorithm that works for sorted arrays",
            "avoid": "Do not use built-in search functions or linear search",
            "name": "binary_search_implementation_test2"
        }
    )

    # 4. Debugging specific case
    submit_query(
        access_token=token,
        code="int main() {\n    int* ptr;\n    *ptr = 5;\n    return 0;\n}",
        error="Segmentation fault",
        issue="Why am I getting a segmentation fault? I think I understand how pointers work",
        task_instructions={
            "tools": "C",
            "details": "Debug a program using pointers and memory allocation",
            "avoid": "Do not use global variables or arrays",
            "name": "pointer_debugging 3"
        }
    )

    # 5. Testing if normal contexts still work
    code_message = r'''
    #include <stdio.h>
    int main() {
        int a = 5;
        if (a = 10) {
            printf("True\n");
        }
        return 0;
    }
    '''
    error_message = "Error: Logical error"
    issue_message = "I thought this would check if a is equal to 10, but it’s not working the way I expected."
    submit_query(token, code_message, error_message, issue_message, context="new_context" )

    print("==============================================\n")

    print("==============================================\n")
    print("TESTING CONTEXTS RETRIEVED ON TEST CLASS\n")

    allContexts = get_contexts(token)
    print("Contexts from Class 1: ", allContexts)
    print("==============================================\n")

    switch_to_class(token, 2)

    print("==============================================\n")
    print("TESTING CREATING CONTEXTS BY ADMIN ON NEW TEST CLASS\n")
    testing_context = create_context(token, "Testing Context", {"tools": "C\r\nPython", "details": "Student learning to use C", "avoid": "libraries"})
    print(testing_context)  

    print("==============================================\n")

    print("==============================================\n")
    print("TESTING CONTEXTS RETRIEVED ON NEW TEST CLASS\n")
    allContexts = get_contexts(token)
    print("Contexts from Class 2: ", allContexts)

    print("==============================================\n")

    print("==============================================\n")
    print("TESTING QUERIES SENT BY STUDENT ON TEST CLASS\n")
    username = "student1"

    # Get token for student account
    student_token = get_access_token(username, password)
    switch_to_class(student_token, 1)

    # Testing Python programming without loops with the student account just to confirm
    submit_query(
        access_token=student_token,
        code="def sum_list(numbers):\n    total = 0\n    for n in numbers:\n        total += n\n    return total",
        error="",
        issue="How can I sum a list without using loops?",
        task_instructions={
            "tools": "Python",
            "details": "Write a function to sum all numbers in a list without using loops",
            "avoid": "loops\r\nfor\r\nwhile",
            "name": "recursive_sum"
        }
    )
    print("==============================================\n")

    print("==============================================\n")
    print("TESTING CONTEXTS RETRIEVED BY STUDENT ON TEST CLASS\n")

    allContexts = get_contexts(student_token)
    print("Contexts from Student's Class: ", allContexts)

    print("==============================================\n")
