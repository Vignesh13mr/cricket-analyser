import streamlit as st
import duckdb
import pandas as pd
import os


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Cricket Analyser",
    page_icon="🏏",
    layout="wide"
)


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
    st.error("❌ Database not found!")
    st.stop()


@st.cache_resource
def get_connection():
    return duckdb.connect(
        DATABASE,
        read_only=True
    )


con = get_connection()


# ============================================================
# FORMAT AND SEASON LISTS
# ============================================================

@st.cache_data
def get_formats():

    query = """
        SELECT DISTINCT match_type
        FROM ball_by_ball
        WHERE match_type IS NOT NULL
        ORDER BY match_type
    """

    return con.execute(query).df()["match_type"].tolist()


@st.cache_data
def get_seasons():

    query = """
        SELECT DISTINCT season
        FROM ball_by_ball
        WHERE season IS NOT NULL
        ORDER BY season DESC
    """

    return con.execute(query).df()["season"].tolist()


formats = get_formats()
seasons = get_seasons()


# ============================================================
# FILTER BUILDER
# ============================================================

def create_filter_sql(selected_format, selected_season):

    conditions = []
    parameters = []

    if selected_format != "All":

        conditions.append("match_type = ?")
        parameters.append(selected_format)

    if selected_season != "All":

        conditions.append("season = ?")
        parameters.append(selected_season)

    if conditions:

        return (
            " AND " + " AND ".join(conditions),
            parameters
        )

    return "", parameters


# ============================================================
# DASHBOARD STATISTICS
# ============================================================

@st.cache_data
def get_dashboard_stats(
    selected_format,
    selected_season
):

    extra_sql, parameters = create_filter_sql(
        selected_format,
        selected_season
    )

    query = f"""
        SELECT
            COUNT(DISTINCT match_id) AS matches,
            COUNT(*) AS deliveries,
            COALESCE(SUM(runs_off_bat), 0) AS runs
        FROM ball_by_ball
        WHERE 1=1
        {extra_sql}
    """

    result = con.execute(
        query,
        parameters
    ).fetchone()

    matches = result[0] or 0
    deliveries = result[1] or 0
    runs = result[2] or 0

    wicket_query = f"""
        SELECT COUNT(*)
        FROM ball_by_ball
        WHERE player_dismissed IS NOT NULL

        AND LOWER(
            COALESCE(wicket_type, '')
        ) NOT IN (
            'run out',
            'retired hurt',
            'retired out',
            'obstructing the field'
        )

        {extra_sql}
    """

    wickets = con.execute(
        wicket_query,
        parameters
    ).fetchone()[0] or 0

    return (
        matches,
        deliveries,
        runs,
        wickets
    )


# ============================================================
# TOP BATSMEN
# ============================================================

@st.cache_data
def get_top_batsmen(
    selected_format,
    selected_season,
    limit=10
):

    extra_sql, parameters = create_filter_sql(
        selected_format,
        selected_season
    )

    query = f"""
        SELECT
            striker AS player,
            SUM(runs_off_bat) AS runs

        FROM ball_by_ball

        WHERE striker IS NOT NULL

        {extra_sql}

        GROUP BY striker

        ORDER BY runs DESC

        LIMIT ?
    """

    parameters.append(limit)

    return con.execute(
        query,
        parameters
    ).df()


# ============================================================
# TOP BOWLERS
# ============================================================

@st.cache_data
def get_top_bowlers(
    selected_format,
    selected_season,
    limit=10
):

    extra_sql, parameters = create_filter_sql(
        selected_format,
        selected_season
    )

    query = f"""
        SELECT
            bowler AS player,
            COUNT(*) AS wickets

        FROM ball_by_ball

        WHERE player_dismissed IS NOT NULL

        AND LOWER(
            COALESCE(wicket_type, '')
        ) NOT IN (
            'run out',
            'retired hurt',
            'retired out',
            'obstructing the field'
        )

        {extra_sql}

        GROUP BY bowler

        ORDER BY wickets DESC

        LIMIT ?
    """

    parameters.append(limit)

    return con.execute(
        query,
        parameters
    ).df()


# ============================================================
# RUNS BY SEASON
# ============================================================

@st.cache_data
def get_runs_by_season(selected_format, selected_season):

    filter_condition, parameters = create_filter_sql(
        selected_format,
        selected_season
    )

    query = f"""
        SELECT
            season,
            SUM(runs_off_bat) AS runs

        FROM ball_by_ball

        WHERE season IS NOT NULL
        {filter_condition}

        GROUP BY season

        ORDER BY season
    """

    return con.execute(
        query,
        parameters
    ).df()


# ============================================================
# WICKETS BY SEASON
# ============================================================

@st.cache_data
def get_wickets_by_season(selected_format, selected_season):

    filter_condition, parameters = create_filter_sql(
        selected_format,
        selected_season
    )

    query = f"""
        SELECT
            season,
            COUNT(*) AS wickets

        FROM ball_by_ball

        WHERE player_dismissed IS NOT NULL

        AND LOWER(
            COALESCE(wicket_type, '')
        ) NOT IN (
            'run out',
            'retired hurt',
            'retired out',
            'obstructing the field'
        )

        {filter_condition}

        GROUP BY season

        ORDER BY season
    """

    return con.execute(
        query,
        parameters
    ).df()


# ============================================================
# PLAYER LIST
# ============================================================

@st.cache_data
def get_players():

    query = """
        SELECT DISTINCT name

        FROM people

        WHERE name IS NOT NULL

        ORDER BY name
    """

    return con.execute(
        query
    ).df()


# ============================================================
# DETAILED BATTING STATISTICS
# ============================================================

@st.cache_data
def get_detailed_batting_stats(
    player,
    selected_format="All",
    selected_season="All"
):

    filter_condition, filter_parameters = create_filter_sql(
        selected_format,
        selected_season
    )

    query = f"""
        SELECT
            COUNT(
                DISTINCT
                CAST(match_id AS VARCHAR)
                || '-'
                || CAST(innings AS VARCHAR)
            ) AS innings,

            COALESCE(
                SUM(runs_off_bat),
                0
            ) AS runs,

            COUNT(*) AS balls,

            COUNT(
                DISTINCT match_id
            ) AS matches,

            COALESCE(
                SUM(
                    CASE
                        WHEN runs_off_bat = 4
                        THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS fours,

            COALESCE(
                SUM(
                    CASE
                        WHEN runs_off_bat = 6
                        THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS sixes

        FROM ball_by_ball

        WHERE LOWER(striker) = LOWER(?)
        {filter_condition}
    """

    result = con.execute(
        query,
        [player] + filter_parameters
    ).fetchone()

    innings = result[0] or 0
    runs = result[1] or 0
    balls = result[2] or 0
    matches = result[3] or 0
    fours = result[4] or 0
    sixes = result[5] or 0

    # --------------------------------------------------------
    # DISMISSALS
    # --------------------------------------------------------

    dismissal_query = f"""
        SELECT COUNT(*)

        FROM ball_by_ball

        WHERE LOWER(striker) = LOWER(?)

        AND player_dismissed IS NOT NULL

        AND LOWER(player_dismissed) = LOWER(?)
        {filter_condition}
    """

    dismissals = con.execute(
        dismissal_query,
        [player, player] + filter_parameters
    ).fetchone()[0] or 0

    # --------------------------------------------------------
    # BATTING AVERAGE
    # --------------------------------------------------------

    if dismissals > 0:

        average = runs / dismissals

    else:

        average = runs

    # --------------------------------------------------------
    # STRIKE RATE
    # --------------------------------------------------------

    if balls > 0:

        strike_rate = (
            runs * 100 / balls
        )

    else:

        strike_rate = 0

    # --------------------------------------------------------
    # HIGHEST SCORE
    # --------------------------------------------------------

    highest_query = f"""
        SELECT
            SUM(runs_off_bat) AS score

        FROM ball_by_ball

        WHERE LOWER(striker) = LOWER(?)
        {filter_condition}

        GROUP BY
            match_id,
            innings

        ORDER BY score DESC

        LIMIT 1
    """

    highest_result = con.execute(
        highest_query,
        [player] + filter_parameters
    ).fetchone()

    if highest_result:

        highest_score = (
            highest_result[0] or 0
        )

    else:

        highest_score = 0

    # --------------------------------------------------------
    # 50s AND 100s
    # --------------------------------------------------------

    innings_scores_query = f"""
        SELECT
            SUM(runs_off_bat) AS score

        FROM ball_by_ball

        WHERE LOWER(striker) = LOWER(?)
        {filter_condition}

        GROUP BY
            match_id,
            innings
    """

    innings_scores = con.execute(
        innings_scores_query,
        [player] + filter_parameters
    ).fetchall()

    fifties = 0
    hundreds = 0

    for row in innings_scores:

        score = row[0] or 0

        if score >= 100:

            hundreds += 1

        elif score >= 50:

            fifties += 1

    return {
        "matches": matches,
        "innings": innings,
        "runs": runs,
        "balls": balls,
        "average": average,
        "strike_rate": strike_rate,
        "highest_score": highest_score,
        "fours": fours,
        "sixes": sixes,
        "fifties": fifties,
        "hundreds": hundreds
    }


# ============================================================
# DETAILED BOWLING STATISTICS
# ============================================================

@st.cache_data
def get_detailed_bowling_stats(player, selected_format, selected_season):

    filter_condition, filter_parameters = create_filter_sql(
        selected_format,
        selected_season
    )

    query = f"""
        SELECT
            COUNT(
                DISTINCT match_id
            ) AS matches,

            COUNT(*) AS deliveries,

            COALESCE(
                SUM(runs_off_bat),
                0
            )
            +
            COALESCE(
                SUM(wides),
                0
            )
            +
            COALESCE(
                SUM(noballs),
                0
            ) AS runs_conceded

        FROM ball_by_ball

        WHERE LOWER(bowler) = LOWER(?)
        {filter_condition}
    """

    result = con.execute(
        query,
        [player] + filter_parameters
    ).fetchone()

    matches = result[0] or 0
    deliveries = result[1] or 0
    runs_conceded = result[2] or 0

    # --------------------------------------------------------
    # WICKETS
    # --------------------------------------------------------

    wickets_query = f"""
        SELECT COUNT(*)

        FROM ball_by_ball

        WHERE LOWER(bowler) = LOWER(?)

        AND player_dismissed IS NOT NULL

        AND LOWER(
            COALESCE(wicket_type, '')
        ) NOT IN (
            'run out',
            'retired hurt',
            'retired out',
            'obstructing the field'
        )
        {filter_condition}
    """

    wickets = con.execute(
        wickets_query,
        [player] + filter_parameters
    ).fetchone()[0] or 0

    # --------------------------------------------------------
    # BOWLING AVERAGE
    # --------------------------------------------------------

    if wickets > 0:

        bowling_average = (
            runs_conceded / wickets
        )

    else:

        bowling_average = 0

    # --------------------------------------------------------
    # ECONOMY
    # --------------------------------------------------------

    if deliveries > 0:

        economy = (
            runs_conceded * 6 / deliveries
        )

    else:

        economy = 0

    # --------------------------------------------------------
    # BEST BOWLING
    # --------------------------------------------------------

    best_query = f"""
        SELECT

            COUNT(
                CASE
                    WHEN player_dismissed IS NOT NULL
                    AND LOWER(
                        COALESCE(wicket_type, '')
                    ) NOT IN (
                        'run out',
                        'retired hurt',
                        'retired out',
                        'obstructing the field'
                    )
                    THEN 1
                END
            ) AS wickets,

            COALESCE(
                SUM(runs_off_bat),
                0
            )
            +
            COALESCE(
                SUM(wides),
                0
            )
            +
            COALESCE(
                SUM(noballs),
                0
            ) AS runs

        FROM ball_by_ball

        WHERE LOWER(bowler) = LOWER(?)
        {filter_condition}

        GROUP BY match_id

        ORDER BY wickets DESC, runs ASC

        LIMIT 1
    """

    best_result = con.execute(
        best_query,
        [player] + filter_parameters
    ).fetchone()

    if best_result:

        best_wickets = (
            best_result[0] or 0
        )

        best_runs = (
            best_result[1] or 0
        )

        best_figures = (
            f"{best_wickets}/{best_runs}"
        )

    else:

        best_figures = "0/0"

    return {
        "matches": matches,
        "deliveries": deliveries,
        "runs_conceded": runs_conceded,
        "wickets": wickets,
        "average": bowling_average,
        "economy": economy,
        "best": best_figures
    }


# ============================================================
# PLAYER RUNS BY SEASON
# ============================================================

@st.cache_data
def get_player_runs_by_season(player, selected_format, selected_season):

    filter_condition, filter_parameters = create_filter_sql(
        selected_format,
        selected_season
    )

    query = f"""
        SELECT
            season,
            SUM(runs_off_bat) AS runs

        FROM ball_by_ball

        WHERE LOWER(striker) = LOWER(?)
        {filter_condition}

        GROUP BY season

        ORDER BY season
    """

    return con.execute(
        query,
        [player] + filter_parameters
    ).df()


# ============================================================
# PLAYER WICKETS BY SEASON
# ============================================================

@st.cache_data
def get_player_wickets_by_season(player, selected_format, selected_season):

    filter_condition, filter_parameters = create_filter_sql(
        selected_format,
        selected_season
    )

    query = f"""
        SELECT
            season,

            COUNT(
                CASE
                    WHEN player_dismissed IS NOT NULL
                    AND LOWER(
                        COALESCE(wicket_type, '')
                    ) NOT IN (
                        'run out',
                        'retired hurt',
                        'retired out',
                        'obstructing the field'
                    )
                    THEN 1
                END
            ) AS wickets

        FROM ball_by_ball

        WHERE LOWER(bowler) = LOWER(?)
        {filter_condition}

        GROUP BY season

        ORDER BY season
    """

    return con.execute(
        query,
        [player] + filter_parameters
    ).df()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🏏 Cricket Analyser")

page = st.sidebar.radio(
    "Select Analysis",
    [
        "Dashboard",
        "Player Analysis",
        "Player Comparison",
        "Leaderboards",
        "Match Analysis"
    ]
)

st.sidebar.divider()

st.sidebar.info(
    "Python + DuckDB + Pandas + Streamlit"
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    st.title("🏏 Cricket Analyser")

    st.markdown(
        "### Cricket Statistics & Performance Dashboard"
    )

    # --------------------------------------------------------
    # FILTERS
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    selected_format = col1.selectbox(
        "🏏 Format",
        ["All"] + formats
    )

    selected_season = col2.selectbox(
        "📅 Season",
        ["All"] + seasons
    )

    st.divider()

    # --------------------------------------------------------
    # KPI CARDS
    # --------------------------------------------------------

    matches, deliveries, runs, wickets = \
        get_dashboard_stats(
            selected_format,
            selected_season
        )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🏏 Matches",
        f"{matches:,}"
    )

    c2.metric(
        "⚾ Deliveries",
        f"{deliveries:,}"
    )

    c3.metric(
        "🏃 Runs",
        f"{runs:,}"
    )

    c4.metric(
        "🎯 Wickets",
        f"{wickets:,}"
    )

    st.divider()

    # --------------------------------------------------------
    # LEADERBOARDS
    # --------------------------------------------------------

    left, right = st.columns(2)

    with left:

        st.subheader(
            "🏆 Top Run Scorers"
        )

        top_runs = get_top_batsmen(
            selected_format,
            selected_season,
            10
        )

        st.dataframe(
            top_runs,
            use_container_width=True,
            hide_index=True
        )

    with right:

        st.subheader(
            "🎯 Top Wicket Takers"
        )

        top_wickets = get_top_bowlers(
            selected_format,
            selected_season,
            10
        )

        st.dataframe(
            top_wickets,
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    # --------------------------------------------------------
    # RUNS CHART
    # --------------------------------------------------------

    st.subheader(
        "📈 Runs by Season"
    )

    runs_season = get_runs_by_season(
        selected_format,
        selected_season
    )

    if not runs_season.empty:

        runs_season = runs_season.set_index(
            "season"
        )

        st.line_chart(
            runs_season["runs"]
        )

    # --------------------------------------------------------
    # WICKETS CHART
    # --------------------------------------------------------

    st.subheader(
        "🎯 Wickets by Season"
    )

    wickets_season = get_wickets_by_season(
        selected_format,
        selected_season
    )

    if not wickets_season.empty:

        wickets_season = wickets_season.set_index(
            "season"
        )

        st.line_chart(
            wickets_season["wickets"]
        )


# ============================================================
# PLAYER ANALYSIS
# ============================================================

elif page == "Player Analysis":

    st.title("👤 Player Analysis")

    st.markdown(
        "### Detailed Player Performance"
    )

    players = get_players()["name"].tolist()

    player = st.selectbox(
        "🔎 Select Player",
        players
    )

    filter_col1, filter_col2 = st.columns(2)
    selected_format = filter_col1.selectbox(
        "🏏 Format",
        ["All"] + formats,
        key="player_analysis_format"
    )
    selected_season = filter_col2.selectbox(
        "📅 Season",
        ["All"] + seasons,
        key="player_analysis_season"
    )

    if player:

        batting = get_detailed_batting_stats(
            player,
            selected_format,
            selected_season
        )

        bowling = get_detailed_bowling_stats(
            player,
            selected_format,
            selected_season
        )

        st.divider()

        st.header(
            f"🏏 {player}"
        )

        # ====================================================
        # BATTING
        # ====================================================

        st.subheader(
            "🏏 Batting Statistics"
        )

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Matches",
            f"{batting['matches']:,}"
        )

        c2.metric(
            "Innings",
            f"{batting['innings']:,}"
        )

        c3.metric(
            "Runs",
            f"{batting['runs']:,}"
        )

        c4.metric(
            "Average",
            f"{batting['average']:.2f}"
        )

        c5.metric(
            "Strike Rate",
            f"{batting['strike_rate']:.2f}"
        )

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Highest Score",
            f"{batting['highest_score']:,}"
        )

        c2.metric(
            "50s",
            f"{batting['fifties']:,}"
        )

        c3.metric(
            "100s",
            f"{batting['hundreds']:,}"
        )

        c4.metric(
            "4s",
            f"{batting['fours']:,}"
        )

        c5.metric(
            "6s",
            f"{batting['sixes']:,}"
        )

        # ====================================================
        # BOWLING
        # ====================================================

        st.divider()

        st.subheader(
            "🎯 Bowling Statistics"
        )

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Matches",
            f"{bowling['matches']:,}"
        )

        c2.metric(
            "Deliveries",
            f"{bowling['deliveries']:,}"
        )

        c3.metric(
            "Runs Conceded",
            f"{bowling['runs_conceded']:,}"
        )

        c4.metric(
            "Wickets",
            f"{bowling['wickets']:,}"
        )

        c5.metric(
            "Economy",
            f"{bowling['economy']:.2f}"
        )

        c1, c2 = st.columns(2)

        c1.metric(
            "Bowling Average",
            f"{bowling['average']:.2f}"
        )

        c2.metric(
            "Best Bowling",
            bowling["best"]
        )

        # ====================================================
        # CHARTS
        # ====================================================

        st.divider()

        left, right = st.columns(2)

        with left:

            st.subheader(
                "📈 Runs by Season"
            )

            runs_data = get_player_runs_by_season(
                player,
                selected_format,
                selected_season
            )

            if not runs_data.empty:

                runs_data = runs_data.set_index(
                    "season"
                )

                st.line_chart(
                    runs_data["runs"]
                )

            else:

                st.info(
                    "No batting season data available."
                )

        with right:

            st.subheader(
                "🎯 Wickets by Season"
            )

            wickets_data = \
                get_player_wickets_by_season(
                    player,
                    selected_format,
                    selected_season
                )

            if not wickets_data.empty:

                wickets_data = wickets_data.set_index(
                    "season"
                )

                st.line_chart(
                    wickets_data["wickets"]
                )

            else:

                st.info(
                    "No bowling season data available."
                )

        # ====================================================
        # PLAYER SUMMARY
        # ====================================================

        st.divider()

        st.subheader(
            "📋 Player Summary"
        )

        summary = pd.DataFrame({

            "Category": [
                "Matches",
                "Batting Runs",
                "Batting Average",
                "Strike Rate",
                "Highest Score",
                "Fifties",
                "Hundreds",
                "Fours",
                "Sixes",
                "Bowling Wickets",
                "Bowling Average",
                "Economy",
                "Best Bowling"
            ],

            "Value": [
                batting["matches"],
                batting["runs"],
                f"{batting['average']:.2f}",
                f"{batting['strike_rate']:.2f}",
                batting["highest_score"],
                batting["fifties"],
                batting["hundreds"],
                batting["fours"],
                batting["sixes"],
                bowling["wickets"],
                f"{bowling['average']:.2f}",
                f"{bowling['economy']:.2f}",
                bowling["best"]
            ]
        })

        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ Download Player Summary (CSV)",
            data=summary.to_csv(index=False).encode("utf-8"),
            file_name=f"{player.lower().replace(' ', '_')}_summary.csv",
            mime="text/csv",
            key="download_player_summary"
        )


# ============================================================
# PLAYER COMPARISON
# ============================================================

elif page == "Player Comparison":

    st.title("⚔️ Player Comparison")

    filter_col1, filter_col2 = st.columns(2)
    selected_format = filter_col1.selectbox(
        "🏏 Format",
        ["All"] + formats,
        key="comparison_format"
    )
    selected_season = filter_col2.selectbox(
        "📅 Season",
        ["All"] + seasons,
        key="comparison_season"
    )

    players = get_players()["name"].tolist()

    col1, col2 = st.columns(2)

    player1 = col1.selectbox(
        "Player 1",
        players,
        key="comparison_player_1"
    )

    player2 = col2.selectbox(
        "Player 2",
        players,
        key="comparison_player_2"
    )

    p1 = get_detailed_batting_stats(
        player1,
        selected_format,
        selected_season
    )

    p2 = get_detailed_batting_stats(
        player2,
        selected_format,
        selected_season
    )

    comparison = pd.DataFrame({

        "Statistic": [
            "Matches",
            "Runs",
            "Average",
            "Strike Rate",
            "Highest Score",
            "50s",
            "100s",
            "4s",
            "6s"
        ],

        player1: [
            p1["matches"],
            p1["runs"],
            round(p1["average"], 2),
            round(p1["strike_rate"], 2),
            p1["highest_score"],
            p1["fifties"],
            p1["hundreds"],
            p1["fours"],
            p1["sixes"]
        ],

        player2: [
            p2["matches"],
            p2["runs"],
            round(p2["average"], 2),
            round(p2["strike_rate"], 2),
            p2["highest_score"],
            p2["fifties"],
            p2["hundreds"],
            p2["fours"],
            p2["sixes"]
        ]
    })

    st.subheader(
        "🏏 Batting Comparison"
    )

    st.dataframe(
        comparison,
        use_container_width=True,
        hide_index=True
    )

    st.subheader(
        "📊 Runs Comparison"
    )

    chart_data = pd.DataFrame({
        player1: [p1["runs"]],
        player2: [p2["runs"]]
    })

    st.bar_chart(
        chart_data
    )


# ============================================================
# LEADERBOARDS
# ============================================================

elif page == "Leaderboards":

    st.title("🏆 Leaderboards")

    col1, col2 = st.columns(2)

    selected_format = col1.selectbox(
        "🏏 Format",
        ["All"] + formats,
        key="leaderboard_format"
    )

    selected_season = col2.selectbox(
        "📅 Season",
        ["All"] + seasons,
        key="leaderboard_season"
    )

    number = st.slider(
        "Number of players",
        min_value=5,
        max_value=50,
        value=10
    )

    # --------------------------------------------------------
    # RUNS
    # --------------------------------------------------------

    st.subheader(
        "🏏 Top Run Scorers"
    )

    runs = get_top_batsmen(
        selected_format,
        selected_season,
        number
    )

    st.dataframe(
        runs,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "⬇️ Download Run Scorers (CSV)",
        data=runs.to_csv(index=False).encode("utf-8"),
        file_name="top_run_scorers.csv",
        mime="text/csv",
        key="download_run_scorers"
    )

    if not runs.empty:

        st.bar_chart(
            runs.set_index(
                "player"
            )["runs"]
        )

    # --------------------------------------------------------
    # WICKETS
    # --------------------------------------------------------

    st.subheader(
        "🎯 Top Wicket Takers"
    )

    wickets_df = get_top_bowlers(
        selected_format,
        selected_season,
        number
    )

    st.dataframe(
        wickets_df,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "⬇️ Download Wicket Takers (CSV)",
        data=wickets_df.to_csv(index=False).encode("utf-8"),
        file_name="top_wicket_takers.csv",
        mime="text/csv",
        key="download_wicket_takers"
    )

    if not wickets_df.empty:

        st.bar_chart(
            wickets_df.set_index(
                "player"
            )["wickets"]
        )


# ============================================================
# MATCH ANALYSIS
# ============================================================

elif page == "Match Analysis":

    st.title("🏏 Match Analysis")

    filter_col1, filter_col2 = st.columns(2)
    selected_format = filter_col1.selectbox(
        "🏏 Format",
        ["All"] + formats,
        key="match_analysis_format"
    )
    selected_season = filter_col2.selectbox(
        "📅 Season",
        ["All"] + seasons,
        key="match_analysis_season"
    )

    team = st.text_input(
        "🔎 Enter team name",
        placeholder="Example: India"
    )

    if team:

        match_filters = []
        match_filter_parameters = []

        if selected_format != "All":
            match_filters.append("b.match_type = ?")
            match_filter_parameters.append(selected_format)

        if selected_season != "All":
            match_filters.append("b.season = ?")
            match_filter_parameters.append(selected_season)

        match_filter_sql = (
            " AND " + " AND ".join(match_filters)
            if match_filters
            else ""
        )

        query = f"""
            SELECT
                mi.match_id,
                b.match_type,
                b.season,
                mi.team1,
                mi.team2,
                mi.venue,
                mi.end_date

            FROM match_info AS mi

            JOIN (
                SELECT DISTINCT match_id, match_type, season
                FROM ball_by_ball
            ) AS b
                ON CAST(b.match_id AS VARCHAR)
                 = CAST(mi.match_id AS VARCHAR)

            WHERE (LOWER(mi.team1)
                LIKE LOWER(?)

               OR LOWER(mi.team2)
                LIKE LOWER(?))
                {match_filter_sql}

            ORDER BY mi.end_date DESC

            LIMIT 50
        """

        matches = con.execute(
            query,
            [
                f"%{team}%",
                f"%{team}%"
            ] + match_filter_parameters
        ).df()

        if matches.empty:

            st.warning(
                "No matches found."
            )

        else:

            st.subheader(
                f"Matches involving {team}"
            )

            st.dataframe(
                matches,
                use_container_width=True,
                hide_index=True
            )


# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "🏏 Cricket Analyser"
)

st.sidebar.caption(
    "Powered by Python • DuckDB • Pandas • Streamlit"
)
