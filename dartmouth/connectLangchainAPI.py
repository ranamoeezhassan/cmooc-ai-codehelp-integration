"""
name: langchainConnection.py

description: TODO

Rana Moeez Hassan
Winter 2024
"""

import os
from dotenv import find_dotenv, load_dotenv
from langchain_dartmouth.llms import DartmouthLLM

def main():
    load_dotenv(find_dotenv())
    dartmouth_api_key = os.environ["DARTMOUTH_API_KEY"]

    # Instantantiate a code llama model that is capable of receiving instructions
    llm = DartmouthLLM(model_name="codellama-13b-instruct-hf", max_new_tokens=1000, return_full_text=True)

    # Instruction format needs to be the same as how the model was tuned
    response = llm.invoke("How can I define a class in Python?")
    print(f"BAD RESPONSE:\n {response}")
    print("=================================================================")

    betterResponse = llm.invoke("<s> [INST] How can I define a class in Python? [/INST]")
    print(f"BETTER RESPONSE:\n {betterResponse}\n")
    print("=================================================================")

    betterResponse2 = llm.invoke("<s> [INST] What are pointers in C? [/INST]")
    print(f"BETTER RESPONSE 2:\n {betterResponse2}\n")
    print("=================================================================")

if __name__ == "__main__":
    main() 