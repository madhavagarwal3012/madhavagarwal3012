import os
import re

README_PATH = 'README.md'
ISSUE_TITLE = os.getenv('ISSUE_TITLE', '')

def main():
    if not ISSUE_TITLE.startswith("ttb|"):
        return

    with open(README_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find the 3x3 grid rows
    pattern = r'\| (.*?) \| (.*?) \| (.*?) \|'
    matches = re.findall(pattern, content)
    
    # Selecting the game board rows (ignoring header and separator)
    board_rows = matches[2:5] 
    flat_board = []
    for row in board_rows:
        for cell in row:
            if "❌" in cell: flat_board.append("X")
            elif "⭕" in cell: flat_board.append("O")
            else: flat_board.append(" ")

    if "reset" in ISSUE_TITLE:
        flat_board = [" "] * 9
    else:
        try:
            move_idx = int(ISSUE_TITLE.split('|')[1]) - 1
            if 0 <= move_idx <= 8 and flat_board[move_idx] == " ":
                flat_board[move_idx] = "X"
                # Simple Bot: Moves to the first available spot
                for i in range(9):
                    if flat_board[i] == " ":
                        flat_board[i] = "O"
                        break
        except Exception:
            return

    def get_cell(i):
        if flat_board[i] == "X": return "❌"
        if flat_board[i] == "O": return "⭕"
        return f"[ ](https://github.com/madhavagarwal3012/madhavagarwal3012/issues/new?title=ttb%7C{i+1})"

    new_table = (
        f"| {get_cell(0)} | {get_cell(1)} | {get_cell(2)} |\n"
        f"| {get_cell(3)} | {get_cell(4)} | {get_cell(5)} |\n"
        f"| {get_cell(6)} | {get_cell(7)} | {get_cell(8)} |"
    )

    table_regex = r'\| :---: \| :---: \| :---: \|\n(?:\|.*\|\n?){3}'
    new_header_and_table = f"| :---: | :---: | :---: |\n{new_table}"
    
    updated_content = re.sub(table_regex, new_header_and_table, content)

    with open(README_PATH, 'w', encoding='utf-8') as f:
        f.write(updated_content)

if __name__ == "__main__":
    main()
