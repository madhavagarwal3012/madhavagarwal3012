import os
import yaml
import ast
from urllib.parse import urlencode

with open('data/settingsC4.yml', 'r') as f:
    settings = yaml.safe_load(f)

def create_link(text, link):
    return f" [{text}]({link}) |"


def create_issue_link(source):
    base_url = settings['issues']['link'].format(repo=os.environ["GITHUB_REPOSITORY"], params="")
    # Build params separately to handle the source injection safely
    params = urlencode(settings['issues']['move']).replace("{source}", str(source))
    return f" [{source}]({base_url.split('?')[0]}?{params}) |"
    
def generate_top_moves():
    try:
        with open("data/top_movesC4.txt", 'r') as f:
            dictionary = ast.literal_eval(f.read())
    except: dictionary = {}
    
    md = "\n| Total moves | User |\n| :---: | :--- |\n"
    for user, val in sorted(dictionary.items(), key=lambda x: x[1], reverse=True)[:settings['misc']['max_top_moves']]:
        md += f"| {val} | {create_link(user, 'https://github.com/' + user[1:])} \n"
    return md


def generate_last_moves():
    md = "\n| Move | Author |\n| :---: | :--- |\n"
    try:
        with open("data/last_movesC4.txt", 'r') as f:
            lines = f.readlines()[:settings['misc']['max_last_moves']]
        for line in lines:
            if ":" in line:
                move, user = line.strip().split(":", 1)
                md += f"| `{move}` | {create_link(user.strip(), 'https://github.com/' + user.strip()[1:])} \n"
    except: pass
    return md


def generate_moves_list(board):
    if board.has_space_left() and not os.path.exists("games/currentC4.p"):
        url = settings['issues']['link'].format(repo=os.environ["GITHUB_REPOSITORY"], params=urlencode(settings['issues']['new_game']))
        return f"**GAME OVER!** [Click here to start new game]({url})\n"
    return ""


def board_to_list(board):
    board_list = []

    for line in board.split('\n'):
        sublist = []
        for item in line.split(' '):
            sublist.append(item)

        board_list.append(sublist)

    return board_list


def get_image_link(piece):
    # Standard: 0=Blank, 1=Red, 2=Blue
    imgs = {0: 'img/blank.png', 1: 'img/circles/red.png', 2: 'img/circles/blue.png'}
    return imgs.get(piece, 'img/blank.png')

def board_to_markdown(board):
    grid = board.grid
    markdown = ""

    # Header showing column numbers
    markdown += "|   | 1 | 2 | 3 | 4 | 5 | 6 | 7 |   |\n"
    markdown += "|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|\n"

    # Write board - DO NOT use reversed() if row 0 is the top
    for row in grid:
        markdown += "|   |" # Changed from |---| for cleaner look
        for elem in row:
            # You can use images OR emojis. Emojis are more reliable:
            # switcher = ["⚪", "🔴", "🔵"]
            # markdown += f" {switcher[elem]} | "
            markdown += "<img src=\"{}\" width=50px> | ".format(get_image_link(elem))
        markdown += "   |\n"

    # Footer with Move Buttons
    moves = board.valid_moves()
    markdown += "| **MOVE** |" # Added label for clarity
    for i in range(1, 8): # 1 through 7
        if i in moves:
            markdown += create_issue_link(i)
        else:
            markdown += f" {i} (Full) |"
    markdown += " |\n"

    return markdown

if __name__ == '__main__':
    nums = range(9)
    for move in nums:
        print(create_issue_link(move))
