import re
import os
import sys
import ast
from enum import Enum
from datetime import datetime

import chess
import chess.pgn
import yaml
from github import Github

import src.markdown as markdown
import src.selftest as selftest

# TODO: Use an image instead of a raw link to start new games

class Action(Enum):
    UNKNOWN = 0
    MOVE = 1
    NEW_GAME = 2


def update_top_moves(user):
    """Adds the given user to the top moves file"""
    with open('data/top_moves.txt', 'r') as file:
        contents = file.read()
        dictionary = ast.literal_eval(contents)

    if user not in dictionary:
        dictionary[user] = 1 # First move
    else:
        dictionary[user] += 1

    with open('data/top_moves.txt', 'w') as file:
        file.write(str(dictionary))


def update_last_moves(line):
    """Adds the given line to the last moves file"""
    with open('data/last_moves.txt', 'r+') as last_moves:
        content = last_moves.read()
        last_moves.seek(0, 0)
        last_moves.write(line.rstrip('\r\n') + '\n' + content)


def replace_text_between(original_text, marker, replacement_text):
    """Replace text between `marker['begin']` and `marker['end']` with `replacement`"""
    delimiter_a = marker['begin']
    delimiter_b = marker['end']

    if original_text.find(delimiter_a) == -1 or original_text.find(delimiter_b) == -1:
        return original_text

    leading_text = original_text.split(delimiter_a)[0]
    trailing_text = original_text.split(delimiter_b)[1]

    return leading_text + delimiter_a + replacement_text + delimiter_b + trailing_text

def parse_issue(title):
    """Parse issue title and return a tuple with (action, <move>)"""
    title_clean = title.lower().strip()

    if title_clean == 'chess: start new game':
        return (Action.NEW_GAME, None)

    if 'chess: move' in title_clean:
        # This regex captures:
        # 1. Source (A-H, 1-8)
        # 2. Destination (A-H, 1-8)
        # 3. Optional Promotion Piece inside parentheses or at the end
        # Example: "Chess: Move A7 to A8 (Knight)" or "Chess: Move e7e8q"
        
        # Strategy: Extract the UCI string (e7e8q) which is the last word in our new links
        parts = title_clean.split()
        move_str = parts[-1].rstrip(')').lstrip('(') 
        
        # Validation: check if it's a valid coordinate pattern
        if re.match(r'^[a-h][1-8][a-h][1-8][qrbn]?$', move_str):
            return (Action.MOVE, move_str)
            
        # Fallback for old 4-character titles
        match_obj = re.search(r'([a-h][1-8])\s*to\s*([a-h][1-8])', title_clean, re.I)
        if match_obj:
            source = match_obj.group(1)
            dest = match_obj.group(2)
            return (Action.MOVE, (source + dest).lower())

    return (Action.UNKNOWN, None) 

def main(issue, issue_author, repo_owner):
    if not os.path.exists("games"):
        os.makedirs("games")
    action = parse_issue(issue.title)
    gameboard = chess.Board()

    with open('data/settings.yaml', 'r') as settings_file:
        settings = yaml.load(settings_file, Loader=yaml.FullLoader)

    if action[0] == Action.NEW_GAME:
        with open('data/captured_data.txt', 'w') as f:
            f.close()
        if os.path.exists('games/current.pgn') and issue_author != repo_owner:
            issue.create_comment(settings['comments']['invalid_new_game'].format(author=issue_author))
            issue.edit(state='closed')
            return False, 'ERROR: A current game is in progress. Only the repo owner can start a new game'

        issue.create_comment(settings['comments']['successful_new_game'].format(author=issue_author))
        issue.edit(state='closed', labels=['New Game'])

        with open('data/last_moves.txt', 'w') as last_moves:
            last_moves.write('Start game: ' + issue_author)

        # Create new game
        game = chess.pgn.Game()
        game.headers['Event'] = repo_owner + '\'s Online Open Chess Tournament'
        game.headers['Site'] = 'https://github.com/' + os.environ['GITHUB_REPOSITORY']
        game.headers['Date'] = datetime.now().strftime('%Y.%m.%d')
        game.headers['Round'] = '1'

    elif action[0] == Action.MOVE:
        try:
            if not os.path.exists('games/current.pgn'):
                return False, 'ERROR: There is no game in progress! Start a new game first'
    
            # Load game
            with open('games/current.pgn') as pgn_file:
                game = chess.pgn.read_game(pgn_file)
                gameboard = game.board()
    
            # Replay the game to get current state
            for move in game.mainline_moves():
                gameboard.push(move)
    
            board_snapshot = markdown.board_to_markdown(gameboard, is_comment=True)
    
            # 1. Create the move object from the parsed UCI (e.g., 'e7e8q')
            try:
                move = chess.Move.from_uci(action[1])
            except ValueError:
                return False, 'ERROR: Invalid UCI format'
    
            # 2. Validation Check
            if move not in gameboard.legal_moves:
                issue.create_comment(settings['comments']['invalid_move'].format(author=issue_author, move=action[1]))
                issue.edit(state='closed', labels=['Invalid'])
                return False, 'ERROR: Move is invalid!'
    
            # 3. Prevent Double Moves
            with open('data/last_moves.txt') as moves:
                line = moves.readline()
                last_player = line.split(':')[1].strip()
                last_move = line.split(':')[0].strip()
    
            if last_player != repo_owner and last_player == issue_author and 'Start game' not in last_move:
                issue.create_comment(settings['comments']['consecutive_moves'].format(author=issue_author))
                issue.edit(state='closed', labels=['Invalid'])
                return False, 'ERROR: Two moves in a row!'
    
            # 4. Prepare the Success Message
            comment_msg = settings['comments']['successful_move'].format(author=issue_author, move=action[1])
            issue_labels = ['White' if gameboard.turn == chess.WHITE else 'Black']
    
            # Handle Promotion specifics
            if move.promotion:
                p_name = chess.piece_name(move.promotion).capitalize()
                comment_msg += f"\n\n🌟 **Pawn promoted to {p_name}!**"
                issue_labels.append('🌟 Promotion')
    
            if gameboard.is_capture(move):
                issue_labels.append('⚔️ Capture!')
                captured_piece = gameboard.piece_at(move.to_square)
                # If En Passant or unusual capture
                if captured_piece is None:
                    captured_piece = chess.Piece(chess.PAWN, not gameboard.turn)
        
                p_color = "white" if captured_piece.color == chess.WHITE else "black"
                p_name = chess.piece_name(captured_piece.piece_type)
    
                issue_id = issue.number
                with open('data/captured_data.txt', 'a') as f:
                    f.write(f"{p_color},{p_name},{action[1]},{issue_id}\n")
    
            comment_msg += "--- \n\n" 
            comment_msg += "### Board state before this move:\n"
            comment_msg += board_snapshot
    
            # 5. EXECUTE & COMMENT (Single call)
            issue.create_comment(comment_msg)
            update_last_moves(action[1] + ': ' + issue_author)
            update_top_moves(issue_author)
    
            gameboard.push(move)
            if gameboard.is_checkmate():
                issue_labels.append('🏆 Checkmate!')
            elif gameboard.is_check():
                issue_labels.append('❗ Check')
            issue.edit(state='closed', labels=issue_labels)

            game.end().add_main_variation(move, comment=issue_author)
            game.headers['Result'] = gameboard.result()

        except Exception as e:
            # 🚨 CATCH-ALL FOR CRASHES
            error_msg = f"\n 💥 **Action Error**: Something went wrong during the move execution.\n`{str(e)}`"
            issue.create_comment(error_msg)
            issue.edit(state='closed', labels=['Action Failed'])
            return False, str(e)
    

    elif action[0] == Action.UNKNOWN:
        issue.create_comment(settings['comments']['unknown_command'].format(author=issue_author))
        issue.edit(state='closed', labels=['Invalid'])
        return False, 'ERROR: Unknown action'

    # Save game to "games/current.pgn"
    print(game, file=open('games/current.pgn', 'w'), end='\n\n')

    last_moves = markdown.generate_last_moves()

    # If it is a game over, archive current game
    if gameboard.is_game_over():
        win_msg = {
            '1/2-1/2': 'It\'s a draw',
            '1-0': 'White wins',
            '0-1': 'Black wins'
        }

        with open('data/last_moves.txt', 'r') as last_moves_file:
            lines = last_moves_file.readlines()
            pattern = re.compile('.*: (@[a-z\\d](?:[a-z\\d]|-(?=[a-z\\d])){0,38})', flags=re.I)
            player_list = { re.match(pattern, line).group(1) for line in lines }

        draw_label = '👑 Draw!'
        if gameboard.is_stalemate():
            draw_label = '👑 Draw! (Stalemate)'
        elif gameboard.is_insufficient_material():
            draw_label = '👑 Draw! (Insufficient Material)'

        if gameboard.result() == '1/2-1/2':
            issue.add_to_labels(draw_label)
        else:
            issue.add_to_labels('👑 Winner!')

        issue.create_comment(settings['comments']['game_over'].format(
            outcome=win_msg.get(gameboard.result(), 'UNKNOWN'),
            players=', '.join(player_list),
            num_moves=len(lines)-1,
            num_players=len(player_list)))

        os.rename('games/current.pgn', datetime.now().strftime('games/game-%Y%m%d-%H%M%S.pgn'))
        os.remove('data/last_moves.txt')

    with open('README.md', 'r') as file:
        readme = file.read()
        readme = replace_text_between(readme, settings['markers']['board'], '{chess_board}')
        readme = replace_text_between(readme, settings['markers']['moves'], '{moves_list}')
        readme = replace_text_between(readme, settings['markers']['turn'], '{turn}')
        readme = replace_text_between(readme, settings['markers']['last_moves'], '{last_moves}')
        readme = replace_text_between(readme, settings['markers']['top_moves'], '{top_moves}')
        readme = replace_text_between(readme, settings['markers']['status_top'], '{status_top}')
        readme = replace_text_between(readme, settings['markers']['status_bottom'], '{status_bottom}')
        readme = replace_text_between(readme, settings['markers']['captured_table'], '{captured_table}')

    with open('README.md', 'w') as file:
        file.write(readme.format(
            chess_board=markdown.board_to_markdown(gameboard),
            moves_list=markdown.generate_moves_list(gameboard),
            turn=('white' if gameboard.turn == chess.WHITE else 'black'),
            last_moves=last_moves,
            top_moves=markdown.generate_top_moves(),
            status_top=markdown.generate_status_badge(gameboard),
            status_bottom=markdown.generate_status_badge(gameboard),
            captured_table=markdown.generate_captured_table() 
        ))

    return True, ''


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == '--self-test':
        selftest.run(main)
        sys.exit(0)
    else:
        repo = Github(os.environ['GITHUB_TOKEN']).get_repo(os.environ['GITHUB_REPOSITORY'])
        issue = repo.get_issue(number=int(os.environ['ISSUE_NUMBER']))
        issue_author = '@' + issue.user.login
        repo_owner = '@' + os.environ['REPOSITORY_OWNER']

    ret, reason = main(issue, issue_author, repo_owner)

    if ret == False:

        sys.exit(reason)


















