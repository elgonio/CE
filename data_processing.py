from enums import char_dict, dan_names_dict
from collections import Counter
from scipy.stats import binom
from multiprocessing import Pool, cpu_count
import pandas as pd

# pandas dataframe columns
# Data columns (total 24 columns):
#  #   Column            Dtype 
# ---  ------            ----- 
#  0   battle_at         int64 
#  1   battle_id         object
#  2   battle_type       int64 
#  3   game_version      int64 
#  4   p1_chara_id       int64 
#  5   p1_name           object
#  6   p1_polaris_id     object
#  7   p1_power          int64 
#  8   p1_rank           int64 
#  9   p1_rating_before  int64 
#  10  p1_rating_change  int64 
#  11  p1_rounds         int64 
#  12  p1_user_id        int64 
#  13  p2_chara_id       int64 
#  14  p2_name           object
#  15  p2_polaris_id     object
#  16  p2_power          int64 
#  17  p2_rank           int64 
#  18  p2_rating_before  int64 
#  19  p2_rating_change  int64 
#  20  p2_rounds         int64 
#  21  p2_user_id        int64 
#  22  stage_id          int64 
#  23  winner            int64 
# dtypes: int64(19), object(5)


# get unique players with their highest rank and character
def get_unique_players(df):
    # get unique players
    # first iterate over the df and get unique players
    unique_players = {}
    for index, row in df.iterrows():
        # 1p
        if row['p1_polaris_id'] not in unique_players:
            unique_players[row['p1_polaris_id']] = {
                'rank': row['p1_rank'],
                'char': row['p1_chara_id'],
                'tekken_power': row['p1_power'],
                'area': row['p1_area_id'],
                'lang': row['p2_lang'],
                'region': row['p1_region_id'],
                'rating': int(row['p1_rating_before']) + int(row['p1_rating_change']),
                'characters': {row['p1_chara_id']},
            }
        else:
            # we have seen this player before but we want to capture all the characters they have played
            unique_players[row['p1_polaris_id']]['characters'].add(row['p1_chara_id'])

            # if the current rank is higher than the previous rank, or the character is the same but the game is newer, update the rank and character
            if row['p1_rank'] > unique_players[row['p1_polaris_id']]['rank'] or row['p1_chara_id'] == unique_players[row['p1_polaris_id']]['char']:
                unique_players[row['p1_polaris_id']]['rank'] = row['p1_rank']
                unique_players[row['p1_polaris_id']]['char'] = row['p1_chara_id']
                unique_players[row['p1_polaris_id']]['rating'] = row['p1_rating_before'] + row['p1_rating_change']

            # Let's also capture the highest tekken power
            if row['p1_power'] > unique_players[row['p1_polaris_id']]['tekken_power']:
                unique_players[row['p1_polaris_id']]['tekken_power'] = row['p1_power']
        # 2p
        if row['p2_polaris_id'] not in unique_players:
            unique_players[row['p2_polaris_id']] = {
                'rank': row['p2_rank'],
                'char': row['p2_chara_id'],
                'tekken_power': row['p2_power'],
                'area': row['p2_area_id'],
                'lang': row['p2_lang'],
                'region': row['p2_region_id'],
                'rating': int(row['p2_rating_before']) + int(row['p2_rating_change']),
                'characters': {row['p2_chara_id']},
            }
        else:
            # we have seen this player before but we want to capture all the characters they have played
            unique_players[row['p2_polaris_id']]['characters'].add(row['p2_chara_id'])

            # if the current rank is higher than the previous rank, or the character is the same but the game is newer, update the rank and character
            if row['p2_rank'] > unique_players[row['p2_polaris_id']]['rank'] or row['p2_chara_id'] == unique_players[row['p2_polaris_id']]['char']:
                unique_players[row['p2_polaris_id']]['rank'] = row['p2_rank']
                unique_players[row['p2_polaris_id']]['char'] = row['p2_chara_id']
                unique_players[row['p2_polaris_id']]['rating'] = int(row['p2_rating_before']) + int(row['p2_rating_change'])

            # Let's also capture the highest tekken power
            if row['p2_power'] > unique_players[row['p2_polaris_id']]['tekken_power']:
                unique_players[row['p2_polaris_id']]['tekken_power'] = row['p2_power']


    return unique_players

intermediate_threshold = 12
advanced_threshold = 21
master_threshold = 26

# split the unique players into 3 categories according to their highest rank
def split_unique_players(unique_players):
    # split the unique players into 3 categories according to their highest rank
    # 1. Beginners: rank 1 - 11
    # 2. Intermediate: rank 12 - 20
    # 3. Advanced: rank 21+
    # 4. Master: rank 26+
    
    beginners = {}
    intermediate = {}
    advanced = {}
    master = {}
    for user_id, data in unique_players.items():
        if data['rank'] <= intermediate_threshold:
            beginners[user_id] = data
        elif data['rank'] <= advanced_threshold:
            intermediate[user_id] = data
        elif data['rank'] <= master_threshold:
            advanced[user_id] = data
        else:
            master[user_id] = data
            
    return beginners, intermediate, advanced, master

# get the most popular characters for a given category
def get_most_popular_characters(unique_players):
    # get the most popular characters for a given category
    character_counts = {}
    for user_id, data in unique_players.items():
        char = char_dict[data['char']]
        if char not in character_counts:
            character_counts[char] = 1
        else:
            character_counts[char] += 1
    return character_counts

# get the distribution of ranks for a given category
def get_rank_distribution(unique_players):
    rank_counts = {}
    for user_id, data in unique_players.items():
        rank = data['rank']
        if rank not in rank_counts:
            rank_counts[rank] = 1
        else:
            rank_counts[rank] += 1
    return rank_counts

def calculate_percentiles(rank_counts):
    total_players = sum(rank_counts.values())
    percentiles = {}
    cumulative_count = 0

    for rank, count in sorted(rank_counts.items()):
        percentile = (cumulative_count / total_players) * 100
        percentiles[dan_names_dict[rank]] = percentile
        cumulative_count += count

    return percentiles



# split replays into 3 categories according to the rank of the players
def split_replays_into_categories(master_df):
    # split replays into 3 categories according to the rank of the players
    # get games where both gamers are beginners i.e rank 1 - 11
    beginners = master_df[(master_df['p1_rank'] <= intermediate_threshold) & (master_df['p2_rank'] <= intermediate_threshold)]
    # get games where both gamers are intermediate i.e rank 12 - 17
    intermediate = master_df[((master_df['p1_rank'] > intermediate_threshold) & (master_df['p1_rank'] <= advanced_threshold)) & ((master_df['p2_rank'] > intermediate_threshold) & (master_df['p2_rank'] <= advanced_threshold))]
    # get games where both gamers are advanced i.e rank 25+
    advanced = master_df[(master_df['p1_rank'] > advanced_threshold) & (master_df['p1_rank'] <= master_threshold) & (master_df['p2_rank'] > advanced_threshold) & (master_df['p2_rank'] <= master_threshold)]

    master = master_df[(master_df['p1_rank'] > master_threshold) & (master_df['p2_rank'] > master_threshold)]
    return beginners, intermediate, advanced, master
    
def calculate_win_rates_with_confidence_interval(master_df, confidence_level=0.95):
    # remove mirror matches
    mirror_matches = master_df[master_df['p1_chara_id'] == master_df['p2_chara_id']]
    master_df = master_df[master_df['p1_chara_id'] != master_df['p2_chara_id']]

    print(f"Number of mirror matches: {len(mirror_matches)}")

    # count the number of times each character appears in the p1_chara_id and p2_chara_id columns
    char1_counts = Counter(master_df['p1_chara_id'])
    char2_counts = Counter(master_df['p2_chara_id'])
    char_counts = char1_counts + char2_counts

    # count the number of times each character wins
    win_counts = Counter(master_df[master_df['winner'] == 1]['p1_chara_id'])
    win_counts += Counter(master_df[master_df['winner'] == 2]['p2_chara_id'])

    # calculate the win rates
    win_rates = {char_dict[k]: 0 for k in char_counts.keys()}
    intervals = {char_dict[k]: (0,0) for k in char_counts.keys()}
    for char, count in char_counts.items():
        if count != 0:
            win_rates[char_dict[char]] = win_counts[char] / count
            lower, upper = binom.interval(confidence_level, count, win_rates[char_dict[char]])
            intervals[char_dict[char]] = (lower/count, upper/count)

    # sort the win rates dictionary
    win_rates = {k: v for k, v in sorted(win_rates.items(), key=lambda item: item[1], reverse=True)}

    return win_rates, intervals

def process_chunk(chunk):
    unique_players = {}
    for index, row in chunk.iterrows():
        # Process player 1
        if row['p1_polaris_id'] not in unique_players:
            unique_players[row['p1_polaris_id']] = {
                'rank': row['p1_rank'],
                'char': row['p1_chara_id'],
                'tekken_power': row['p1_power'],
                'characters': {row['p1_chara_id']},
                'last_battle': row['battle_at'],
                'rating': row['p1_rating_before'] + row['p1_rating_change'],
                'winrate': {row['p1_chara_id']: {'wins': 0, 'losses': 0}},
                'area': row['p1_area_id'],
            }
        else:
            unique_players[row['p1_polaris_id']]['characters'].add(row['p1_chara_id'])
            if row['battle_at'] > unique_players[row['p1_polaris_id']]['last_battle']:
                unique_players[row['p1_polaris_id']]['rank'] = row['p1_rank']
                unique_players[row['p1_polaris_id']]['char'] = row['p1_chara_id']
                unique_players[row['p1_polaris_id']]['tekken_power'] = row['p1_power']
                unique_players[row['p1_polaris_id']]['last_battle'] = row['battle_at']
                unique_players[row['p1_polaris_id']]['rating'] = row['p1_rating_before'] + row['p1_rating_change']
            if row['p1_chara_id'] not in unique_players[row['p1_polaris_id']]['winrate']:
                unique_players[row['p1_polaris_id']]['winrate'][row['p1_chara_id']] = {'wins': 0, 'losses': 0}

        # Update win/loss for player 1
        if row['winner'] == 1:
            unique_players[row['p1_polaris_id']]['winrate'][row['p1_chara_id']]['wins'] += 1
            unique_players[row['p2_polaris_id']]['winrate'][row['p2_chara_id']]['losses'] += 1
        elif row['winner'] == 2:
            unique_players[row['p1_polaris_id']]['winrate'][row['p1_chara_id']]['losses'] += 1
            unique_players[row['p2_polaris_id']]['winrate'][row['p2_chara_id']]['wins'] += 1

        # Process player 2
        if row['p2_polaris_id'] not in unique_players:
            unique_players[row['p2_polaris_id']] = {
                'rank': row['p2_rank'],
                'char': row['p2_chara_id'],
                'tekken_power': row['p2_power'],
                'characters': {row['p2_chara_id']},
                'last_battle': row['battle_at'],
                'rating': row['p2_rating_before'] + row['p2_rating_change'],
                'winrate': {row['p2_chara_id']: {'wins': 0, 'losses': 0}},
                'area': row['p2_area_id'],
            }
        else:
            unique_players[row['p2_polaris_id']]['characters'].add(row['p2_chara_id'])
            if row['battle_at'] > unique_players[row['p2_polaris_id']]['last_battle']:
                unique_players[row['p2_polaris_id']]['rank'] = row['p2_rank']
                unique_players[row['p2_polaris_id']]['char'] = row['p2_chara_id']
                unique_players[row['p2_polaris_id']]['tekken_power'] = row['p2_power']
                unique_players[row['p2_polaris_id']]['last_battle'] = row['battle_at']
                unique_players[row['p2_polaris_id']]['rating'] = row['p2_rating_before'] + row['p2_rating_change']
            if row['p2_chara_id'] not in unique_players[row['p2_polaris_id']]['winrate']:
                unique_players[row['p2_polaris_id']]['winrate'][row['p2_chara_id']] = {'wins': 0, 'losses': 0}

    return unique_players

def get_unique_players_parallel(df):
    num_processes = cpu_count()
    chunk_size = len(df) // num_processes
    chunks = [df[i:i + chunk_size] for i in range(0, len(df), chunk_size)]
    
    with Pool(processes=num_processes) as pool:
        results = pool.map(process_chunk, chunks)
    
    # Merge results from all processes
    final_results = {}
    for result in results:
        for player_id, data in result.items():
            if player_id not in final_results:
                final_results[player_id] = data
            else:
                final_results[player_id]['characters'].update(data['characters'])
                if data['last_battle'] > final_results[player_id]['last_battle']:
                    final_results[player_id]['rank'] = data['rank']
                    final_results[player_id]['char'] = data['char']
                    final_results[player_id]['tekken_power'] = data['tekken_power']
                    final_results[player_id]['last_battle'] = data['last_battle']
                    final_results[player_id]['rating'] = data['rating']
                for char_id, win_loss in data['winrate'].items():
                    if char_id not in final_results[player_id]['winrate']:
                        final_results[player_id]['winrate'][char_id] = win_loss
                    else:
                        final_results[player_id]['winrate'][char_id]['wins'] += win_loss['wins']
                        final_results[player_id]['winrate'][char_id]['losses'] += win_loss['losses']
    
    return final_results