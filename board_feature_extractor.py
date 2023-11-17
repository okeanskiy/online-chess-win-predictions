# board_feature_extractor.py

import chess
from chess import Board

def count_pieces(board):
    piece_count = {'pawns': {'white': 0, 'black': 0}, 'pieces': {'white': 0, 'black': 0}}
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            if piece.piece_type == chess.PAWN:
                color = 'white' if piece.color == chess.WHITE else 'black'
                piece_count['pawns'][color] += 1
            elif piece.piece_type != chess.KING:
                color = 'white' if piece.color == chess.WHITE else 'black'
                piece_count['pieces'][color] += 1
    return piece_count

def count_developed_pieces(board):
    developed_pieces = {'white': 0, 'black': 0}
    for piece_type in range(2, 7):
        for square in board.pieces(piece_type, True):
            if square not in Board().pieces(piece_type, True):
                developed_pieces['white'] += 1
        for square in board.pieces(piece_type, False):
            if square not in Board().pieces(piece_type, False):
                developed_pieces['black'] += 1
    return developed_pieces

def count_open_files(board):
    open_files = 0
    for file_index in range(8):
        file_has_pawn = False
        for rank_index in range(8):
            square = chess.square(file_index, rank_index)
            piece = board.piece_at(square)
            if piece and piece.piece_type == chess.PAWN:
                file_has_pawn = True
                break
        if not file_has_pawn:
            open_files += 1
    return open_files

def count_passed_pawns(board):
    passed_pawns = {'white': 0, 'black': 0}
    
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.piece_type == chess.PAWN:
            square_file = chess.square_file(square)
            square_rank = chess.square_rank(square)

            is_passed = True
            # For white pawns, check squares ahead until the last rank
            if piece.color == chess.WHITE:
                for rank in range(square_rank + 1, 8):
                    for file in range(max(0, square_file - 1), min(7, square_file + 1) + 1):
                        if board.piece_at(chess.square(file, rank)) == chess.Piece(chess.PAWN, chess.BLACK):
                            is_passed = False
                            break
                    if not is_passed:
                        break
                if is_passed:
                    passed_pawns['white'] += 1
            
            # For black pawns, check squares ahead until the first rank
            elif piece.color == chess.BLACK:
                for rank in range(square_rank - 1, -1, -1):
                    for file in range(max(0, square_file - 1), min(7, square_file + 1) + 1):
                        if board.piece_at(chess.square(file, rank)) == chess.Piece(chess.PAWN, chess.WHITE):
                            is_passed = False
                            break
                    if not is_passed:
                        break
                if is_passed:
                    passed_pawns['black'] += 1

    return passed_pawns
