import duckdb
import os

# ============================================================
# DATABASE
# ============================================================

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(
    PROJECT_DIR,
    "cricket_database",
    "cricket_all_tables.duckdb"
)

if not os.path.exists(DATABASE):
    print("Database not found!")
    exit()

con = duckdb.connect(DATABASE)

print("=" * 60)
print("             CRICKET ANALYSER")
print("=" * 60)
print("Database connected successfully!")


# ============================================================
# PLAYER SEARCH
# ============================================================

def search_player():

    name = input("\nEnter player name: ").strip()

    query = """
        SELECT identifier, name, unique_name
        FROM people
        WHERE LOWER(name) LIKE LOWER(?)
        ORDER BY name
        LIMIT 20
    """

    result = con.execute(query, [f"%{name}%"]).fetchall()

    if not result:
        print("\nNo player found.")
        return

    print("\nPlayers found:")
    print("-" * 60)

    for identifier, player_name, unique_name in result:
        print(f"{player_name} | {identifier}")


# ============================================================
# PLAYER BATTING STATISTICS
# ============================================================

def batting_stats():

    player = input("\nEnter exact player name: ").strip()

    query = """
        SELECT
            striker AS player,
            COUNT(DISTINCT match_id) AS matches,
            SUM(runs_off_bat) AS runs,
            COUNT(
                CASE
                    WHEN non_boundary = FALSE
                    THEN 1
                END
            ) AS balls_faced
        FROM ball_by_ball
        WHERE LOWER(striker) = LOWER(?)
        GROUP BY striker
    """

    result = con.execute(query, [player]).fetchone()

    if not result:
        print("\nPlayer not found in ball-by-ball data.")
        return

    name, matches, runs, balls = result

    if balls and balls > 0:
        strike_rate = (runs / balls) * 100
    else:
        strike_rate = 0

    print("\n" + "=" * 50)
    print("BATTING STATISTICS")
    print("=" * 50)

    print(f"Player       : {name}")
    print(f"Matches      : {matches}")
    print(f"Runs         : {runs}")
    print(f"Balls Faced  : {balls}")
    print(f"Strike Rate  : {strike_rate:.2f}")


# ============================================================
# PLAYER BOWLING STATISTICS
# ============================================================

def bowling_stats():

    player = input("\nEnter exact player name: ").strip()

    query = """
        SELECT
            bowler AS player,
            COUNT(DISTINCT match_id) AS matches,
            COUNT(*) AS deliveries,
            SUM(runs_off_bat) AS runs_conceded_bat,
            SUM(
                CASE
                    WHEN wides IS NULL THEN 0
                    ELSE wides
                END
            ) AS wides,
            SUM(
                CASE
                    WHEN noballs IS NULL THEN 0
                    ELSE noballs
                END
            ) AS no_balls
        FROM ball_by_ball
        WHERE LOWER(bowler) = LOWER(?)
        GROUP BY bowler
    """

    result = con.execute(query, [player]).fetchone()

    if not result:
        print("\nPlayer not found in bowling data.")
        return

    name, matches, deliveries, runs, wides, no_balls = result

    # Count wickets credited to bowler
    wicket_query = """
        SELECT COUNT(*)
        FROM ball_by_ball
        WHERE LOWER(bowler) = LOWER(?)
        AND player_dismissed IS NOT NULL
        AND LOWER(wicket_type) NOT IN (
            'run out',
            'retired hurt',
            'retired out',
            'obstructing the field'
        )
    """

    wickets = con.execute(
        wicket_query,
        [player]
    ).fetchone()[0]

    print("\n" + "=" * 50)
    print("BOWLING STATISTICS")
    print("=" * 50)

    print(f"Player        : {name}")
    print(f"Matches       : {matches}")
    print(f"Deliveries    : {deliveries}")
    print(f"Runs conceded : {runs}")
    print(f"Wickets       : {wickets}")

    if wickets > 0:
        print(f"Runs/Wicket   : {runs / wickets:.2f}")

    if deliveries > 0:
        economy = (runs / deliveries) * 6
        print(f"Economy       : {economy:.2f}")


# ============================================================
# TOP RUN SCORERS
# ============================================================

def top_run_scorers():

    print("\nHow many players?")
    number = int(input("Enter number: "))

    query = """
        SELECT
            striker AS player,
            SUM(runs_off_bat) AS runs,
            COUNT(DISTINCT match_id) AS matches
        FROM ball_by_ball
        GROUP BY striker
        ORDER BY runs DESC
        LIMIT ?
    """

    result = con.execute(query, [number]).fetchall()

    print("\n" + "=" * 60)
    print("TOP RUN SCORERS")
    print("=" * 60)

    print(f"{'Rank':<6}{'Player':<30}{'Runs':>10}{'Matches':>10}")
    print("-" * 60)

    for i, row in enumerate(result, 1):

        player, runs, matches = row

        print(
            f"{i:<6}"
            f"{str(player):<30}"
            f"{runs:>10}"
            f"{matches:>10}"
        )


# ============================================================
# TOP WICKET TAKERS
# ============================================================

def top_wicket_takers():

    number = int(input("\nHow many players? "))

    query = """
        SELECT
            bowler AS player,
            COUNT(*) AS wickets
        FROM ball_by_ball
        WHERE player_dismissed IS NOT NULL
        AND LOWER(wicket_type) NOT IN (
            'run out',
            'retired hurt',
            'retired out',
            'obstructing the field'
        )
        GROUP BY bowler
        ORDER BY wickets DESC
        LIMIT ?
    """

    result = con.execute(query, [number]).fetchall()

    print("\n" + "=" * 60)
    print("TOP WICKET TAKERS")
    print("=" * 60)

    print(f"{'Rank':<6}{'Player':<30}{'Wickets':>10}")
    print("-" * 60)

    for i, row in enumerate(result, 1):

        player, wickets = row

        print(
            f"{i:<6}"
            f"{str(player):<30}"
            f"{wickets:>10}"
        )


# ============================================================
# PLAYER COMPARISON
# ============================================================

def compare_players():

    player1 = input("\nEnter first player: ").strip()
    player2 = input("Enter second player: ").strip()

    query = """
        SELECT
            striker AS player,
            SUM(runs_off_bat) AS runs,
            COUNT(DISTINCT match_id) AS matches
        FROM ball_by_ball
        WHERE LOWER(striker) IN (LOWER(?), LOWER(?))
        GROUP BY striker
    """

    result = con.execute(
        query,
        [player1, player2]
    ).fetchall()

    print("\n" + "=" * 60)
    print("PLAYER COMPARISON")
    print("=" * 60)

    for player, runs, matches in result:

        print(f"\nPlayer  : {player}")
        print(f"Matches : {matches}")
        print(f"Runs    : {runs}")


# ============================================================
# MATCH SEARCH
# ============================================================

def search_matches():

    team = input("\nEnter team name: ").strip()

    query = """
        SELECT
            match_id,
            match_type,
            team1,
            team2,
            start_date,
            venue
        FROM match_info
        WHERE LOWER(team1) LIKE LOWER(?)
           OR LOWER(team2) LIKE LOWER(?)
        ORDER BY start_date DESC
        LIMIT 20
    """

    result = con.execute(
        query,
        [f"%{team}%", f"%{team}%"]
    ).fetchall()

    if not result:
        print("\nNo matches found.")
        return

    print("\n" + "=" * 80)
    print("MATCHES")
    print("=" * 80)

    for row in result:

        match_id, match_type, team1, team2, date, venue = row

        print(
            f"\nMatch ID : {match_id}"
            f"\nFormat   : {match_type}"
            f"\nTeams    : {team1} vs {team2}"
            f"\nDate     : {date}"
            f"\nVenue    : {venue}"
        )


# ============================================================
# MAIN MENU
# ============================================================

while True:

    print("\n")
    print("=" * 60)
    print("                 CRICKET ANALYSER")
    print("=" * 60)

    print("1. Search Player")
    print("2. Player Batting Statistics")
    print("3. Player Bowling Statistics")
    print("4. Top Run Scorers")
    print("5. Top Wicket Takers")
    print("6. Compare Two Players")
    print("7. Search Matches")
    print("8. Exit")

    print("=" * 60)

    choice = input("Enter your choice: ").strip()

    if choice == "1":
        search_player()

    elif choice == "2":
        batting_stats()

    elif choice == "3":
        bowling_stats()

    elif choice == "4":
        top_run_scorers()

    elif choice == "5":
        top_wicket_takers()

    elif choice == "6":
        compare_players()

    elif choice == "7":
        search_matches()

    elif choice == "8":
        print("\nThank you for using Cricket Analyser!")
        break

    else:
        print("\nInvalid choice. Please enter 1-8.")


con.close()
