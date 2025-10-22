import os
import json
import re
from datetime import datetime

# --- Configuration for your repository structure ---
GAME_STATE_FILE = 'data/ttt_state.json'
MOVE_HISTORY_FILE = 'data/ttt_moves.txt' 
README_FILE = 'README.md'
ASSET_PATH = 'img' 
REPO_OWNER = 'madhavagarwal3012' # IMPORTANT: Ensure this is your username

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
    
    # Ensure the file exists before appending
    if not os.path.exists(MOVE_HISTORY_FILE):
        with open(MOVE_HISTORY_FILE, 'w') as f:
            f.write(move_entry + '\n')
    else:
        with open(MOVE_HISTORY_FILE, 'a') as f:
            f.write(move_entry + '\n')

def get_last_5_moves():
    """Reads the last 5 moves for the README display."""
    if not os.path.exists(MOVE_HISTORY_FILE):
        return []
        
    with open(MOVE_HISTORY_FILE, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
        
        last_moves = []
        for line in lines[-5:]:
            try:
                # Example line: 2023-10-25 10:00:00 - X:B2
                parts = line.split(' - ')
                timestamp = parts[0]
                player_move = parts[-1].split(':')
                player = player_move[0]
                move = player_move[1]
                last_moves.append({'player': player, 'move': move, 'timestamp': timestamp})
            except IndexError:
                # Skip badly formatted lines
                continue 
        return last_moves


# --- 3. Parsing and Game Logic ---
def get_move_from_command(command):
    """Converts a move string (A1-C3) into a board index (0-8) and returns the move string."""
    # Pattern looks for 'TicTacToe:' followed by optional spaces and the move (e.g., B2)
    match = re.search(r'TicTacToe:\s*([A-C][1-3])', command, re.IGNORECASE)
    if match:
        move_str = match.group(1).upper()
        col = ord(move_str[0]) - ord('A')
        row = int(move_str[1]) - 1
        index = row * 3 + col
        return index, move_str if 0 <= index < 9 else (None, None)
    return None, None

def check_for_winner(board):
    """Checks the 8 winning lines."""
    lines = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8], # Columns
        [0, 4, 8], [2, 4, 6]            # Diagonals
    ]
    for line in lines:
        a, b, c = line
        if board[a] and board[a] == board[b] and board[a] == board[c]:
            return board[a]
    return None

def is_board_full(board):
    return "" not in board

def process_move(state, index, move_str):
    """Updates the game state with a valid move."""
    # Check for game over or occupied square
    if state['winner'] or state['board'][index] != "":
        return False
        
    current_player = state['turn']
    state['board'][index] = current_player
    
    record_move(current_player, move_str)

    winner = check_for_winner(state['board'])
    if winner:
        state['winner'] = winner
    elif is_board_full(state['board']):
        state['winner'] = "DRAW"
        
    # Switch turns if game is still active
    if not state['winner']:
        state['turn'] = 'O' if state['turn'] == 'X' else 'X'
        
    return True
    
# --- 4. Board to Markdown Conversion (Renders the Board and Move History) ---
def board_to_markdown(board, state):
    # This uses os.environ.get('GITHUB_REPOSITORY') from the Action context
    repo = os.environ.get('GITHUB_REPOSITORY', REPO_OWNER + '/' + REPO_OWNER)
    
    # Status Header
    if state['winner'] == "DRAW":
        status_header = "**GAME OVER! It's a DRAW!**"
    elif state['winner']:
        status_header = f"**GAME OVER! Winner: {state['winner']}**"
    else:
        status_header = f"**Current Turn: {state['turn']}**"
        
    # Generate the 3x3 table
    markdown_table = "| | | |\n|:-:|:-:|:-:|\n" 
    for i in range(9):
        # Convert index (0-8) to Cell ID (A1-C3)
        cell_id = chr(ord('A') + (i % 3)) + str(1 + (i // 3))
        content = board[i]
        
        if content == "X":
            cell_markdown = f"<img src='{ASSET_PATH}/x.svg' width='100px'>"
        elif content == "O":
            cell_markdown = f"<img src='{ASSET_PATH}/o.svg' width='100px'>"
        elif state['winner']:
            # If game is over, render empty tiles without links
            cell_markdown = f"<img src='{ASSET_PATH}/empty.svg' width='100px'>"
        else: 
            # Render empty tiles with links (Issue Title trigger)
            issue_link = f"https://github.com/{repo}/issues/new?title=TicTacToe:%20{cell_id}"
            cell_markdown = f"<a href='{issue_link}'><img src='{ASSET_PATH}/empty.svg' width='100px'></a>"
        
        markdown_table += f"| {cell_markdown} "
        if (i + 1) % 3 == 0:
            markdown_table += "|\n"
            
    final_output = f"{status_header}\n{markdown_table}"
    
    # Move History Table
    final_output += "\n\n<details>\n  <summary>Last 5 Moves</summary>\n\n| Player | Move | Timestamp |\n| :----: | :--: | :--------: |\n"
    for move in get_last_5_moves():
        final_output += f"| {move['player']} | {move['move']} | {move['timestamp']} |\n"
    final_output += "\n</details>"

    return final_output

# --- Main Execution Block ---
def main():
    state = load_game_state()
    
    command = os.environ.get('MOVE_COMMAND', '').strip()
    comment_username = os.environ.get('GITHUB_ACTOR') 
    
    is_reset_command = re.search(r'TicTacToe:\s*RESET', command, re.IGNORECASE)
    move_index, move_str = get_move_from_command(command)

    # Function to update the README (used by both move and reset)
    def update_readme(current_state):
        markdown_board = board_to_markdown(current_state['board'], current_state)
        
        with open(README_FILE, 'r+') as f:
            content = f.read()
            
            # CRITICAL FIX: Use the correct, non-greedy regex to prevent file bloat
            new_content = re.sub(
                r'.*?',
                f'\n{markdown_board}\n',
                content,
                flags=re.DOTALL
            )
            
            f.seek(0)
            f.write(new_content)
            f.truncate()
            
    if is_reset_command:
        if state['winner'] and comment_username == REPO_OWNER:
            # --- RESET LOGIC ---
            state = {"board": [""] * 9, "turn": "X", "winner": None}
            save_game_state(state)
            update_readme(state)
            print("Tic-Tac-Toe game has been reset by the owner and a new game has started.")
        elif state['winner'] and comment_username != REPO_OWNER:
            print(f"Reset command received, but only the repository owner ({REPO_OWNER}) can reset a finished game.")
        else:
            print("Reset command received, but the game is not yet finished. Skipping reset.")
            
    elif move_index is not None:
        # --- NORMAL MOVE LOGIC ---
        if process_move(state, move_index, move_str):
            save_game_state(state)
            update_readme(state)
            print(f"Move {move_str} processed successfully. Game state saved and README updated.")
        else:
            print("Illegal move (square occupied or game over). Skipping update.")
    else:
        print("Issue title found but does not contain a valid TicTacToe move command. Skipping.")

if __name__ == "__main__":
    main()
