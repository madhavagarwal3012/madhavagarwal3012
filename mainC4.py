import re
import os
import os.path
import sys
import ast
import traceback
from enum import Enum
from datetime import datetime
from connect4 import connect4
import yaml
from github import Github
import src.markdownC4 as markdown

RED = 1
BLUE = 2

class Action(Enum):
    UNKNOWN = 0
    MOVE = 1
    NEW_GAME = 2

def update_top_moves(user):
    with open('data/top_movesC4.txt', 'r') as file:
        contents = file.read()
        dictionary = ast.literal_eval(contents)
    dictionary[user] = dictionary.get(user, 0) + 1
    with open('data/top_movesC4.txt', 'w') as file:
        file.write(str(dictionary))


def update_last_moves(line):
    with open('data/last_movesC4.txt', 'r+') as last_moves:
        content = last_moves.read()
        last_moves.seek(0, 0)
        last_moves.write(line.rstrip('\r\n') + '\n' + content)

def update_win_stats(winner_color):
    stats_path = 'data/win_statsC4.txt'
    if not os.path.exists(stats_path):
        with open(stats_path, 'w') as f: f.write("{'Red Heart': 0, 'Blue Heart': 0}")
    
    with open(stats_path, 'r') as file:
        stats = ast.literal_eval(file.read())
    
    stats[winner_color] = stats.get(winner_color, 0) + 1
    
    with open(stats_path, 'w') as file:
        file.write(str(stats))

def replace_text_between(original_text, marker, replacement_text):
    delimiter_a = marker['begin']
    delimiter_b = marker['end']
    if delimiter_a not in original_text or delimiter_b not in original_text:
        return original_text
    leading_text = original_text.split(delimiter_a)[0]
    trailing_text = original_text.split(delimiter_b)[1]
    return leading_text + delimiter_a + replacement_text + delimiter_b + trailing_text


def parse_issue(title):
    if title.lower() == 'connect4: start new game':
        return Action.NEW_GAME, None
    if 'connect4: put' in title.lower():
        # This regex looks for 'Connect4: Put' followed by a number 1-7
        match_obj = re.match(r'Connect4: Put ([1-7])', title, re.I)
        if match_obj:
            return Action.MOVE, int(match_obj.group(1))
    return Action.UNKNOWN, title
    
def main(issue, issue_author, repo_owner):
    action = parse_issue(issue.title)
    Conn = connect4()

    with open('data/settingsC4.yml', 'r') as settings_file:
        settings = yaml.safe_load(settings_file)

    if action[0] == Action.NEW_GAME:
        if os.path.exists('games/currentC4.p') and issue_author != repo_owner:
            issue.create_comment(settings['comments']['invalid_new_game'].format(author=issue_author))
            issue.edit(state='closed')
            return False, 'ERROR: Only owner can reset active game'
        issue.create_comment(settings['comments']['successful_new_game'].format(author=issue_author))
        issue.edit(state='closed', labels=['New Game'])
        with open('data/last_movesC4.txt', 'w') as last_moves:
            last_moves.write('Start game: ' + issue_author)
        Conn.create_newgame()

    elif action[0] == Action.MOVE:
        if not os.path.exists('games/currentC4.p'):
            return False, 'ERROR: No game in progress'

        with open('data/last_movesC4.txt') as moves:
            line = moves.readline()
            
            # Safety check: ensure the line actually has a colon
            if ':' in line:
                last_player = line.split(':')[1].strip()
                last_move   = line.split(':')[0].strip()
            else:
                # Default values if the file is new or formatted differently
                last_player = ""
                last_move = "Start game"
                
        Valid_Moves = Conn.valid_moves()
        move = action[1]

        # Check if player is moving twice in a row
        if last_player != repo_owner and last_player == issue_author and 'Start game' not in last_move:
            issue.create_comment(settings['comments']['consecutive_moves'].format(author=issue_author))
            issue.edit(state='closed', labels=['Invalid'])
            return False, 'ERROR: Two moves in a row!'
            
        # Check if move is valid    
        if move not in Valid_Moves:
            issue.create_comment(settings['comments']['invalid_move'].format(author=issue_author, move=move))
            issue.edit(state='closed', labels=['Invalid'])
            return False, f'ERROR: Move "{move}" is invalid!'

        plays, _, finished = Conn.move(move, issue_author)

        if finished == 1:
            winner_team = "Red Heart" if plays == 1 else "Blue Heart"
            update_win_stats(winner_team)
            issue.create_comment(settings['comments']['game_over'].format(
                outcome=winner_team + " won", 
                num_moves=Conn.rounds, 
                num_players=len(Conn.player), 
                players=Conn.player
            ))
            issue.edit(state='closed', labels=['Winner', winner_team])
        elif finished == 2:
            issue.create_comment(settings['comments']['game_over'].format(
                outcome="Draw", 
                num_moves=Conn.rounds, 
                num_players=len(Conn.player), 
                players=Conn.player
            ))
            issue.edit(state='closed', labels=['Draw', 'Red Heart', 'Blue Heart'])
        else:
            # plays is the NEXT player (e.g., if Blue just moved, plays is 1/Red)
            next_player_color = "Red Heart" if plays == 1 else "Blue Heart"
            
            # The player who JUST moved is the opposite of plays
            last_player_color = "Blue Heart" if plays == 1 else "Red Heart"
            
            # 1. Post comment using the color that was JUST placed
            issue.create_comment(f"Successfully placed a **{last_player_color}**! It is now {next_player_color}'s turn.")
            issue.edit(state='closed', labels=[last_player_color])

        update_last_moves(f"{move}: {issue_author}")
        update_top_moves(issue_author)

    elif action[0] == Action.UNKNOWN:
        issue.create_comment(settings['comments']['unknown_command'].format(author=issue_author) + f" Command: {action[1]}")
        issue.edit(state='closed', labels=['Invalid'])
        return False, 'ERROR: Unknown action'

    # --- README UPDATE LOGIC ---
    with open('README.md', 'r') as file:
        readme = file.read()

    # Dynamic Turn Badge Logic
    current_turn = Conn.whosturn()[0]
    t_name = "Red" if current_turn == 1 else "Blue"
    t_color = "red" if current_turn == 1 else "blue"

    turn_badge = f"![Turn](https://img.shields.io/badge/Current%20Heart's%20Color-{t_name}-{t_color}?style=for-the-badge)"

    data_map = {
        '{board_placeholder}': markdown.board_to_markdown(Conn),
        '{moves_placeholder}': markdown.generate_moves_list(Conn),
        '{turn_placeholder}': turn_badge,
        '{last_moves_placeholder}': markdown.generate_last_moves(),
        '{top_moves_placeholder}': markdown.generate_top_moves()
    }

    # Replace sections with placeholders
    readme = replace_text_between(readme, settings['markers']['board'], '{board_placeholder}')
    readme = replace_text_between(readme, settings['markers']['moves'], '{moves_placeholder}')
    readme = replace_text_between(readme, settings['markers']['turn'], f"\n{turn_badge}\n")
    readme = replace_text_between(readme, settings['markers']['last_moves'], '{last_moves_placeholder}')
    readme = replace_text_between(readme, settings['markers']['top_moves'], '{top_moves_placeholder}')

    # --- Generate Win Streak Table ---
    with open('data/win_statsC4.txt', 'r') as f:
        stats = ast.literal_eval(f.read())
        
    streak_table = (
        "| Team | Total Wins | Status |\n"
        "| :---: | :---: | :---: |\n"
        f"| ❤️ Red Heart Team ❤️ | **{stats['Red Heart']}** | {'🔥 Winning' if stats['Red Heart'] > stats['Blue Heart'] else 'Standard'} |\n"
        f"| 💙 Blue Heart Team 💙| **{stats['Blue Heart']}** | {'🔥 Winning' if stats['Blue Heart'] > stats['Red Heart'] else 'Standard'} |"
    )
    readme = replace_text_between(readme, settings['markers']['win_stats'], f"\n{streak_table}\n")

    # Final safe injection
    for placeholder, value in data_map.items():
        readme = readme.replace(placeholder, str(value))

    with open('README.md', 'w') as file:
        file.write(readme)
    return True, ''

if __name__ == '__main__':
    repo = Github(os.environ['GITHUB_TOKEN']).get_repo(os.environ['GITHUB_REPOSITORY'])
    issue = repo.get_issue(number=int(os.environ['ISSUE_NUMBER']))
    issue_author = '@' + issue.user.login
    repo_owner = '@' + os.environ['REPOSITORY_OWNER']
    try:
        ret, reason = main(issue, issue_author, repo_owner)
        if not ret: sys.exit(reason)
    except Exception:
        traceback.print_exc()
        with open('data/settingsC4.yml', 'r') as f: 
            settings = yaml.safe_load(f)
        # Simply log the error and comment on the issue without touching the workflow file
        issue.create_comment(settings['comments']['big_error'].format(author=issue_author, repo_owner=repo_owner))
        issue.edit(state='closed', labels=['Invalid'])
