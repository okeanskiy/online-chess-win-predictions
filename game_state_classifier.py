# game_state_classifier.py
# uses pretrained KNN model loaded as 'game_state_classifier.joblib' to predict game state from a board

import chess
import board_feature_extractor
from joblib import load
from sklearn.neighbors import KNeighborsClassifier
import os
import pandas as pd

knn_model = None

def _load_model():
    if not os.path.isfile('game_state_classifier.joblib'):
        raise FileNotFoundError("The file 'game_state_classifier.joblib' is not found in the current directory. Ensure that this file exists to load the model.")

    global knn_model
    knn_model = load('game_state_classifier.joblib')

def extract_predictors_from_board(board):
    move_count = board.fullmove_number - 0.5 # Starts at 0.5 instead of 1
    if board.turn == chess.WHITE:  # Adjust for half moves (this checks whose turn is next, not the current turn)
        move_count -= 0.5 # subtracts 0.5 from black

    pieces_count = board_feature_extractor.count_pieces(board)
    developed_pieces_count = board_feature_extractor.count_developed_pieces(board)
    open_files_count = board_feature_extractor.count_open_files(board)
    passed_pawns_count = board_feature_extractor.count_passed_pawns(board)

    return {
        'move_count': move_count,
        'white_pawns': pieces_count['pawns']['white'],
        'black_pawns': pieces_count['pawns']['black'],
        'white_pieces': pieces_count['pieces']['white'],
        'black_pieces': pieces_count['pieces']['black'],
        'white_developed_pieces': developed_pieces_count['white'],
        'black_developed_pieces': developed_pieces_count['black'],
        'open_files': open_files_count,
        'white_passed_pawns': passed_pawns_count['white'],
        'black_passed_pawns': passed_pawns_count['black'],
    }

def predict(predictor_df):
    if knn_model == None:
        _load_model()
    
    return knn_model.predict(predictor_df)
