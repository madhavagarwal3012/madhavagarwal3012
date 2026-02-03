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

    ret = [create_link(dest, issue_link.format(source=source, dest=dest)) for dest in dest_list]
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

def generate_promotion_table(board):
    """Groups promotion moves by their starting square for better UI."""
    from collections import defaultdict
    
    # Group moves: { 'A7': [move1, move2], 'B7': [move3, move4] }
    promo_groups = defaultdict(list)
    for m in board.legal_moves:
        if m.promotion:
            source_sq = chess.SQUARE_NAMES[m.from_square].upper()
            promo_groups[source_sq].append(m)

    if not promo_groups:
        return ""

    color_str = "white" if board.turn == chess.WHITE else "black"
    repo = os.environ.get('GITHUB_REPOSITORY', 'your-user/your-repo')
    
    markdown = "### 🌟 PAWN PROMOTION AVAILABLE!\n"
    
    # Iterate through each pawn that can promote
    for source, moves in promo_groups.items():
        markdown += f"### ♟️ Promote Pawn at `{source}`\n"
        markdown += "| Piece | Type | Action |\n"
        markdown += "| :---: | :--- | :--- |\n"

        for move in moves:
            p_type = move.promotion
            p_name = chess.piece_name(p_type)
            p_char = chess.piece_symbol(p_type) 
            move_uci = f"{chess.SQUARE_NAMES[move.from_square]}{chess.SQUARE_NAMES[move.to_square]}{p_char}"
            
            body_text = "Performing%20a%20special%20pawn%20promotion%20move!%0A%0APlease%20do%20not%20change%20the%20title.%20Just%20click%20'Submit%20new%20issue'.%20You%20don't%20need%20to%20do%20anything%20else%20:D"
            link = f"https://github.com/{repo}/issues/new?title=Chess:+Move+{move_uci.upper()[:2]}+to+{move_uci.upper()[2:4]}+{move_uci.lower()}&body={body_text}"
            
            icon = f"<img src='img/{color_str}/{p_name}.svg' width='40' valign='middle'>"
            markdown += f"| {icon} | **{p_name.capitalize()}** | [Promote {source} to {p_name.capitalize()}]({link}) |\n"
        
        markdown += "\n" # Space between different pawns
    
    return markdown + "---\n"

def generate_moves_list(board):
    if board.is_game_over():
        repo = os.environ.get("GITHUB_REPOSITORY", "username/repo")
        issue_link = settings['issues']['link'].format(
            repo=repo,
            params=urlencode(settings['issues']['new_game']))
        return "**GAME IS OVER!** " + create_link("Click here", issue_link) + " to start a new game :D\n"

    markdown_output = generate_promotion_table(board)
    if markdown_output:
        markdown_output += "### ♟️ Other Legal Moves\n"

    is_black_turn = (board.turn == chess.BLACK)

    # 1. Map piece types to sort weights (Pawn -> King)
    piece_weights = {
        chess.PAWN: 1,
        chess.KNIGHT: 2,
        chess.BISHOP: 3,
        chess.ROOK: 4,
        chess.QUEEN: 5,
        chess.KING: 6
    }

    # 2. Collect moves and their piece data
    # Structure: (weight, source_name) -> set(destinations)
    moves_data = []
    
    # We use a set of sources to avoid duplicate rows for the same piece
    sources = {move.from_square for move in board.legal_moves if not move.promotion}
    
    for sq in sources:
        piece = board.piece_at(sq)
        if piece:
            weight = piece_weights.get(piece.piece_type, 7)
            source_name = chess.SQUARE_NAMES[sq].upper()
            
            # Get all legal destinations for THIS specific square
            dests = [chess.SQUARE_NAMES[m.to_square].upper() for m in board.legal_moves 
                     if m.from_square == sq and not m.promotion]
            
            moves_data.append({
                'weight': weight,
                'source': source_name,
                'piece': piece,
                'dests': sorted(dests, reverse=is_black_turn)
            })

    # 3. Sort logic: First by Piece Weight, then by Source Square
    # This keeps all Pawns together, then Knights, etc.
    moves_data.sort(key=lambda x: (x['weight'], sorted(x['source'], reverse=is_black_turn)))

    if board.is_check() and not markdown_output:
        markdown_output += "**CHECK!** Choose your move wisely!\n"

    table = "| Piece | Type | From | To (Click to Move) |\n"
    table += "| :---: | :--- | :---: | :--- |\n"

    for entry in moves_data:
        p = entry['piece']
        color_str = "white" if p.color == chess.WHITE else "black"
        p_type_name = chess.piece_name(p.piece_type).capitalize()
        icon = f"<img src='img/{color_str}/{p_type_name.lower()}.svg' width='40' valign='middle'>"
        
        links = create_issue_link(entry['source'], entry['dests'])
        table += f"| {icon} | **{p_type_name}** | `{entry['source']}` | {links} |\n"

    return markdown_output + table

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
    repo = os.environ.get("GITHUB_REPOSITORY", "username/repo")
    
    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
        return "\n #### No pieces captured yet. \n"

    with open(file_path, 'r') as f:
        for line in f:
            if not line.strip(): continue
            color, piece, uci, issue_id = line.strip().split(',')
            issue_url = f"https://github.com/{repo}/issues/{issue_id}"
            move_link = f"[`{uci}`]({issue_url})"
            
            # Capitalize piece name (e.g., 'pawn' -> 'Pawn')
            display_name = piece.capitalize()
            
            # Format: Image + Name + Move
            entry = f"&nbsp; <img src='img/{color}/{piece}.svg' width='30' valign='middle'> {piece.capitalize()} ({move_link}) &nbsp;"
            
            if color == "white":
                white_lost.append(entry)
            else:
                black_lost.append(entry)

    rows = max(len(white_lost), len(black_lost))
    if rows == 0:
        return "#### No pieces captured yet.\n"
    
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

def board_to_markdown(board, is_comment=False):
    board_list = [[item for item in line.split(' ')] for line in str(board).split('\n')]
    markdown = ""

    # If is_comment is True, we use the full raw URL so GitHub Issues can see the images.
    repo = os.environ.get("GITHUB_REPOSITORY", "username/repo")
    base_url = f"https://raw.githubusercontent.com/{repo}/master/" if is_comment else ""

    # --- ADDED: Define your custom colors here ---
    # LIGHT_SQUARE_COLOR = "#EDEAD8"  # Light: (Very Light Cream)
    # DARK_SQUARE_COLOR = "#A78C6F"   # Dark: (Faded Sepia Brown)
    # ---------------------------------------------

    # All image paths now prepend the base_url
    images = {
        "r": f"{base_url}img/black/rook.svg",
        "n": f"{base_url}img/black/knight.svg",
        "b": f"{base_url}img/black/bishop.svg",
        "k": f"{base_url}img/black/king.svg",
        "q": f"{base_url}img/black/queen.svg",
        "p": f"{base_url}img/black/pawn.svg",
        
        "R": f"{base_url}img/white/rook.svg",
        "N": f"{base_url}img/white/knight.svg",
        "B": f"{base_url}img/white/bishop.svg",
        "K": f"{base_url}img/white/king.svg",
        "Q": f"{base_url}img/white/queen.svg",
        "P": f"{base_url}img/white/pawn.svg",
        
        ".": f"{base_url}img/blank.png"
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
        # markdown += "| <span style=\"color:#A78C6F; font-weight:bold;\">" + str(9 - row) + "</span> | "

        markdown += f"| **{9 - row}** | "
        
        columns = board_list[rank_index]
        file_indexes = range(0, 8)
        
        if board.turn == chess.BLACK:
            columns = reversed(columns)
            file_indexes = reversed(file_indexes)

        for file_index, elem in zip(file_indexes, columns):
            # Calculate the chess square index (0 to 63)
            # square = file_index + (rank_index * 8)
            
            # Robust Color Check (Based on Square Index Parity)
            # This correctly determines the square's intrinsic color regardless of its content.
            # is_dark = (square % 2) != (rank_index % 2)
            # bg_color = DARK_SQUARE_COLOR if is_dark else LIGHT_SQUARE_COLOR
            
            # GitHub Styling Hack (Force DIV to cover the whole cell)
            # This ensures the background color is not overridden by the cell's default white.
            # base_style = "background-color:{};".format(bg_color)
            # full_cell_style = base_style + " display: block; height: 100%; margin: -8px -10px; padding: 8px 10px;"
            
            # markdown += "<div style=\"{}\">".format(full_cell_style)
            
            img_width = "150px" if is_comment else "218px"
            
            # markdown += f"<div style=\"{full_cell_style}\"><img src=\"{images.get(elem, '???')}\" width=\"{img_width}\"></div> | "
            markdown += f"<img src=\"{images.get(elem, '???')}\" width=\"{img_width}\"> | "

            # NOTE: Use the correct width (218px) for your custom pieces
            # markdown += f"<div style=\"{full_cell_style}\"><img src=\"{images.get(elem, '???')}\" width=\"218px\"></div> | "

        # markdown += "<span style=\"color:#A78C6F; font-weight:bold;\">" + str(9 - row) + "</span> |\n"
        markdown += f"| **{9 - row}** | "

    # Write footer in Markdown format
    # if board.turn == chess.BLACK:
        # markdown += "|   | <span style=\"color:#A78C6F; font-weight:bold;\">H</span> | <span style=\"color:#A78C6F; font-weight:bold;\">G</span> | <span style=\"color:#A78C6F; font-weight:bold;\">F</span> | <span style=\"color:#A78C6F; font-weight:bold;\">E</span> | <span style=\"color:#A78C6F; font-weight:bold;\">D</span> | <span style=\"color:#A78C6F; font-weight:bold;\">C</span> | <span style=\"color:#A78C6F; font-weight:bold;\">B</span> | <span style=\"color:#A78C6F; font-weight:bold;\">A</span> |   |\n"
    # else:
        # markdown += "|   | <span style=\"color:#A78C6F; font-weight:bold;\">A</span> | <span style=\"color:#A78C6F; font-weight:bold;\">B</span> | <span style=\"color:#A78C6F; font-weight:bold;\">C</span> | <span style=\"color:#A78C6F; font-weight:bold;\">D</span> | <span style=\"color:#A78C6F; font-weight:bold;\">E</span> | <span style=\"color:#A78C6F; font-weight:bold;\">F</span> | <span style=\"color:#A78C6F; font-weight:bold;\">G</span> | <span style=\"color:#A78C6F; font-weight:bold;\">H</span> |   |\n"

    # Footer
    if board.turn == chess.BLACK:
        markdown += "| | **H** | **G** | **F** | **E** | **D** | **C** | **B** | **A** | |\n"
    else:
        markdown += "| | **A** | **B** | **C** | **D** | **E** | **F** | **G** | **H** | |\n"
        
    return markdown











