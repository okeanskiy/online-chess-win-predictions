# archives_manager.py
# Adam Cunningham
# Nov 7 2023

import json
import os
import requests
import re
import time


## Initialize directories
os.makedirs('json/archive_lists', exist_ok=True)
os.makedirs('json/archives', exist_ok=True)


## Initialize requests session from user-agent headers
# read user-agent json
with open('user-agent.json', 'r') as file:
    user_agent = json.load(file)

# init requests session
session = requests.session()
session.headers["User-Agent"] = f"username: {user_agent['username']}, email: {user_agent['email']}"


# requests retrieval error
class ArchiveRetrievalError(Exception):
    """Exception raised when failing to retrieve archive data from api.chess.com"""
    pass


## Monthly Archives Lists
def _jsonMonthlyArchivesListURL(player_name):
    return f"https://api.chess.com/pub/player/{player_name}/games/archives"

def _requestMonthlyArchivesList(player_name):
    time.sleep(0.5)
    response = session.get(_jsonMonthlyArchivesListURL(player_name))

    if response.status_code == 200:
        data = response.json()['archives']
        return data
    else:
        raise ArchiveRetrievalError(f"Failed to retrieve player {player_name} data: {response.status_code}")

def _monthlyArchivesFilePath(player_name):
    file_name = f'{player_name.lower()}.json'
    file_path = os.path.join('json', 'archive_lists', file_name)
    return file_path

def _monthlyArchivesListExists(player_name):
    return os.path.isfile(_monthlyArchivesFilePath(player_name))

def _saveMonthlyArchivesList(player_name, list_data):
    with open(_monthlyArchivesFilePath(player_name), 'w') as json_file:
        json.dump(list_data, json_file)

def _readMonthlyArchivesList(player_name):
    with open(_monthlyArchivesFilePath(player_name), 'r') as json_file:
        list_data = json.load(json_file)
    
    return list_data

def _getMonthlyArchivesList(player_name):
    if _monthlyArchivesListExists(player_name):
        return _readMonthlyArchivesList(player_name)
    else:
        data = _requestMonthlyArchivesList(player_name)
        _saveMonthlyArchivesList(player_name, data)
        return data


## Per-Month Archived Games (as downloaded from api.chess.com)
def _requestArchivedGames(month_url):
    time.sleep(0.5)
    response = session.get(month_url)

    if response.status_code == 200:
        data = response.json()['games']
        return data
    else:
        raise ArchiveRetrievalError(f"Failed to retrieve month archive data: {response.status_code}, URL: {month_url}")

def _archivedGamesFilePath(player_name, year, month):
    file_name = f'{player_name.lower()}.json'
    file_path = os.path.join('json', 'archives', player_name, year, f'{month}.json')
    return file_path

def _archivedGamesExists(player_name, year, month):
    return os.path.isfile(_archivedGamesFilePath(player_name, year, month))

def _saveArchivedGames(player_name, year, month, list_data):
    file_path = _archivedGamesFilePath(player_name, year, month)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, 'w') as json_file:
        json.dump(list_data, json_file)

def _readArchivedGames(player_name, year, month):
    with open(_archivedGamesFilePath(player_name, year, month), 'r') as json_file:
        list_data = json.load(json_file)
    
    return list_data

def _extract_url_data(month_url):
    url_regex = r"https://api.chess.com/pub/player/([^/]+)/games/(\d{4})/(\d{2})"
    match = re.search(url_regex, month_url)
    
    if match:
        player_name, year, month = match.groups()
        return {
            "player_name": player_name,
            "year": year,
            "month": month
        }
    else:
        return None

def _getArchivedGames(month_url):
    url_data = _extract_url_data(month_url)
    player_name, year, month = url_data['player_name'], url_data['year'], url_data['month']

    if _archivedGamesExists(player_name, year, month):
        return _readArchivedGames(player_name, year, month)
    else:
        data = _requestArchivedGames(month_url)
        _saveArchivedGames(player_name, year, month, data)
        return data

def _filterOutArchiveListAfterUnixTimestamp(monthly_archived_list, unix_timestamp):
    time_tuple = time.gmtime(unix_timestamp)
    unix_year = time_tuple.tm_year
    unix_month = time_tuple.tm_mon

    filtered_archive_list = []
    for monthly_archive_url in monthly_archived_list:
        url_data = _extract_url_data(monthly_archive_url)
        year = int(url_data['year'])
        month = int(url_data['month'])

        if year < unix_year or (year == unix_year and month <= unix_month):
            filtered_archive_list.append(monthly_archive_url)

    return filtered_archive_list

def _filterOutArchiveListBeforeUnixTimestamp(monthly_archived_list, unix_timestamp):
    time_tuple = time.gmtime(unix_timestamp)
    unix_year = time_tuple.tm_year
    unix_month = time_tuple.tm_mon

    filtered_archive_list = []
    for monthly_archive_url in monthly_archived_list:
        url_data = _extract_url_data(monthly_archive_url)
        year = int(url_data['year'])
        month = int(url_data['month'])

        if year > unix_year or (year == unix_year and month >= unix_month):
            filtered_archive_list.append(monthly_archive_url)

    return filtered_archive_list

def get_most_recent_games(player_name, num_games=100, filter_func=None):
    """
    Retrieve a list of archived games most recent to a player.

    Parameters:
    - player_name (str): The player's username on chess.com
    - num_games (int): The amount of games to include. List will be this long or include all games if not enough. Default 100.
    - filter_func (function): A function that takes a game as input and returns True if the game should be included. Default None.

    Returns:
    - list: The list of most recent archived games.
    """
    monthly_archived_list = _getMonthlyArchivesList(player_name)

    recent_archived_games = []

    for i in range(len(monthly_archived_list)):
        month_url = monthly_archived_list[-(i+1)]
        archived_games = _getArchivedGames(month_url)

        for j in range(len(archived_games)):
            archived_game = archived_games[-(j+1)]

            if filter_func is None or filter_func(archived_game):
                recent_archived_games.append(archived_game)

            if len(recent_archived_games) == num_games:
                break
        
        if len(recent_archived_games) == num_games:
                break
    
    return recent_archived_games

# legacy name
getMostRecentGames = get_most_recent_games

def get_games_between_timestamps(player_name, start_unix, end_unix, filter_func=None):
    """
    Retrieve a list of all of a player's archived games between two unix timestamps.

    Parameters:
    - player_name (str): The player's username on chess.com
    - start_unix (int): The beginning timestamp, all games will be after this.
    - end_unix (int): The end timestamp, all games will be before this.
    - filter_func (function): A function that takes an archived game as input and returns True if the game should be included. Default None.

    Returns:
    - list: The list of archived games between the two unix timestamps.
    """
    monthly_archived_list = _getMonthlyArchivesList(player_name)
    monthly_archived_list = _filterOutArchiveListAfterUnixTimestamp(monthly_archived_list, end_unix)
    monthly_archived_list = _filterOutArchiveListBeforeUnixTimestamp(monthly_archived_list, start_unix)

    recent_archived_games = []

    for i in range(len(monthly_archived_list)):
        month_url = monthly_archived_list[-(i+1)]
        archived_games = _getArchivedGames(month_url)

        for j in range(len(archived_games)):
            archived_game = archived_games[-(j+1)]

            unix_timestamp = archived_game['end_time']
            if unix_timestamp > end_unix or unix_timestamp < start_unix:
                continue

            if filter_func is None or filter_func(archived_game):
                recent_archived_games.append(archived_game)
    
    return recent_archived_games

# legacy name
getGamesBetweenTimestamps = get_games_between_timestamps

def get_opponent_name(archived_game, player_name):
    """
    Get the opponent's chess.com username from a game.

    Parameters:
    - archived_game (dict): The archived game dictionary.
    - player_name (str): The perspective player.

    Returns:
    - str: Username string of the opponent name.
    """

    if archived_game['white']['username'] == player_name:
        return archived_game['black']['username']
    elif archived_game['black']['username'] == player_name:
        return archived_game['white']['username']
    
    raise ValueError(f'Player name {player_name} not found in archived game')

def get_accuracy(archived_game, player_name):
    """
    Get the chess.com rated accuracy for this game. ValueError if accuracies are not available for this game.

    Parameters:
    - archived_game (dict): The archived game dictionary.
    - player_name (str): The perspective player.

    Returns:
    - dict: {
        'Player': The perspective player's rated accuracy.
        'Opponent': The opponent rated accuracy.
    }
    """

    white_player = archived_game['white']['username']
    black_player = archived_game['black']['username']

    if 'accuracies' not in archived_game:
        raise ValueError('accuracies not in archived game')

    white_acc = archived_game['accuracies']['white']
    black_acc = archived_game['accuracies']['black']

    player_acc = 0
    opponent_acc = 0

    if white_player == player_name:
        player_acc = white_acc
        opponent_acc = black_acc
    elif black_player == player_name:
        player_acc = black_acc
        opponent_acc = white_acc
    else:
        raise ValueError(f"Player name '{player_name}' does not match either player in the game.")
    
    return {
        'Player': player_acc,
        'Opponent': opponent_acc
    }

def get_elo(archived_game, player_name):
    """
    Get the chess.com rated elo for this game.

    Parameters:
    - archived_game (dict): The archived game dictionary.
    - player_name (str): The perspective player.

    Returns:
    - dict: {
        'Player': The perspective player's rated elo.
        'Opponent': The opponent rated elo.
    }
    """

    white_player = archived_game['white']['username']
    black_player = archived_game['black']['username']

    white_elo = archived_game['white']['rating']
    black_elo = archived_game['black']['rating']

    player_elo = 0
    opponent_elo = 0

    if white_player == player_name:
        player_elo = white_elo
        opponent_elo = black_elo
    elif black_player == player_name:
        player_elo = black_elo
        opponent_elo = white_elo
    else:
        raise ValueError(f"Player name '{player_name}' does not match either player in the game.")
    
    return {
        'Player': player_elo,
        'Opponent': opponent_elo
    }

def get_won(archived_game, player_name):
    """
    Get's the win result as an integer 1 for won, 0 for lost. ValueError if the game did not result in a win for either player (draw).

    Parameters:
    - archived_game (dict): The archived game dictionary.
    - player_name (str): The perspective player.

    Returns:
    - int: 1 if won, 0 if lost
    """

    white_player = archived_game['white']['username']
    black_player = archived_game['black']['username']

    white_result = archived_game['white']['result']
    black_result = archived_game['black']['result']

    if white_player == player_name:
        if white_result == 'win':
            return 1
        elif black_result == 'win':
            return 0
        else:
            raise ValueError(f"Archived game did not result in a win for either player")
    elif black_player == player_name:
        if white_result == 'win':
            return 0
        elif black_result == 'win':
            return 1
        else:
            raise ValueError(f"Archived game did not result in a win for either player")

    raise ValueError(f"Player name '{player_name}' does not match either player in the game.")

def _builtin_archive_filter():
    print("hi")

def build_archive_filter(rated=None, time_class=None, has_accuracies=None, exclude_draws=None):
    def filter_func(archived_game):
        if has_accuracies is not None:
            if 'accuracies' not in archived_game and has_accuracies:
                return False
            elif 'accuracies' in archived_game and not has_accuracies:
                return False

        if rated is not None and archived_game.get('rated') != rated:
            return False

        if time_class is not None and archived_game.get('time_class') != time_class:
            return False

        if exclude_draws is not None:
            white_result = archived_game.get('white', {}).get('result')
            black_result = archived_game.get('black', {}).get('result')
            if white_result == "draw" and black_result == "draw" and exclude_draws:
                return False

        return True

    return filter_func