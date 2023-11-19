import json
import archives_manager

# Prompts user for game state entries and saves the data to a json file
def data_entry(player_name, game_count):
    
    # Try to load existing data, if file exists
    try:
        with open('game_state_classifier_data.json', 'r') as file:
            data = json.load(file)
            games = data['games']
    except FileNotFoundError:
        print("A json file will be created in the working directory.")
        games = []
    except json.JSONDecodeError:
        print("Error: The JSON file is corrupted or improperly formatted. Please check the file.")
        return
    
    # Filters games by those that have 'accuracies'
    archive_filter = archives_manager.build_archive_filter(rated=None, has_accuracies=True, exclude_draws=None, max_elo_diff=None)
    
    # Gets the last 50 games with the filter applied
    archived_games = archives_manager.get_most_recent_games(player_name, game_count, time_class='rapid', filter_func=archive_filter)
    
    # Begin data entry
    for archived_game in archived_games:

        # Check for duplicates
        if any(game['url'] == archived_game['url'] for game in games):
            print("This game has already been entered. Skipping duplicate entry.")
            continue

        # Prints the url for easy access
        print(archived_game['url'])

        # Asking for details of each chess game with an option to stop the process
        move_count_middle_game = input("Enter the move count for the middle game (type 'stop' to exit or 'skip' to skip to the next game): ")
        if move_count_middle_game.lower() == 'stop':
            print("Data entry stopped by user.")
            break  # Exits the loop if user inputs 'stop'
        elif move_count_middle_game.lower() == 'skip':
            continue # Continues to the next game in the list if the user inputs 'skip'
        move_count_end_game = input("Enter the move count for the end game (type 'stop' to exit or 'skip' to skip to the next game): ")
        if move_count_end_game.lower() == 'stop':
            print("Data entry stopped by user.")
            break # Exits the loop if user inputs 'stop'
        elif move_count_end_game.lower() == 'skip':
            continue # Continues to the next game in the list if the user inputs 'skip'

        move_count_middle_game = float(move_count_middle_game)
        move_count_end_game = float(move_count_end_game)

        # Appending the game data
        games.append({
            'url': archived_game['url'],
            'pgn': archived_game['pgn'],
            'move_count_middle_game': move_count_middle_game,
            'move_count_end_game': move_count_end_game
        })

        # Saving to a file
        with open('game_state_classifier_data.json', 'w') as file:
            json.dump({'games': games}, file, indent=4)

        print("Data saved to game_state_classifier_data.json")
