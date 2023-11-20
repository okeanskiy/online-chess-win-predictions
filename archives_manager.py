# archives_manager.py
# Adam Cunningham
# Nov 7 2023

import json
import os
import requests
import re
import time
import chess
import datetime


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


# username matching
def _case_insensitive_match(str_a, str_b):
    return str.lower(str_a) == str.lower(str_b)


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

def _correct_archive_elo(archived_games, player_name):
    """
    Function used in archived game retrieval to make the rated elo for each game
    representative of what the elo was at game start, as opposed to chess.com rating after game was completed.
    """

    n = len(archived_games)

    if n < 2:
        return

    prev_player_elo = get_elo(archived_games[0], player_name)['Player']
    average_abs_elo_change = 0

    # correct games after the first one
    for archived_game in archived_games[1:]:
        uncorrected_player_elo = get_elo(archived_game, player_name)['Player']
        elo_change = uncorrected_player_elo - prev_player_elo

        white_player = archived_game['white']['username']
        if _case_insensitive_match(white_player, player_name):
            archived_game['white']['rating'] = prev_player_elo
            archived_game['black']['rating'] += elo_change
        else:
            archived_game['black']['rating'] = prev_player_elo
            archived_game['white']['rating'] += elo_change

        average_abs_elo_change += (abs(elo_change) / (n-1))
        prev_player_elo = uncorrected_player_elo

    # correct the first game as a guess based on average abs elo change
    first_game = archived_games[0]
    won = get_won(first_game, player_name)
    if won == None:
        return
    white_player = first_game['white']['username']
    average_abs_elo_change = int(round(average_abs_elo_change))
    if _case_insensitive_match(white_player, player_name):
        if won == 1:
            first_game['white']['rating'] -= average_abs_elo_change
            first_game['black']['rating'] += average_abs_elo_change
        else:
            first_game['white']['rating'] += average_abs_elo_change
            first_game['black']['rating'] -= average_abs_elo_change
    else:
        if won == 1:
            first_game['white']['rating'] += average_abs_elo_change
            first_game['black']['rating'] -= average_abs_elo_change
        else:
            first_game['white']['rating'] -= average_abs_elo_change
            first_game['black']['rating'] += average_abs_elo_change

def get_most_recent_games(player_name, num_games=100, time_class='rapid', filter_func=None, correct_elo=True, max_games_searched=None):
    """
    Retrieve a list of archived games most recent to a player.

    Parameters:
    - player_name (str): The player's username on chess.com
    - num_games (int): The amount of games to include. List will be this long or include all games if not enough. Default 100.
    - time_class (string): The name of the time class ('bullet', 'blitz', 'rapid') of chess games to pull from. Default 'rapid'.
    - filter_func (function): A function that takes a game as input and returns True if the game should be included. Default None.
    - correct_elo (bool): Toggle the correction of chess.com post-game ratings to pre-game ratings. Default True.
    - max_games_searched (int): Maximum number of games the search should internally consider, None will search (num_games * 10) times. Default None.

    Returns:
    - list: The list of most recent archived games.
    """
    if max_games_searched == None:
        max_games_searched = num_games * 10
    games_searched = 0

    monthly_archived_list = _getMonthlyArchivesList(player_name)

    recent_archived_games = []
    num_unfiltered = 0

    for i in range(len(monthly_archived_list)):
        month_url = monthly_archived_list[-(i+1)]
        archived_games = _getArchivedGames(month_url)

        for j in range(len(archived_games)):
            if num_unfiltered == num_games or games_searched == max_games_searched:
                break

            archived_game = archived_games[-(j+1)]
            games_searched += 1

            if time_class is not None and archived_game['time_class'] != time_class:
                continue

            filtered = True if (filter_func and filter_func(archived_game) == False) else False

            recent_archived_games.append({
                'game': archived_game,
                'filtered': filtered
            })

            if not filtered:
                num_unfiltered += 1

        if num_unfiltered == num_games or games_searched == max_games_searched:
                break
    
    recent_archived_games = list(reversed(recent_archived_games))

    games_list = [game_dict['game'] for game_dict in recent_archived_games]

    if correct_elo:
        _correct_archive_elo(games_list, player_name)

    if filter_func != None:
        filtered_list = [game_dict['game'] for game_dict in recent_archived_games if not game_dict['filtered']]
        return filtered_list
    else:
        return games_list

def get_games_between_timestamps(player_name, start_unix, end_unix, time_class='rapid', filter_func=None, verbose=False, correct_elo=True):
    """
    Retrieve a list of all of a player's archived games between two unix timestamps.

    Parameters:
    - player_name (str): The player's username on chess.com
    - start_unix (int): The beginning timestamp, all games will be after this.
    - end_unix (int): The end timestamp, all games will be before this.
    - time_class (string): The name of the time class ('bullet', 'blitz', 'rapid') of chess games to pull from. Default 'rapid'.
    - filter_func (function): A function that takes an archived game as input and returns True if the game should be included. Default None.
    - correct_elo (bool): Toggle the correction of chess.com post-game ratings to pre-game ratings. Default True.

    Returns:
    - list: The list of archived games between the two unix timestamps.
    """
    if verbose:
        print(f"Scanning games from {player_name} from {start_unix} to {end_unix}")

    monthly_archived_list = _getMonthlyArchivesList(player_name)
    monthly_archived_list = _filterOutArchiveListAfterUnixTimestamp(monthly_archived_list, end_unix)
    monthly_archived_list = _filterOutArchiveListBeforeUnixTimestamp(monthly_archived_list, start_unix)

    recent_archived_games = []

    for i in range(len(monthly_archived_list)):
        month_url = monthly_archived_list[-(i+1)]
        archived_games = _getArchivedGames(month_url)

        for j in range(len(archived_games)):
            archived_game = archived_games[-(j+1)]
            
            if verbose:
                print(archived_game['end_time'], archived_game['white']['username'], "v.s.", archived_game['black']['username'])

            unix_timestamp = archived_game['end_time']
            if unix_timestamp > end_unix or unix_timestamp < start_unix:
                continue

            if time_class is not None and archived_game['time_class'] != time_class:
                continue

            filtered = True if (filter_func and filter_func(archived_game) == False) else False

            recent_archived_games.append({
                'game': archived_game,
                'filtered': filtered
            })
    
    recent_archived_games = list(reversed(recent_archived_games))

    games_list = [game_dict['game'] for game_dict in recent_archived_games]

    if correct_elo:
        _correct_archive_elo(games_list, player_name)

    if filter_func != None:
        filtered_list = [game_dict['game'] for game_dict in recent_archived_games if not game_dict['filtered']]
        return filtered_list
    else:
        return games_list

def get_opponent_name(archived_game, player_name):
    """
    Get the opponent's chess.com username from a game.

    Parameters:
    - archived_game (dict): The archived game dictionary.
    - player_name (str): The perspective player.

    Returns:
    - str: Username string of the opponent name.
    """

    white_username = archived_game['white']['username']
    black_username = archived_game['black']['username']

    if _case_insensitive_match(white_username, player_name):
        return black_username
    elif _case_insensitive_match(black_username, player_name):
        return white_username
    
    raise ValueError(f'Player name {player_name} not found in archived game')

def get_accuracy(archived_game, player_name):
    """
    Get the chess.com rated accuracy for this game. Returns 'None' if accuracies are not available for this game.

    Parameters:
    - archived_game (dict): The archived game dictionary.
    - player_name (str): The perspective player.

    Returns:
    - dict: {
        'Player': The perspective player's rated accuracy.
        'Opponent': The opponent rated accuracy.
    }
    or None if accuracies not available for this game.
    """

    white_player = archived_game['white']['username']
    black_player = archived_game['black']['username']

    if 'accuracies' not in archived_game:
        return None

    white_acc = archived_game['accuracies']['white']
    black_acc = archived_game['accuracies']['black']

    player_acc = 0
    opponent_acc = 0

    if _case_insensitive_match(white_player, player_name):
        player_acc = white_acc
        opponent_acc = black_acc
    elif _case_insensitive_match(black_player, player_name):
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

    if _case_insensitive_match(white_player, player_name):
        player_elo = white_elo
        opponent_elo = black_elo
    elif _case_insensitive_match(black_player, player_name):
        player_elo = black_elo
        opponent_elo = white_elo
    else:
        raise ValueError(f"Player name '{player_name}' does not match either player in the game.")
    
    return {
        'Player': player_elo,
        'Opponent': opponent_elo
    }

def get_color(archived_game, player_name):
    white_player = archived_game['white']['username']
    black_player = archived_game['black']['username']

    if _case_insensitive_match(white_player, player_name):
        return True
    elif _case_insensitive_match(black_player, player_name):
        return False
    
    raise ValueError(f"Player name '{player_name}' does not match either player in the game.")

def get_won(archived_game, player_name):
    """
    Get's the win result as an integer 1 for won, 0 for lost. ValueError if the game did not result in a win for either player (draw).

    Parameters:
    - archived_game (dict): The archived game dictionary.
    - player_name (str): The perspective player.

    Returns:
    - int: 1 if won, 0 if lost, or None if draw
    """

    white_player = archived_game['white']['username']
    black_player = archived_game['black']['username']

    white_result = archived_game['white']['result']
    black_result = archived_game['black']['result']

    if _case_insensitive_match(white_player, player_name):
        if white_result == 'win':
            return 1
        elif black_result == 'win':
            return 0
        else:
            return None
    elif _case_insensitive_match(black_player, player_name):
        if white_result == 'win':
            return 0
        elif black_result == 'win':
            return 1
        else:
            return None

    raise ValueError(f"Player name '{player_name}' does not match either player in the game.")

def build_archive_filter(rated=None, has_accuracies=None, exclude_draws=None, max_elo_diff=None, rules='chess'):
    def filter_func(archived_game):
        if max_elo_diff is not None:
            elo_diff = archived_game['white']['rating'] - archived_game['black']['rating']
            if abs(elo_diff) > max_elo_diff:
                return False

        if has_accuracies is not None:
            if 'accuracies' not in archived_game and has_accuracies:
                return False
            elif 'accuracies' in archived_game and not has_accuracies:
                return False

        if rated is not None and archived_game.get('rated') != rated:
            return False

        if exclude_draws is not None:
            white_result = archived_game.get('white', {}).get('result')
            black_result = archived_game.get('black', {}).get('result')
            if white_result != "win" and black_result != "win":
                return False

        if rules is not None and archived_game.get('rules') != rules:
            return False

        return True

    return filter_func

def simplified_archived_game(archived_game):
    date_time = datetime.datetime.fromtimestamp(archived_game['end_time'])
    formatted_date = date_time.strftime('%Y.%m.%d')

    simplified =  {
        'url': archived_game['url'],
        'end_time': archived_game['end_time'],
        'date': formatted_date,
        'rated': archived_game['rated'],
        'time_class': archived_game['time_class']
    }

    for color in ['white', 'black']:
        simplified[color] = {
            'username': archived_game[color]['username'],
            'rating': archived_game[color]['rating'],
            'result': archived_game[color]['result']
        }

    return simplified
