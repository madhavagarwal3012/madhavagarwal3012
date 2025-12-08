import os

# --- Configuration (SECURELY READ FROM ENVIRONMENT) ---
# This value is passed by the GitHub Action from your repository secrets.
CORRECT_ANSWER = os.environ.get("CIPHER_SOLUTION", "") 
if not CORRECT_ANSWER:
    # This prevents the action from running if the secret is missing
    print("Error: CIPHER_SOLUTION environment variable not set in the workflow.")
    exit()

# Get data about the issue that triggered the action
issue_title = os.environ.get("ISSUE_TITLE", "")
issue_creator = os.environ.get("ISSUE_AUTHOR", "a fan")


# Function to handle README file updates
def update_readme(winner=None):
    """Reads README, updates the cipher section based on winner, and writes back."""
    try:
        with open("README.md", "r") as f:
            content = f.read()
    except FileNotFoundError:
        print("Error: README.md not found.")
        return

    # Markers MUST exist in your README.md
    START_MARKER = ""
    END_MARKER = ""

    if START_MARKER not in content or END_MARKER not in content:
        print("Error: README markers not found. Please add and .")
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
        # Challenge text (if no winner or wrong guess)
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

    with open("README.md", "w") as f:
        f.write(updated_content)


# --- Main Verification Logic ---
def main():
    # 1. Extract the guess from the issue title
    try:
        # Example title: "Atbash Solution: Message"
        # We take the part after the colon and convert to uppercase for safe comparison.
        guess = issue_title.split(":")[1].strip().upper()
    except IndexError:
        print("Issue title not in correct format. Skipping.")
        return

    # 2. Compare guess with the secure answer
    if guess == CORRECT_ANSWER:
        print(f"✅ Correct answer submitted by {issue_creator}!")
        update_readme(winner=issue_creator)
    else:
        print(f"❌ Incorrect guess: {guess}. No changes to README.")

if __name__ == "__main__":
    main()
