import os
import json
import re
from datetime import datetime

# --- File paths adjusted for your repository structure ---
GAME_STATE_FILE = 'data/ttt_state.json'
MOVE_HISTORY_FILE = 'data/ttt_moves.txt' # NEW FILE
README_FILE = 'README.md'
ASSET_PATH = 'img' 

# --- 1. Load/Save Game State ---
def load_game_state():
    if os.path.exists(GAME_STATE_FILE):
        with open(GAME_STATE_FILE, 'r') as f:
            return json.load(f)
    return {"board": [""] * 9, "turn": "X", "winner": None}

def save_game_state(state):
    with open(GAME_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

# --- 2. Move History Functions ---
def record_move(player, move):
    """Appends the new move to the move history file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    move_entry = f"{timestamp} - {player}:{move}"
    
    with open(MOVE_HISTORY_FILE, 'a') as f:
        f.write(move_entry + '\n')

def get_last_5_moves():
    """Reads the last 5 moves from the history file."""
    if not os.path.exists(MOVE_HISTORY_FILE):
        return []
        
    with open(MOVE_HISTORY_FILE, 'r') as f:
        # Read all lines, skip the header line (if it exists)
        lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
        
        last_moves = []
        for line in lines[-5:]:
            # Expected format: "2025-10-22 22:15:00 - X:B2"
            parts = line.split(' - ')
            move_data = parts[-1].split(':')
            last_moves.append({'player': move_data[0], 'move': move_data[1], 'timestamp': parts[0]})
        return last_moves


# --- 3. Parsing and Logic ---
def get_move_from_command(command):
    match = re.search(r'TicTacToe:\s*([A-C][1-3])', command, re.IGNORECASE)
    if match:
        move_str = match.group(1).upper()
        # Converts A1, B2, C3 into board indices 0-8
        col = ord(move_str[0]) - ord('A')
        row = int(move_str[1]) - 1
        index = row * 3 + col
        return index if 0 <= index < 9 else None
    return None

def check_for_winner(board):
    lines = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Horizontal
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Vertical
        [0, 4, 8], [2, 4, 6]            # Diagonal
    ]
    for line in lines:
        a, b, c = line
        if board[a] and board[a] == board[b] and board[a] == board[c]:
            return board[a]
    return None

def is_board_full(board):
    return "" not in board

def process_move(state, index, move_str):
    if state['winner'] or state['board'][index] != "":
        print("Illegal move or game over.")
        return False
        
    current_player = state['turn']
    state['board'][index] = current_player
    
    # Record the move before checking the winner
    record_move(current_player, move_str)

    winner = check_for_winner(state['board'])
    if winner:
        state['winner'] = winner
    elif is_board_full(state['board']):
        state['winner'] = "DRAW"
        
    if not state['winner']:
        state['turn'] = 'O' if state['turn'] == 'X' else 'X'
        
    return True
    
# --- 4. Board to Markdown Conversion ---
def board_to_markdown(board, state):
    repo = os.environ.get('GITHUB_REPOSITORY', 'madhavagarwal3012/madhavagarwal3012')
    
    # Board Table Generation
    markdown = "| | | |\n|:-:|:-:|:-:|\n" 
    for i in range(9):
        cell_id = chr(ord('A') + (i % 3)) + str(1 + (i // 3))
        content = board[i]
        
        if content == "X":
            cell_markdown = f"<img src='{ASSET_PATH}/x.svg' width='100px'>"
        elif content == "O":
            cell_markdown = f"<img src='{ASSET_PATH}/o.svg' width='100px'>"
        else:
            issue_link = (f"https://github.com/{repo}/issues/new?title=TicTacToe:%20{cell_id}"
                          f"&body=Click%20Submit%20to%20make%20your%20move%20to%20{cell_id}")
            cell_markdown = f"<a href='{issue_link}'><img src='{ASSET_PATH}/empty.svg' width='100px'></a>"
        
        markdown += f"| {cell_markdown} "
        if (i + 1) % 3 == 0:
            markdown += "|\n"
            
    # Status Header
    if state['winner'] == "DRAW":
        status_header = "**GAME OVER! It's a DRAW!**"
    elif state['winner']:
        status_header = f"**GAME OVER! Winner: {state['winner']}**"
    else:
        status_header = f"**Current Turn: {state['turn']}**"
        
    final_output = f"{status_header}\n{markdown}"
    
    # Move History Table (NEW)
    final_output += "\n\n<details>\n  <summary>Last 5 Moves</summary>\n\n| Player | Move | Timestamp |\n| :----: | :--: | :--------: |\n"
    
    for move in get_last_5_moves():
        final_output += f"| {move['player']} | {move['move']} | {move['timestamp']} |\n"
        
    final_output += "\n</details>"

    return final_output

# --- Main Execution Block ---
if __name__ == "__main__":
    state = load_game_state()
    
    command = os.environ.get('MOVE_COMMAND', '').strip()
    match = re.search(r'TicTacToe:\s*([A-C][1-3])', command, re.IGNORECASE)
    
    if match:
        move_str = match.group(1).upper()
        move_index = get_move_from_command(command)
    else:
        move_index = None
        move_str = None
        
    if move_index is not None and process_move(state, move_index, move_str):
        save_game_state(state)
        
        markdown_board = board_to_markdown(state['board'], state)
        
        with open(README_FILE, 'r+') as f:
            content = f.read()
            # Replace content between the TTC markers
            new_content = re.sub(
                r'.*?',
                f'\n{markdown_board}\n',
                content,
                flags=re.DOTALL
            )
            f.seek(0)
            f.write(new_content)
            f.truncate()
    else:
        print("No valid move found or game is over. Skipping update.")
