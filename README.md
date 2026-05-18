# MLB Statcast ETL Pipeline

An automated data pipeline that extracts Major League Baseball (MLB) player statistics from the Statcast API, calculates advanced batting metrics (AVG and OBP), and loads the processed data into a MySQL database.

## 🚀 Features

- **Extract**: Fetches the last 14 days of MLB Statcast data using `pybaseball`.

- **Transform**: 
  - Filters raw pitch-level data into Plate Appearance outcomes.
  - Calculates **Batting Average (AVG)** and **On-Base Percentage (OBP)** using standard MLB definitions.
  - Maps MLB player IDs to player names.
  - Sorts data by team and performance (OBP).

- **Load**: Performs an optimized bulk insert into a MySQL database using `SQLAlchemy`.

## 📊 Data Logic

The pipeline calculates metrics based on the following logic:

- **Plate Appearances (PA)**: Total number of times a player has stepped to the plate.

- **At-Bats (AB)**: Calculated by subtracting walks, hit-by-pitches, sacrifice flies/bunts, and catcher interference from total Plate Appearances.

- $\Large \text{AVG} = \frac{Hits}{At Bats}$

- $\Large \text{OBP} = \frac{Hits + Walks + Hit By Pitch}{At Bats + Walks + Hit By Pitch + Sacrifice Flies}$

- $\Large \text{OBP (alt)} = \frac{Hits + Walks + Hit By Pitch}{PA - Sacrifice Bunts - Catcher Interference}$

## 🛠️ Tech Stack

- **Language**: Python 3.x
- **Data Processing**: Pandas, NumPy
- **API Wrapper**: Pybaseball
- **Database**: MySQL, SQLAlchemy, PyMySQL
- **Environment**: Dotenv for secure credential management

## 📋 Prerequisites

Before running the script, ensure you have synced and installed the dependencies:

```bash
uv sync
```

## ⚙️ Configuration

Create a MySQL server and database.

Create a .env file in the root directory of the project and provide your MySQL credentials: you can find an example in `.env.example`.

```bash
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=your_host_address
DB_PORT=your_port
DB_NAME=your_database_name
```

## 🖥️ Usage

Simply run the main script to initiate the ETL process:

```bash
uv run main.py
```

The script will output progress logs to the console:

```
--- Extracting data from Statcast ---
This is a large query, it may take a moment to complete
100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████| 14/14 [00:01<00:00,  7.61it/s]
--- Transforming data ---
Gathering player lookup table. This may take a moment.

--- Data successfully loaded to MySQL! ---
```

## 📝 Table Schema (batter_stats)

| Column      | Type  | Description                      |
|-------------|-------|----------------------------------|
| team        | TEXT  | The MLB team abbreviation        |
| batter_id   | INT   | MLBAM Player ID                  |
| batter_name | TEXT  | Full Name of the player          |
| pa          | INT   | Plate Appearances                |
| ab          | INT   | At-Bats                          |
| h           | INT   | Total Hits                       |
| bb          | INT   | Total Walks                      |
| avg         | FLOAT | Batting Average (.000 format)    |
| obp         | FLOAT | On-Base Percentage (.000 format) |

## 📊 Example Output

### Raw data from pybaseball.statcast() (pitched level)

| game_date  | player_name        | batter | events | balls | strikes | home_team | away_team | inning_topbot |
|------------|--------------------|--------|--------|-------|---------|-----------|-----------|---------------|
| 2026-05-10 | Morillo, Juan      | 683146 | walk   | 3     | 1       | AZ        | NYM       | Top           |
| 2026-05-10 | Morillo, Juan      | 683146 | NaN    | 2     | 1       | AZ        | NYM       | Top           |
| 2026-05-10 | Morillo, Juan      | 683146 | NaN    | 1     | 1       | AZ        | NYM       | Top           |
| 2026-05-10 | Morillo, Juan      | 683146 | NaN    | 0     | 1       | AZ        | NYM       | Top           |
| 2026-05-10 | Morillo, Juan      | 683146 | NaN    | 0     | 0       | AZ        | NYM       | Top           |
| 2026-05-10 | Rodriguez, Eduardo | 668901 | single | 1     | 1       | AZ        | NYM       | Top           |
| 2026-05-10 | Rodriguez, Eduardo | 668901 | NaN    | 0     | 1       | AZ        | NYM       | Top           |
| 2026-05-10 | Rodriguez, Eduardo | 668901 | NaN    | 0     | 0       | AZ        | NYM       | Top           |

### After cleaning and filtering (plate appearance level)

| team | batter_id  | events    |
|------|------------|-----------|
| NYM  | 669004     | field_out |
| NYM  | **683146** | walk      |
| NYM  | 543760     | field_out |
| NYM  | **668901** | single    |
| NYM  | 596103     | strikeout |
| AZ   | 678489     | walk      |
| AZ   | 543510     | field_out |
| AZ   | 571448     | strikeout |

### After adding flags (plate appearance level)

| team | batter_id  | events    | is_hit | is_ab_exclude | is_on_base | is_obp_ignore | is_bb |
|------|------------|-----------|--------|---------------|------------|---------------|-------|
| NYM  | 669004     | field_out | False  | False         | False      | False         | False |
| NYM  | **683146** | walk      | False  | True          | True       | False         | True  |
| NYM  | 543760     | field_out | False  | False         | False      | False         | False |
| NYM  | **668901** | single    | True   | False         | True       | False         | False |
| NYM  | 596103     | strikeout | False  | False         | False      | False         | False |
| AZ   | 678489     | walk      | False  | True          | True       | False         | True  |
| AZ   | 543510     | field_out | False  | False         | False      | False         | False |
| AZ   | 571448     | strikeout | False  | False         | False      | False         | False |

### After aggregation and calculation of avg and obp (batter level)

| team | batter_id  | pa | ab | h  | bb | is_ab_exclude | is_on_base | is_obp_ignore | avg   | obp   |
|------|------------|----|----|----|----|---------------|------------|---------------|-------|-------|
| NYM  | 669004     | 31 | 26 | 7  |  3 | 5             | 11         | 1             | 0.269 | 0.367 |
| NYM  | **683146** | 38 | 29 | 5  |  7 | 9             | 13         | 1             | 0.172 | 0.351 |
| NYM  | 543760     | 47 | 43 | 10 |  4 | 4             | 14         | 0             | 0.233 | 0.298 |
| NYM  | **668901** | 41 | 38 | 8  |  3 | 3             | 11         | 0             | 0.211 | 0.268 |
| NYM  | 596103     | 16 | 16 | 5  |  0 | 0             | 5          | 0             | 0.312 | 0.312 |
| AZ   | 678489     | 24 | 20 | 3  |  4 | 4             | 7          | 0             | 0.150 | 0.292 |
| AZ   | 543510     | 15 | 14 | 3  |  0 | 1             | 3          | 1             | 0.214 | 0.214 |
| AZ   | 571448     | 40 | 33 | 7  |  6 | 7             | 14         | 0             | 0.212 | 0.350 |

### Data from pybaseball.playerid_reverse_lookup(), adding batter_name column

| key_mlbam  | name_last | name_first | key_retro | mlb_played_first | mlb_played_last | batter_name   |
|------------|-----------|------------|-----------|------------------|-----------------|---------------|
| 669004     | melendez  | mj         | melem001  | 2022.0           | 2026.0          | Mj Melendez   |
| **683146** | baty      | brett      | batyb001  | 2022.0           | 2026.0          | Brett Baty    |
| 543760     | semien    | marcus     | semim001  | 2013.0           | 2026.0          | Marcus Semien |
| **668901** | vientos   | mark       | vienm001  | 2022.0           | 2026.0          | Mark Vientos  |
| 596103     | slater    | austin     | slata001  | 2017.0           | 2026.0          | Austin Slater |
| 678489     | barrosa   | jorge      | barrj004  | 2024.0           | 2026.0          | Jorge Barrosa |
| 543510     | mccann    | james      | mccaj001  | 2014.0           | 2026.0          | James Mccann  |
| 571448     | arenado   | nolan      | arenn001  | 2013.0           | 2026.0          | Nolan Arenado |

### Merge batter_name column back to main table and filter for needed columns (sorted by team ASC and obp DESC)

| team | batter_id  | batter_name   | pa | ab | h  | bb | avg   | obp   |
|------|------------|---------------|----|----|----|----|-------|-------|
| AZ   | 571448     | Nolan Arenado | 40 | 33 | 7  | 6  | 0.212 | 0.350 |
| AZ   | 678489     | Jorge Barrosa | 24 | 20 | 3  | 4  | 0.150 | 0.292 |
| AZ   | 543510     | James Mccann  | 15 | 14 | 3  | 0  | 0.214 | 0.214 |
| NYM  | 669004     | Mj Melendez   | 31 | 26 | 7  | 3  | 0.269 | 0.367 |
| NYM  | **683146** | Brett Baty    | 38 | 29 | 5  | 7  | 0.172 | 0.351 |
| NYM  | 596103     | Austin Slater | 16 | 16 | 5  | 0  | 0.312 | 0.312 |
| NYM  | 543760     | Marcus Semien | 47 | 43 | 10 | 4  | 0.233 | 0.298 |
| NYM  | **668901** | Mark Vientos  | 41 | 38 | 8  | 3  | 0.211 | 0.268 |

### There are some new batters that don't have names in the playerid_reverse_lookup table

| team | batter_id | batter_name | pa | ab | h | bb | avg   | obp   |
|------|-----------|-------------|----|----|---|----|-------|-------|
| SF   | 683679    | NaN         | 30 | 28 | 6 | 1  | 0.214 | 0.267 |
| ATH  | 703607    | NaN         | 15 | 13 | 5 | 1  | 0.385 | 0.400 |
| NYY  | 682987    | NaN         | 19 | 16 | 3 | 3  | 0.188 | 0.316 |

### Get missing names from MLB API and map them back to the main table

API: https://statsapi.mlb.com/api/v1/people/682987

| team | batter_id | batter_name     | pa | ab | h | bb | avg   | obp   |
|------|-----------|-----------------|----|----|---|----|-------|-------|
| SF   | 683679    | Jesus Rodriguez | 30 | 28 | 6 | 1  | 0.214 | 0.267 |
| ATH  | 703607    | Henry Bolte     | 15 | 13 | 5 | 1  | 0.385 | 0.400 |
| NYY  | 682987    | Spencer Jones   | 19 | 16 | 3 | 3  | 0.188 | 0.316 |

### Load data into database

#### For the sample players:

```sql
mysql> select * from batter_stats where batter_id in ('683146', '668901');
+------+-----------+--------------+------+------+------+------+-------+-------+
| team | batter_id | batter_name  | pa   | ab   | h    | bb   | avg   | obp   |
+------+-----------+--------------+------+------+------+------+-------+-------+
| NYM  | 683146    | Brett Baty   |   38 |   29 |    5 |    7 | 0.172 | 0.351 |
| NYM  | 668901    | Mark Vientos |   41 |   38 |    8 |    3 | 0.211 | 0.268 |
+------+-----------+--------------+------+------+------+------+-------+-------+
```

#### For the Yankees:

```sql
mysql> select * from batter_stats where team = 'NYY';
+------+-----------+------------------+------+------+------+------+-------+-------+
| team | batter_id | batter_name      | pa   | ab   | h    | bb   | avg   | obp   |
+------+-----------+------------------+------+------+------+------+-------+-------+
| NYY  | 592450    | Aaron Judge      |   54 |   43 |   15 |   10 | 0.349 | 0.481 |
| NYY  | 641355    | Cody Bellinger   |   53 |   46 |   17 |    6 |  0.37 | 0.434 |
| NYY  | 642708    | Amed Rosario     |   13 |   11 |    3 |    2 | 0.273 | 0.385 |
| NYY  | 502671    | Paul Goldschmidt |   30 |   27 |    8 |    3 | 0.296 | 0.367 |
| NYY  | 700250    | Ben Rice         |   34 |   31 |    9 |    3 |  0.29 | 0.353 |
| NYY  | 641857    | Ryan Mcmahon     |   37 |   35 |   11 |    2 | 0.314 | 0.351 |
| NYY  | 680474    | Max Schuemann    |    6 |    5 |    1 |    1 |   0.2 | 0.333 |
| NYY  | 676609    | Jos Caballero    |   41 |   36 |    8 |    3 | 0.222 | 0.317 |
| NYY  | 663757    | Trent Grisham    |   50 |   44 |    9 |    5 | 0.205 |  0.28 |
| NYY  | 669224    | Austin Wells     |   33 |   29 |    5 |    4 | 0.172 | 0.273 |
| NYY  | 641555    | J. C. Escarra    |   11 |   10 |    2 |    1 |   0.2 | 0.273 |
| NYY  | 665862    | Jazz Chisholm    |   50 |   44 |    8 |    5 | 0.182 |  0.26 |
| NYY  | 691176    | Jasson Domnguez  |   32 |   30 |    6 |    1 |   0.2 |  0.25 |
| NYY  | 682987    | Spencer Jones    |    6 |    5 |    0 |    1 |     0 | 0.167 |
+------+-----------+------------------+------+------+------+------+-------+-------+
```

