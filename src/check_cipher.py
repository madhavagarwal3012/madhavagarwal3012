import os
import pathlib
import re

# --- Configuration (SECURELY READ FROM ENVIRONMENT) ---
CORRECT_ANSWER = os.environ.get("CIPHER_SOLUTION", "") 
if not CORRECT_ANSWER:
    print("Error: CIPHER_SOLUTION environment variable not set in the workflow.")
    exit()

issue_title = os.environ.get("ISSUE_TITLE", "")
issue_creator = os.environ.get("ISSUE_AUTHOR", "a fan")

# Define the absolute path to the README file
# GitHub Actions typically runs from the root of the repository.
# pathlib ensures cross-platform compatibility.
REPO_ROOT = pathlib.Path(__file__).parent.parent
README_PATH = REPO_ROOT / "README.md"


# Function to handle README file updates
def update_readme(winner=None):
    """Reads README, updates the cipher section based on winner, and writes back."""
    try:
        # 1. Read the content from the guaranteed location
        with open(README_PATH, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: README.md not found at {README_PATH}.")
        return

    # Markers MUST exist in your README.md
    START_MARKER = ""
    END_MARKER = ""

    if START_MARKER not in content or END_MARKER not in content:
        print("Error: README markers not found. Please verify placement.")
        return

    start_index = content.find(START_MARKER) + len(START_MARKER)
    end_index = content.find(END_MARKER)

    # --- Content to insert into the README ---
    if winner:
        # Success message
        new_content = f"""
        
### 🏆 SOLVED!
Congratulations to **[@{winner}](https://github.com/{winner})** for cracking the Atbash Code!
The secret phrase was: **{CORRECT_ANSWER}**

*A new challenge will be launched soon!*
        
"""
    else:
        # Challenge text
        new_content = f"""
        
### 🧩 The Cipher:
This is an **Atbash Cipher**. (A ↔ Z, B ↔ Y, C ↔ X, etc.)
*The solution is a common programming phrase (3 words).*

### 📜 Encoded Message:
> **QZIZ RH KLDUUEFO**

Do you have the solution? Be the first to submit the correct answer to be featured!

[Submit Your Solution Here!](https://github.com/madhavagarwal3012/madhavagarwal3012/issues/new?title=Atbash%20Solution:%20[Your%20Decoded%20Phrase]&body=I%20solved%20the%20code!%20My%20answer%20is:%20)
        
"""
    # ----------------------------------------
    
    updated_content = content[:start_index] + new_content + content[end_index:]

    # 2. Write the content back to the guaranteed location
    try:
        with open(README_PATH, "w") as f:
            f.write(updated_content)
        print(f"Successfully updated README.md at {README_PATH}")
    except Exception as e:
        print(f"Error writing to README.md: {e}")


# --- Main Verification Logic (Final Diagnostic Version) ---
def main():
    # 1. Look for the exact starting phrase to isolate the guess part
    if not issue_title.startswith("Atbash Solution:"):
        print("Title format is incorrect. Skipping verification.")
        return

    # 2. Extract the guess robustly
    try:
        guess_raw = issue_title.split(":", 1)[1].strip()
        guess_clean = re.sub(r'[\s\[\]#\d]+$', '', guess_raw).upper()
        
    except IndexError:
        print("Could not parse guess from issue title.")
        return
        
    print("--- DIAGNOSTIC START ---")
    print(f"Parsed Guess (Cleaned): '{guess_clean}'")
    print(f"Expected Answer (Secret): '{CORRECT_ANSWER}'")
    print(f"Guess is empty: {guess_clean == ''}")
    print(f"Secret is empty: {CORRECT_ANSWER == ''}")
    print("--- DIAGNOSTIC END ---")

    # 3. Compare the cleaned guess with the secure answer
    if guess_clean == CORRECT_ANSWER:
        print(f"✅ SUCCESS! Correct answer submitted by {issue_creator}!")
        update_readme(winner=issue_creator)
    else:
        print(f"❌ FAILURE. Incorrect guess: {guess_clean}. No changes to README. Exiting with error code 1.")
        # 💡 NEW: Exit with a non-zero code to fail the job
        exit(1)
        
if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
