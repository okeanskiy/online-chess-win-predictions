# Pawn Structure Analysis

# Usage:
# board = chess.Board()
# analysis = PawnStructureAnalysis(board)
# open_files = analysis.count_open_files()
# semi_open_black = analysis.count_semi_open_black_files()
# ... and so on

# count_pawns(color)
# calculate_shiftness(color)
# calculate_forwardness(color)
# count_isolated_pawns(color)
# count_blockades()
# measure_tension()
# count_passed_pawns(color)
# count_doubled_pawns(color)
# count_open_files()
# count_semi_open_black_files()
# count_semi_open_white_files()
# count_closed_files()

import numpy as np
import chess
from chess import Board

class PawnStructureAnalysis:
    def __init__(self, board):
        self.board = board
        self.update()

    def push_move(self, move):
        self.board.push(move)
        self.update()

    def update(self):
        self.Bw = self._board_to_matrix(chess.WHITE, chess.PAWN)
        self.Bb = self._board_to_matrix(chess.BLACK, chess.PAWN)

    def _from_black_perspective(self, row, col):
        return 7-row, 7-col

    def _matrix_from_color(self, color):
        if color == chess.WHITE:
            return self.Bw
        elif color == chess.BLACK:
            return self.Bb
        else:
            raise ValueError('no valid color provided')

    def _board_to_matrix(self, color, piece_type):
        matrix = np.zeros((8, 8), dtype=int)
        for i in range(64):
            square = chess.SQUARES[i]
            piece = self.board.piece_at(square)
            if piece and piece.color == color and piece.piece_type == piece_type:
                row, col = divmod(square, 8)
                matrix[row, col] = 1
        return matrix

    # number of pawns
    def count_pawns(self, color):
        B = self._matrix_from_color(color)
        pawns = 0
        for r in range(8):
            for c in range(8):
                if B[r, c]:
                    pawns += 1
        return pawns

    # pawn columns => mean and variance of pawn shiftness
    def calculate_shiftness(self, color):
        B = self._matrix_from_color(color)
        col_list = []
        for r in range(1, 7):
            for c in range(8):
                if B[r, c]:
                    col_list.append(c)
        arr = np.array(col_list, dtype=np.float32)
        if color == chess.WHITE:
            arr = (arr - 3.5) / 3.5
        elif color == chess.BLACK:
            arr = ((7 - arr) - 3.5) / 3.5
        mean_shiftness, var_shiftness = arr.mean(), arr.var()
        return mean_shiftness, var_shiftness

    # pawn rows => mean and variance of pawn forwardness
    def calculate_forwardness(self, color):
        B = self._matrix_from_color(color)
        row_list = []
        for r in range(1, 7):
            for c in range(8):
                if B[r, c]:
                    row_list.append(r)
        arr = np.array(row_list, dtype=np.float32)
        if color == chess.WHITE:
            arr = (arr - 1) / 6
        elif color == chess.BLACK:
            arr = ((7 - arr) - 1) / 6
        mean_forwardness, var_forwardness = arr.mean(), arr.var()
        return mean_forwardness, var_forwardness

    # isolated pawns
    def count_isolated_pawns(self, color):
        B = self._matrix_from_color(color)
        isolated_pawns = 0
        for r in range(1, 7):
            for c in range(8):
                if B[r, c]:
                    if ((c > 0) and not np.any(B[:,c-1])) and ((c < 7) and not np.any(B[:,c+1])):
                        isolated_pawns += 1
        return isolated_pawns

    # blocked pawns
    def count_blockades(self):
        blockades = 0
        for r in range(1, 7):
            for c in range(8):
                if self.Bw[r, c] and self.Bb[r+1, c]:
                    blockades += 1
        return blockades

    # pawn tension
    def measure_tension(self):
        tension = 0
        for r in range(1, 7):
            for c in range(8):
                if self.Bw[r, c] == 1:
                    if (c > 0) and (self.Bb[r + 1, c - 1]):
                        tension += 1
                    if (c < 7) and (self.Bb[r + 1, c + 1]):
                        tension += 1
        return tension

    # passed pawns
    def _is_passed_pawn_white(self, row, col):
        for r in range(row + 1, 8):
            for c in range(max(0, col - 1), min(8, col + 2)):
                if self.Bb[r, c] == 1:
                    return False
        return True
    
    def _is_passed_pawn_black(self, row, col):
        for r in range(row - 1, 0, -1):
            for c in range(max(0, col - 1), min(8, col + 2)):
                if self.Bw[r, c] == 1:
                    return False
        return True

    def count_passed_pawns(self, color):
        B = self._matrix_from_color(color)

        passed_pawns = 0
        for row in range(7):  # No need to check the last row
            for col in range(8):
                if color == chess.WHITE:
                    r, c = row, col
                else:
                    r, c = self._from_black_perspective(row, col)
                if B[r, c] == 1:
                    if (color == chess.WHITE and self._is_passed_pawn_white(r, c)) or (self._is_passed_pawn_black(r, c)):
                        passed_pawns += 1

        return passed_pawns

    # doubled pawns
    def count_doubled_pawns(self, color):
        B = self._matrix_from_color(color)
        doubled_pawns = 0
        for c in range(8):
            pawns_in_column = np.sum(B[:, c])
            if pawns_in_column > 1:
                doubled_pawns += (pawns_in_column - 1)
        return doubled_pawns

    # open files
    def count_open_files(self):
        open_files = 0
        for c in range(8):
            if not np.any(self.Bw[:, c]) and not np.any(self.Bb[:, c]):
                open_files += 1
        return open_files

    # semi-open black files
    def count_semi_open_black_files(self):
        semi_open_black_files = 0
        for c in range(8):
            if np.any(self.Bw[:, c]) and not np.any(self.Bb[:, c]):
                semi_open_black_files += 1
        return semi_open_black_files

    # semi-open white files
    def count_semi_open_white_files(self):
        semi_open_white_files = 0
        for c in range(8):
            if np.any(self.Bb[:, c]) and not np.any(self.Bw[:, c]):
                semi_open_white_files += 1

        return semi_open_white_files

    # closed files
    def count_closed_files(self):
        closed_files = 0
        for c in range(8):
            if np.any(self.Bw[:, c]) and np.any(self.Bb[:, c]):
                closed_files += 1

        return closed_files
