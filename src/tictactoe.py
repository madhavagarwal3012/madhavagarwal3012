import os
import re

README_PATH = 'README.md'
ISSUE_TITLE = os.getenv('ISSUE_TITLE', '')

def main():
    if not ISSUE_TITLE.startswith("ttb|"):
        return

    with open(README_PATH, 'r', encoding='utf-8') as f:
        full_content = f.read()

    # 1. Extract ONLY the Tic Tac Toe section
    section_match = re.search(r'(.*?)', full_content, re.DOTALL)
    if not section_match:
        return
    
    game_section = section_match.group(1)

    # 2. Parse the board from that section
    pattern = r'\| (.*?) \| (.*?) \| (.*?) \|'
    matches = re.findall(pattern, game_section)
    board_rows = matches[1:] # Skip the alignment row
    
    flat_board = []
    for row in board_rows:
        for cell in row:
            if "❌" in cell: flat_board.append("X")
            elif "⭕" in cell: flat_board.append("O")
            else: flat_board.append(" ")

    # 3. Handle Logic
    if "reset" in ISSUE_TITLE:
        flat_board = [" "] * 9
    else:
        try:
            move_idx = int(ISSUE_TITLE.split('|')[1]) - 1
            if 0 <= move_idx <= 8 and flat_board[move_idx] == " ":
                flat_board[move_idx] = "X"
                for i in range(9):
                    if flat_board[i] == " ":
                        flat_board[i] = "O"
                        break
        except: return

    # 4. Rebuild the Table
    def get_cell(i):
        if flat_board[i] == "X": return "❌"
        if flat_board[i] == "O": return "⭕"
        return f"[ {i+1} ](https://github.com/madhavagarwal3012/madhavagarwal3012/issues/new?title=ttb%7C{i+1})"

    new_table = (
        f"\n| :---: | :---: | :---: |\n"
        f"| {get_cell(0)} | {get_cell(1)} | {get_cell(2)} |\n"
        f"| {get_cell(3)} | {get_cell(4)} | {get_cell(5)} |\n"
        f"| {get_cell(6)} | {get_cell(7)} | {get_cell(8)} |\n"
    )

    # 5. Put it back only in its own section
    updated_content = full_content.replace(game_section, new_table)

    with open(README_PATH, 'w', encoding='utf-8') as f:
        f.write(updated_content)

if __name__ == "__main__":
    main()
