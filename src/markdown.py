from collections import defaultdict
from urllib.parse import urlencode
import os
import re
import ast

import chess
import yaml

with open('data/settings.yaml', 'r') as settings_file:
    settings = yaml.load(settings_file, Loader=yaml.FullLoader)


def create_link(text, link):
    return f"[{text}]({link})"

def create_issue_link(source, dest_list):
    issue_link = settings['issues']['link'].format(
        repo=os.environ["GITHUB_REPOSITORY"],
        params=urlencode(settings['issues']['move'], safe="{}"))

    ret = [create_link(dest, issue_link.format(source=source, dest=dest)) for dest in sorted(dest_list)]
    return ", ".join(ret)

def generate_top_moves():
    with open("data/top_moves.txt", 'r') as file:
        dictionary = ast.literal_eval(file.read())

    markdown = "\n"
    markdown += "| Total moves |  User  |\n"
    markdown += "| :---------: | :----- |\n"

    max_entries = settings['misc']['max_top_moves']
    for key,val in sorted(dictionary.items(), key=lambda x: x[1], reverse=True)[:max_entries]:
        markdown += "| {} | {} |\n".format(val, create_link(key, "https://github.com/" + key[1:]))

    return markdown + "\n"

def generate_last_moves():
    markdown = "\n"
    markdown += "| Move | Author |\n"
    markdown += "| :--: | :----- |\n"

    counter = 0

    with open("data/last_moves.txt", 'r') as file:
        for line in file.readlines():
            parts = line.rstrip().split(':')

            if not ":" in line:
                continue

            if counter >= settings['misc']['max_last_moves']:
                break

            counter += 1

            match_obj = re.search('([A-H][1-8])([A-H][1-8])', line, re.I)
            if match_obj is not None:
                source = match_obj.group(1).upper()
                dest   = match_obj.group(2).upper()

                markdown += "| `" + source + "` to `" + dest + "` | " + create_link(parts[1], "https://github.com/" + parts[1].lstrip()[1:]) + " |\n"
            else:
                markdown += "| `" + parts[0] + "` | " + create_link(parts[1], "https://github.com/" + parts[1].lstrip()[1:]) + " |\n"

    return markdown + "\n"

def generate_moves_list(board):
    # Create dictionary and fill it
    moves_dict = defaultdict(set)

    for move in board.legal_moves:
        source = chess.SQUARE_NAMES[move.from_square].upper()
        dest   = chess.SQUARE_NAMES[move.to_square].upper()
        moves_dict[source].add(dest)

    # Write everything in Markdown format
    markdown = ""

    if board.is_game_over():
        issue_link = settings['issues']['link'].format(
            repo=os.environ["GITHUB_REPOSITORY"],
            params=urlencode(settings['issues']['new_game']))

        return "**GAME IS OVER!** " + create_link("Click here", issue_link) + " to start a new game :D\n"

    if board.is_check():
        markdown += "**CHECK!** Choose your move wisely!\n"

    markdown = "| Piece | From | To (Click to Move) |\n"
    markdown += "| :---: | :---: | :--- |\n"

    for source, dest_list in sorted(moves_dict.items()):
        square_index = chess.SQUARE_NAMES.index(source.lower())
        piece = board.piece_at(square_index)
        if piece:
            color = "white" if piece.color == chess.WHITE else "black"
            piece_name = chess.piece_name(piece.piece_type)
            # Create the small icon
            icon = f"<img src='img/{color}/{piece_name}.svg' width='24' valign='middle'>"
            
            # Format the destination links
            links = create_issue_link(source, dest_list)
            
            markdown += f"| {icon} | **{source}** | {links} |\n"

    return markdown

def generate_status_badge(board):
    current_player = "WHITE" if board.turn == chess.WHITE else "BLACK"
    icon = "⚪" if board.turn == chess.WHITE else "⚫"
    
    if board.is_checkmate():
        status, color = f"{current_player}_CHECKMATE", "red"
    elif board.is_check():
        status, color = f"{current_player}_IN_CHECK", "orange"
    else:
        # Displays "WHITE_TO_MOVE" or "BLACK_TO_MOVE"
        status, color = f"{current_player}_TO_MOVE", "green"

    badge_url = f"https://img.shields.io/badge/TURN-{status}-{color}?style=for-the-badge"
    return f"\n![Status]({badge_url})\n"
    
def generate_captured_table():
    white_lost, black_lost = [], []
    file_path = 'data/captured_data.txt'
    
    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
        return "*No pieces captured yet.*"

    with open(file_path, 'r') as f:
        for line in f:
            if not line.strip(): continue
            color, piece, uci = line.strip().split(',')
            
            # Capitalize piece name (e.g., 'pawn' -> 'Pawn')
            display_name = piece.capitalize()
            
            # Format: Image + Name + Move
            entry = f"&nbsp; <img src='img/{color}/{piece}.svg' width='22' valign='middle'> {piece.capitalize()} (`{uci}`) &nbsp;"
            
            if color == "white":
                white_lost.append(entry)
            else:
                black_lost.append(entry)

    rows = max(len(white_lost), len(black_lost))
    if rows == 0:
        return "*No pieces captured yet.*"
    
    # Start the table
    markdown = "\n"
    markdown += "| ⚪ White Pieces Lost | ⚫ Black Pieces Lost |\n"
    markdown += "| :---: | :---: |\n"
    
    for i in range(rows):
        w = white_lost[i] if i < len(white_lost) else " "
        b = black_lost[i] if i < len(black_lost) else " "
        # Ensure there are only TWO columns (one | at start, middle, and end)
        markdown += f"| {w} | {b} |\n"
    
    return markdown

def board_to_markdown(board):
    board_list = [[item for item in line.split(' ')] for line in str(board).split('\n')]
    markdown = ""

    # --- ADDED: Define your custom colors here ---
    LIGHT_SQUARE_COLOR = "#EDEAD8"  # Light: (Very Light Cream)
    DARK_SQUARE_COLOR = "#A78C6F"   # Dark: (Faded Sepia Brown)
    # ---------------------------------------------

    images = {
        "r": "img/black/rook.svg",
        "n": "img/black/knight.svg",
        "b": "img/black/bishop.svg",
        "k": "img/black/king.svg",
        "q": "img/black/queen.svg",
        "p": "img/black/pawn.svg",

        "R": "img/white/rook.svg",
        "N": "img/white/knight.svg",
        "B": "img/white/bishop.svg",
        "K": "img/white/king.svg",
        "Q": "img/white/queen.svg",
        "P": "img/white/pawn.svg",

        ".": "img/blank.png"
    }
    # ---------------------------------

    # Write header in Markdown format
    if board.turn == chess.BLACK:
        markdown += "|   | H | G | F | E | D | C | B | A |   |\n"
    else:
        markdown += "|   | A | B | C | D | E | F | G | H |   |\n"
    markdown += "|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|\n"

    # Get Rows
    rows = range(1, 9)
    rank_indexes = range(0, 8)
    
    if board.turn == chess.BLACK:
        rows = reversed(rows)
        rank_indexes = reversed(rank_indexes)

    # Write board
    for rank_index, row in zip(rank_indexes, rows):
        # NOTE: Using inline style for coordinates to match the color aesthetic
        markdown += "| <span style=\"color:#A78C6F; font-weight:bold;\">" + str(9 - row) + "</span> | "
        
        columns = board_list[rank_index]
        file_indexes = range(0, 8)
        
        if board.turn == chess.BLACK:
            columns = reversed(columns)
            file_indexes = reversed(file_indexes)

        for file_index, elem in zip(file_indexes, columns):
            # Calculate the chess square index (0 to 63)
            square = file_index + (rank_index * 8)
            
            # 🎯 FIX 1: Robust Color Check (Based on Square Index Parity)
            # This correctly determines the square's intrinsic color regardless of its content.
            is_dark = (square % 2) != (rank_index % 2)
            bg_color = DARK_SQUARE_COLOR if is_dark else LIGHT_SQUARE_COLOR
            
            # FIX 2: GitHub Styling Hack (Force DIV to cover the whole cell)
            # This ensures the background color is not overridden by the cell's default white.
            base_style = "background-color:{};".format(bg_color)
            full_cell_style = base_style + " display: block; height: 100%; margin: -8px -10px; padding: 8px 10px;"
            
            markdown += "<div style=\"{}\">".format(full_cell_style)
            # NOTE: Use the correct width (218px) for your custom pieces
            markdown += "<img src=\"{}\" width=218px></div> | ".format(images.get(elem, "???"))

        markdown += "<span style=\"color:#A78C6F; font-weight:bold;\">" + str(9 - row) + "</span> |\n"

    # Write footer in Markdown format
    if board.turn == chess.BLACK:
        markdown += "|   | <span style=\"color:#A78C6F; font-weight:bold;\">H</span> | <span style=\"color:#A78C6F; font-weight:bold;\">G</span> | <span style=\"color:#A78C6F; font-weight:bold;\">F</span> | <span style=\"color:#A78C6F; font-weight:bold;\">E</span> | <span style=\"color:#A78C6F; font-weight:bold;\">D</span> | <span style=\"color:#A78C6F; font-weight:bold;\">C</span> | <span style=\"color:#A78C6F; font-weight:bold;\">B</span> | <span style=\"color:#A78C6F; font-weight:bold;\">A</span> |   |\n"
    else:
        markdown += "|   | <span style=\"color:#A78C6F; font-weight:bold;\">A</span> | <span style=\"color:#A78C6F; font-weight:bold;\">B</span> | <span style=\"color:#A78C6F; font-weight:bold;\">C</span> | <span style=\"color:#A78C6F; font-weight:bold;\">D</span> | <span style=\"color:#A78C6F; font-weight:bold;\">E</span> | <span style=\"color:#A78C6F; font-weight:bold;\">F</span> | <span style=\"color:#A78C6F; font-weight:bold;\">G</span> | <span style=\"color:#A78C6F; font-weight:bold;\">H</span> |   |\n"

    return markdown





















