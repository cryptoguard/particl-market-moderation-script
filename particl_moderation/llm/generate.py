import json
import subprocess
import os
import shlex
import sys

from typing import Tuple, Dict
from particl_moderation.utils.config import get_config, get_full_path
from particl_moderation.utils.error_handler import handle_keyboard_interrupt, initialize_error_handling, check_for_interrupt
from particl_moderation.utils.platform_compat import is_windows


initialize_error_handling()

def get_current_model() -> str:
    model = get_config("llm.model", "gemma2:2b")
    if not model:
        return "gemma2:2b"
    return model

def get_rules_config_path() -> str:
    return get_full_path("rules.config_file")

def get_predefined_rules_path() -> str:
    return get_full_path("rules.predefined_file")

def verify_rules_configuration() -> bool:
    rules_config_path = get_full_path('rules.config_file')

    if not rules_config_path:
        print("Error: Rules configuration file path is empty", file=sys.stderr)
        return False

    if not os.path.exists(rules_config_path):
        print(f"Error: Rules configuration file not found at {rules_config_path}", file=sys.stderr)
        return False

    try:
        with open(rules_config_path, 'r') as f:
            rules = json.load(f)
        
        required_categories = ["adult-content", "children", "drugs", "online-services", "personal-data", "weapons"]
        required_types = ["downvote", "upvote", "ignore"]

        for category in required_categories:
            if category not in rules:
                print(f"Error: Missing required category '{category}' in rules configuration", file=sys.stderr)
                return False
            
            for rule_type in required_types:
                if rule_type not in rules[category]:
                    print(f"Error: Missing required rule type '{rule_type}' in category '{category}'", file=sys.stderr)
                    return False

        return True

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in rules configuration file {rules_config_path}: {str(e)}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error verifying rules configuration: {str(e)}", file=sys.stderr)
        return False

def simplify_rules(config_file: str) -> str:
    with open(config_file, 'r') as f:
        rules = json.load(f)

    downvote = set()
    upvote = set()
    ignore = set()

    for category in rules.values():
        downvote.update(category.get('downvote', []))
        upvote.update(category.get('upvote', []))
        ignore.update(category.get('ignore', []))

    result = []
    if not downvote:
        result.append("- There is no item in the 'false' category, so do not classify any listing as 'false'.")
    else:
        result.append(f"- The 'false' category: The listing should go in this category if its title and description matches the following terms or closely relate to them: {', '.join(downvote)}.")

    if not upvote:
        result.append("- There is no item in the 'true' category, so do not classify any listing as 'true'.")
    else:
        result.append(f"- The 'True' category: The listing should go in this category if its title and description matches the following terms or closely relate to them: {', '.join(upvote)}.")

    if ignore:
        result.append(f"The 'Ignore' category: The listing should go in this category if its title and description content do not match or closely relate to the terms listed in the false category, or if it matches or closely relate to the following terms: {', '.join(ignore)}.")

    return "\n".join(result)

@handle_keyboard_interrupt
def multiple_llm_calls(title: str, description: str) -> Tuple[int, int, int]:
    true_count = 0
    false_count = 0
    ignore_count = 0

    for _ in range(10):
        check_for_interrupt()
        try:
            response = generate_prompt_and_send(title, description)
            if response == "true":
                true_count += 1
            elif response == "false":
                false_count += 1
            else:
                ignore_count += 1
        except KeyboardInterrupt:
            print("\nLLM calls interrupted by user.")
            raise

    return true_count, false_count, ignore_count

@handle_keyboard_interrupt
def generate_prompt_and_send(title: str, description: str) -> str:
    rules_config_file = get_rules_config_path()
    model = get_current_model()
    
    try:
        simplified_rules = simplify_rules(rules_config_file)
    except FileNotFoundError:
        print(f"Error: {rules_config_file} not found.", file=sys.stderr)
        return "ignore"

    prompt = f"""
You are an operator tasked with classifying online marketplace listings in three different categories: 'true', 'false', or 'ignore'. You are only able to respond to my requests with one of these three words: 'true', 'false', and 'ignore'. To classify listings, you analyze their titles and descriptions and verify if there are terms that match or closely relate to terms contained in each of the following categories:

{simplified_rules}

The listing you must evaluate:
Listing title: {title}
Listing description: {description}

Determine in which category this listing should go based on its title and description.

If a listing doesn't clearly fit in either the "false" or "true" category, mark it as 'ignore'.

Your response(respond with only the word of the category):
"""

    try:
        if is_windows():
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.Popen(
                ["ollama", "run", model, prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                universal_newlines=False  # Use binary mode
            )
            stdout_data, stderr_data = process.communicate()
            
            try:
                full_response = stdout_data.decode('utf-8')
            except UnicodeDecodeError:
                full_response = stdout_data.decode('latin1', errors='replace')
                
            if process.returncode != 0:
                print("Error: Failed to run local model. Check if Ollama is installed and running.", file=sys.stderr)
                return "ignore"
        else:
            # Keep existing behavior for non-Windows systems
            result = subprocess.run(["ollama", "run", model, prompt], capture_output=True, text=True, check=True)
            full_response = result.stdout

    except subprocess.CalledProcessError:
        print("Error: Failed to run local model. Check if Ollama is installed and running.", file=sys.stderr)
        return "ignore"

    response = [line for line in full_response.split('\n') if line.strip()][-1]

    # Process the response
    word_count = len(response.split())
    if word_count > 10:
        return "ignore"
    
    response_lower = response.lower()
    if "true" in response_lower:
        return "true"
    elif "false" in response_lower:
        return "false"
    else:
        return "ignore"

def load_predefined_rules() -> Dict:
    predefined_rules_file = get_predefined_rules_path()
    try:
        with open(predefined_rules_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {predefined_rules_file} not found.", file=sys.stderr)
        return {}

if __name__ == "__main__":
    if verify_rules_configuration():
        title = "Example Product"
        description = "This is a sample product description."
        result = multiple_llm_calls(title, description)
        print(f"Results: True: {result[0]}, False: {result[1]}, Ignore: {result[2]}")

        predefined_rules = load_predefined_rules()
        print("Predefined Rules:")
        print(json.dumps(predefined_rules, indent=2))
    else:
        print("Rules configuration verification failed. Please check your configuration.")