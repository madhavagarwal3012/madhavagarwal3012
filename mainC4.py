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
        issue.edit(state='closed')
        with open('data/last_movesC4.txt', 'w') as last_moves:
            last_moves.write('Start game: ' + issue_author)
        Conn.create_newgame()

    elif action[0] == Action.MOVE:
        if not os.path.exists('games/currentC4.p'):
            return False, 'ERROR: No game in progress'

        Valid_Moves = Conn.valid_moves()
        move = action[1]
        if move not in Valid_Moves:
            issue.create_comment(settings['comments']['invalid_move'].format(author=issue_author, move=move))
            issue.edit(state='closed', labels=['Invalid'])
            return False, f'ERROR: Move "{move}" is invalid!'

        plays, valid_moves, finished = Conn.move(move, issue_author)
        # Check turn after move to label next player
        plays_now = Conn.whosturn()[0]
        issue_labels = ['Red'] if plays_now == 2 else ['Blue']

        if finished == 1:
            won = 'Red won' if plays_now == 2 else 'Blue won'
            issue.create_comment(settings['comments']['game_over'].format(outcome=won, num_moves=Conn.rounds, num_players=len(Conn.player), players=Conn.player))
            issue.edit(state='closed', labels=issue_labels)
        elif finished == 2:
            issue.create_comment(settings['comments']['no_space'].format(num_moves=Conn.rounds, num_players=len(Conn.player), players=Conn.player))
            issue.edit(state='closed', labels=issue_labels)
        else:
            issue.create_comment(settings['comments']['successful_move'].format(author=issue_author, move=move))
            issue.edit(state='closed', labels=issue_labels)

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

    t_emoji = "🔴" if t_color == "red" else "🔵"
    turn_badge = f"## {t_emoji} {t_name} Heart's Turn"

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
    readme = replace_text_between(readme, settings['markers']['turn'], '{turn_placeholder}')
    readme = replace_text_between(readme, settings['markers']['last_moves'], '{last_moves_placeholder}')
    readme = replace_text_between(readme, settings['markers']['top_moves'], '{top_moves_placeholder}')

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
        issue.edit(labels=['bug'])
