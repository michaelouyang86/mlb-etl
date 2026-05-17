from datetime import datetime, timedelta
import os

import numpy as np
from dotenv import load_dotenv
from pybaseball import playerid_reverse_lookup, statcast
from sqlalchemy import create_engine

# --- 1. EXTRACT ---
print("--- Extracting data from Statcast ---")
start_dt = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
end_dt = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
df = statcast(start_dt=start_dt, end_dt=end_dt)

# --- 2. TRANSFORM ---
print("--- Transforming data ---")

# Remove rows where 'events' is null (these are pitches that didn't end a Plate Appearance)
df = df.dropna(subset=['events'])

# 'Top' of the inning = Away team is batting
# 'Bot' of the inning = Home team is batting
df['team'] = np.where(df['inning_topbot'] == 'Top', df['away_team'], df['home_team'])

# Filter for needed columns
df = df[['team', 'batter', 'events']].rename(columns={'batter': 'batter_id'})

# Calculate Batting Average (AVG) and On-Base Percentage (OBP)
# AVG = Hits / At-Bats
# OBP = (Hits + Walks + Hit by Pitch) / (At-Bats + Walks + Hit by Pitch + Sacrifice Flies)
HIT_EVENTS = ['single', 'double', 'triple', 'home_run']
AT_BAT_EVENTS_EXCLUDE = ['walk', 'intent_walk', 'hit_by_pitch', 'sac_fly', 'sac_bunt', 'catcher_interf']
ON_BASE_EVENTS = HIT_EVENTS + ['walk', 'intent_walk', 'hit_by_pitch']
ON_BASE_PERCENTAGE_IGNORE = ['sac_bunt', 'catcher_interf']
BB_EVENTS = ['walk', 'intent_walk']

# Create boolean flags for each event type
df['is_hit'] = df['events'].isin(HIT_EVENTS)
df['is_ab_exclude'] = df['events'].isin(AT_BAT_EVENTS_EXCLUDE)
df['is_on_base'] = df['events'].isin(ON_BASE_EVENTS)
df['is_obp_ignore'] = df['events'].isin(ON_BASE_PERCENTAGE_IGNORE)
df['is_bb'] = df['events'].isin(BB_EVENTS)

# Aggregate statistics
batter_stats_df = df.groupby(['batter_id', 'team'], as_index=False, sort=False).agg({
    'events': 'count',       # Total Plate Appearances
    'is_hit': 'sum',         # Total Hits
    'is_ab_exclude': 'sum',  # Events to subtract to get At-Bats
    'is_on_base': 'sum',     # Numerator for OBP
    'is_obp_ignore': 'sum',  # Events to subtract to get OBP Denominator
    'is_bb': 'sum'           # Walks
}).rename(columns={
    'events': 'pa',
    'is_hit': 'h',
    'is_bb': 'bb'
})

# Calculate Batting Average (AVG)
batter_stats_df['ab'] = batter_stats_df['pa'] - batter_stats_df['is_ab_exclude']
batter_stats_df['avg'] = batter_stats_df['h'] / batter_stats_df['ab']

# Calculate On-Base Percentage (OBP)
batter_stats_df['obp'] = batter_stats_df['is_on_base'] / (batter_stats_df['pa'] - batter_stats_df['is_obp_ignore'])

# Round AVG and OBP to 3 decimal places
batter_stats_df[['avg', 'obp']] = batter_stats_df[['avg', 'obp']].round(3)

# Filter for needed columns
batter_stats_df = batter_stats_df[['team', 'batter_id', 'pa', 'ab', 'h', 'bb', 'avg', 'obp']]

# Get Batter Names (statcast only provides IDs for batters)
batter_ids = batter_stats_df['batter_id'].unique()
batter_info_df = playerid_reverse_lookup(batter_ids, key_type='mlbam')
batter_info_df['batter_name'] = batter_info_df['name_first'] + ' ' + batter_info_df['name_last']
batter_info_df['batter_name'] = batter_info_df['batter_name'].str.title()

# Merge names into our main dataframe
result_df = batter_stats_df.merge(batter_info_df[['key_mlbam', 'batter_name']], 
                                  left_on='batter_id', 
                                  right_on='key_mlbam', 
                                  how='left')
result_df = result_df[['team', 'batter_id', 'batter_name', 'pa', 'ab', 'h', 'bb', 'avg', 'obp']]

# Sort by team ascending, then OBP descending
result_df = result_df.sort_values(
    by=['team', 'obp'],
    ascending=[True, False]
)

# --- 3. LOAD ---
# Database connection information

# This will only load if a .env file is present. 
# If you're in a production 'env', this line is safely ignored.
load_dotenv()

USER = os.getenv('DB_USER')
PASSWORD = os.getenv('DB_PASSWORD')
HOST = os.getenv('DB_HOST')
PORT = os.getenv('DB_PORT')
DATABASE = os.getenv('DB_NAME')

# Create the MySQL Connection Engine
connection_string = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
engine = create_engine(connection_string)

try:
    # Write the DataFrame to MySQL
    result_df.to_sql(
        name='batter_stats',    # Table name in MySQL
        con=engine,             # Connection engine
        if_exists='replace',    # 'append' adds to existing data, 'replace' drops/recreates
        index=False,            # Don't save the Pandas index
        chunksize=5000,         # Sends data in batches for better performance
        method='multi'          # Optimizes for bulk inserts
    )
    print("\n--- Data successfully loaded to MySQL! ---")
    
except Exception as e:
    print(f"\n--- Error loading to MySQL: {e} ---")
