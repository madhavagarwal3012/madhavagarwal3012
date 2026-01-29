import os
import pickle
from datetime import datetime

EAST = 1
SOUTH = 2
SOUTHEAST = 3
SOUTHWEST = 4

class connect4:
    def __init__(self):
        # Ensure the games directory exists
        if not os.path.exists("games"):
            os.makedirs("games")

        if os.path.exists("games/currentC4.p"):
            with open("games/currentC4.p", "rb") as f:
                game = pickle.load(f)
            self.grid = game['grid']
            self.whosTurn = game['plays']
            self.player = game['player']
            self.rounds = game['rounds']
            self.valid_moves()
        else:
            self.create_newgame()

    def is_game_over(self):
        if os.path.exists("games/currentC4.p"):
            return False
        return True
    
    def save_currentgame(self):
        data = {
            'grid': self.grid, 
            'plays': self.whosTurn, 
            'player': self.player,
            'rounds': self.rounds
        }
        with open("games/currentC4.p", "wb") as f:
            pickle.dump(data, f)

    def wongame(self):
        filename = "games/" + datetime.now().strftime("%m_%d_%Y-%H_%M_%S") + ".p"
        with open(filename, "wb") as f:
            pickle.dump({'grid': self.grid, 'plays': self.whosTurn, 
                        'player': self.player, 'rounds': self.rounds}, f)
        os.remove("games/currentC4.p")
    

    def create_newgame(self):
        self.grid = [[0 for col in range(7)] for row in range(6)]
        self.whosTurn = 2
        self.player = []
        self.rounds = 0
        self.save_currentgame()

    def iswonornot(self):
        for row in range(len(self.grid)):
            for col in range(len(self.grid[0])):
                if self.grid[row][col] != 0:
                    color = self.grid[row][col]
                    if self.recur_checker(self.grid, SOUTH, row + 1, col, color, 3) or \
                            self.recur_checker(self.grid, EAST, row, col + 1, color, 3) or \
                            self.recur_checker(self.grid, SOUTHEAST, row + 1, col + 1, color, 3) or \
                            self.recur_checker(self.grid, SOUTHWEST, row + 1, col - 1, color, 3):
                        return True

        return False

    def recur_checker(self, grid, direction, row, col, color, howmanyleft):
        if howmanyleft == 0:
            return True
        if (row >= len(grid)) or (col >= len(grid[0])) or (row < 0) or (col < 0):
            return False

        if grid[row][col] != color:
            return False
        if grid[row][col] == color:

            if direction == SOUTH:
                return self.recur_checker(grid, direction, row + 1, col, color, howmanyleft - 1)
            elif direction == EAST:
                return self.recur_checker(grid, direction, row, col + 1, color, howmanyleft - 1)
            elif direction == SOUTHEAST:
                return self.recur_checker(grid, direction, row + 1, col + 1, color, howmanyleft - 1)
            elif direction == SOUTHWEST:
                return self.recur_checker(grid, direction, row + 1, col - 1, color, howmanyleft - 1)
        return False

    def has_space_left(self):
        for row in self.grid:
            for col in row:
                if col == 0:
                    return True
        return False

    def whosturn(self):
        return self.whosTurn, self.valid_moves()

    def move(self, x, curr_player):
        x -= 1  # Convert 1-7 input to 0-6 index
        if x < 0 or x >= len(self.grid[0]):
            return self.whosTurn, self.valid_moves(), 4

        # FIX: Gravity Logic. We check from the bottom row (5) up to the top (0)
        row_placed = -1
        for r in range(len(self.grid) - 1, -1, -1):
            if self.grid[r][x] == 0:
                self.grid[r][x] = self.whosTurn
                row_placed = r
                break
        
        if row_placed == -1:  # Column was full
            return self.whosTurn, self.valid_moves(), 4

        # Update player list and turn
        if curr_player not in self.player:
            self.player.append(curr_player)
        
        self.rounds += 1
        
        # Check win/draw conditions
        if self.iswonornot():
            self.wongame()
            return self.whosTurn, self.valid_moves(), 1
        elif not self.has_space_left():
            self.wongame()
            return self.whosTurn, self.valid_moves(), 2
        
        # Switch turn: 1 -> 2, 2 -> 1
        self.whosTurn = (self.whosTurn % 2) + 1
        self.save_currentgame()
        return self.whosTurn, self.valid_moves(), 0

    def valid_moves(self):
        # FIX: A move is valid only if the TOP row of that column is empty
        valid = []
        for i in range(len(self.grid[0])):
            if self.grid[0][i] == 0:
                valid.append(i + 1)
        self.valid = valid
        return valid


if __name__ == '__main__':
    Conn = connect4()
    Conn.grid[2][0] = 1
    Conn.grid[3][1] = 1
    Conn.grid[4][2] = 1
    Conn.grid[5][3] = 1