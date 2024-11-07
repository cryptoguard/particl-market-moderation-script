import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from particl_moderation.llm.generate import simplify_rules
from particl_moderation.utils.config import get_full_path
from particl_moderation.utils.queue_utils import add_to_queue
from particl_moderation.utils.error_handler import handle_keyboard_interrupt, initialize_error_handling

DUMMY_LISTINGS_FILE = get_full_path("paths.dummy_listings_file")
OUTPUT_FILE = get_full_path("paths.test_prompts_file")
QUEUE_FILE = get_full_path("paths.queue_file")

initialize_error_handling()

@handle_keyboard_interrupt
def generate_test_prompts():
    if not os.path.exists(DUMMY_LISTINGS_FILE):
        print(f"Error: {DUMMY_LISTINGS_FILE} not found.", file=sys.stderr)
        return False

    open(OUTPUT_FILE, 'w').close()
    open(QUEUE_FILE, 'w').close()

    simplified_rules = simplify_rules(get_full_path("rules.config_file"))

    with open(DUMMY_LISTINGS_FILE, 'r') as dummy_file, open(OUTPUT_FILE, 'a') as output_file:
        for line_number, line in enumerate(dummy_file, 1):
            line = line.strip()
            if not line: 
                continue
            
            parts = line.split('|')
            if len(parts) != 3:
                print(f"Error: Invalid format in line {line_number}: {line}", file=sys.stderr)
                continue

            id, title, description = parts
            print(f"Generating prompt for listing: {title}")

            prompt = f"""You are an operator tasked with classifying online marketplace listings in three different categories: 'true', 'false', or 'ignore'. You are only able to respond to my requests with one of these three words: 'true', 'false', and 'ignore'. To classify listings, you analyze their titles and descriptions and verify if there are terms that match or closely relate to terms contained in each of the following categories:

{simplified_rules}

The listing you must evaluate:
Listing title: {title}
Listing description: {description}

Determine in which category this listing should go based on its title and description.

If a listing doesn't clearly fit in either the "false" or "true" category, mark it as 'ignore'.

Your response(respond with only the word of the category):
"""

            # Append the prompt to the output file
            output_file.write(f"Prompt for Listing {id}:\n")
            output_file.write(prompt)
            output_file.write("-----------------------------------------\n")

            # Add to queue
            add_to_queue(id, title, description, "dummy")

    print(f"All prompts have been generated and saved to {OUTPUT_FILE}")
    print(f"Queue has been populated with test listings in {QUEUE_FILE}")
    return True

if __name__ == "__main__":
    generate_test_prompts()
