import streamlit as st
import nflreadpy as nfl
import polars as pl

# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------

st.set_page_config(
    page_title="Sports by the Numbers Fantasy Football",
    page_icon="🏈",
    layout="wide"
)

st.title("🏈 Sports by the Numbers")
st.subheader("Fantasy Football Weekly Score Calculator")

st.write(
    "Choose the NFL week and your team's starting lineup. "
    "The calculator uses real NFL statistics to calculate your score."
)

SEASON = 2026


# --------------------------------------------------
# LOAD NFL DATA
# --------------------------------------------------

@st.cache_data(ttl=3600)
def load_nfl_data():
    stats = nfl.load_player_stats(
        seasons=[SEASON],
        summary_level="week"
    )

    rosters = nfl.load_rosters_weekly(
        seasons=[SEASON]
    )

    return stats, rosters


try:
    stats, rosters = load_nfl_data()

except Exception as e:
    st.error("The NFL data could not be loaded right now.")
    st.write("Please try again later.")
    st.caption(str(e))
    st.stop()


# --------------------------------------------------
# AVAILABLE WEEKS
# --------------------------------------------------

available_weeks = (
    stats
    .select("week")
    .unique()
    .sort("week")
    .to_series()
    .to_list()
)

if not available_weeks:
    st.warning("No NFL weekly statistics are available yet.")
    st.stop()


week = st.selectbox(
    "🏈 Select NFL Week",
    available_weeks,
    index=len(available_weeks) - 1
)


week_stats = stats.filter(
    pl.col("week") == week
)


# --------------------------------------------------
# GET THE ROSTER FOR THE SELECTED WEEK
# --------------------------------------------------

if "week" in rosters.columns:
    week_rosters = rosters.filter(
        pl.col("week") == week
    )
else:
    week_rosters = rosters


# --------------------------------------------------
# FIND CORRECT COLUMN NAMES
# This makes the app more resistant to roster
# column-name changes.
# --------------------------------------------------

def find_column(df, choices):
    for choice in choices:
        if choice in df.columns:
            return choice
    return None


name_col = find_column(
    week_rosters,
    [
        "full_name",
        "player_name",
        "player_display_name",
        "football_name"
    ]
)

position_col = find_column(
    week_rosters,
    [
        "position",
        "position_group"
    ]
)

team_col = find_column(
    week_rosters,
    [
        "team",
        "team_abbr",
        "recent_team"
    ]
)

id_col = find_column(
    week_rosters,
    [
        "gsis_id",
        "player_id"
    ]
)


if name_col is None or position_col is None:
    st.error("The roster data is missing a required player name or position column.")
    st.write("Roster columns found:", week_rosters.columns)
    st.stop()


# --------------------------------------------------
# BUILD PLAYER POOLS FROM NFL ROSTERS
# --------------------------------------------------

def build_player_pool(position):

    pool = week_rosters.filter(
        pl.col(position_col) == position
    )

    players = []

    for row in pool.iter_rows(named=True):

        name = row.get(name_col)

        if not name:
            continue

        team = row.get(team_col) if team_col else ""
        player_id = row.get(id_col) if id_col else None

        if team:
            label = f"{name} — {team}"
        else:
            label = name

        players.append({
            "label": label,
            "name": name,
            "id": player_id,
            "team": team
        })


    # Remove duplicates
    unique = {}

    for player in players:
        key = (
            player["id"]
            if player["id"]
            else player["label"]
        )

        unique[key] = player


    return sorted(
        unique.values(),
        key=lambda x: x["label"]
    )


qb_pool = build_player_pool("QB")
rb_pool = build_player_pool("RB")
wr_pool = build_player_pool("WR")
te_pool = build_player_pool("TE")


# --------------------------------------------------
# CLASS INFORMATION
# --------------------------------------------------

st.divider()

st.subheader("🏫 Team Information")

col1, col2 = st.columns(2)

with col1:
    period = st.text_input(
        "Period Number"
    )

with col2:
    team_number = st.text_input(
        "Team Number"
    )


# --------------------------------------------------
# PLAYER SELECTOR
# --------------------------------------------------

def player_selector(label, pool, key):

    options = [None] + pool

    selected = st.selectbox(
        label,
        options,
        key=key,
        format_func=lambda x:
            "-- Select Player --"
            if x is None
            else x["label"]
    )

    return selected


# --------------------------------------------------
# STARTING LINEUP
# --------------------------------------------------

st.divider()

st.header("🏟️ Starting Lineup")

st.caption(
    f"Player choices are based on NFL rosters for Week {week}."
)


left, right = st.columns(2)


with left:

    qb = player_selector(
        "QB",
        qb_pool,
        "qb"
    )

    rb1 = player_selector(
        "RB 1",
        rb_pool,
        "rb1"
    )

    rb2 = player_selector(
        "RB 2",
        rb_pool,
        "rb2"
    )

    te = player_selector(
        "TE",
        te_pool,
        "te"
    )


with right:

    wr1 = player_selector(
        "WR 1",
        wr_pool,
        "wr1"
    )

    wr2 = player_selector(
        "WR 2",
        wr_pool,
        "wr2"
    )

    wr3 = player_selector(
        "WR 3",
        wr_pool,
        "wr3"
    )


# --------------------------------------------------
# SAFE STAT FUNCTION
# --------------------------------------------------

def safe_stat(row, column):

    if column not in row:
        return 0

    value = row[column]

    if value is None:
        return 0

    return value


# --------------------------------------------------
# MATCH ROSTER PLAYER TO WEEKLY STATS
# --------------------------------------------------

def find_player_stats(player):

    # Best option: match by GSIS/player ID
    if (
        player["id"]
        and "player_id" in week_stats.columns
    ):

        result = week_stats.filter(
            pl.col("player_id") == player["id"]
        )

        if result.height > 0:
            return result


    # Backup: match by full player name
    if "player_display_name" in week_stats.columns:

        result = week_stats.filter(
            pl.col("player_display_name") == player["name"]
        )

        if result.height > 0:
            return result


    return None


# --------------------------------------------------
# CALCULATE PLAYER SCORE
# --------------------------------------------------

def calculate_player(player, position):

    player_data = find_player_stats(player)


    # Player was on roster but recorded no stats
    if player_data is None or player_data.height == 0:

        return {
            "player": player["label"],
            "position": position,
            "stats": "No recorded fantasy statistics this week",
            "calculation": "0",
            "score": 0.0
        }


    row = player_data.row(
        0,
        named=True
    )


    passing_yards = safe_stat(
        row,
        "passing_yards"
    )

    passing_tds = safe_stat(
        row,
        "passing_tds"
    )

    interceptions = safe_stat(
        row,
        "interceptions"
    )

    rushing_yards = safe_stat(
        row,
        "rushing_yards"
    )

    rushing_tds = safe_stat(
        row,
        "rushing_tds"
    )

    receptions = safe_stat(
        row,
        "receptions"
    )

    receiving_yards = safe_stat(
        row,
        "receiving_yards"
    )

    receiving_tds = safe_stat(
        row,
        "receiving_tds"
    )


    # ---------------- QB ----------------

    if position == "QB":

        score = (
            passing_yards * .12
            + passing_tds * 4
            + rushing_tds * 6
            - interceptions * 2
        )

        stats_text = (
            f"{passing_yards} passing yards • "
            f"{passing_tds} passing TD • "
            f"{rushing_tds} rushing TD • "
            f"{interceptions} INT"
        )

        calculation = (
            f"({passing_yards} × .12) + "
            f"({passing_tds} × 4) + "
            f"({rushing_tds} × 6) − "
            f"({interceptions} × 2)"
        )


    # ---------------- RB ----------------

    elif position == "RB":

        score = (
            rushing_yards * .1
            + rushing_tds * 6
            + receptions * 1
            + receiving_yards * .1
            + receiving_tds * 6
        )

        stats_text = (
            f"{rushing_yards} rushing yards • "
            f"{rushing_tds} rushing TD • "
            f"{receptions} catches • "
            f"{receiving_yards} receiving yards • "
            f"{receiving_tds} receiving TD"
        )

        calculation = (
            f"({rushing_yards} × .1) + "
            f"({rushing_tds} × 6) + "
            f"({receptions} × 1) + "
            f"({receiving_yards} × .1) + "
            f"({receiving_tds} × 6)"
        )


    # ---------------- WR / TE ----------------

    else:

        score = (
            receiving_yards * .1
            + receiving_tds * 6
        )

        stats_text = (
            f"{receiving_yards} receiving yards • "
            f"{receiving_tds} receiving TD"
        )

        calculation = (
            f"({receiving_yards} × .1) + "
            f"({receiving_tds} × 6)"
        )


    return {
        "player": player["label"],
        "position": position,
        "stats": stats_text,
        "calculation": calculation,
        "score": round(score, 2)
    }


# --------------------------------------------------
# CALCULATE BUTTON
# --------------------------------------------------

st.divider()


if st.button(
    "🏈 CALCULATE TEAM SCORE",
    type="primary",
    use_container_width=True
):

    lineup = [
        (qb, "QB"),
        (rb1, "RB"),
        (rb2, "RB"),
        (wr1, "WR"),
        (wr2, "WR"),
        (wr3, "WR"),
        (te, "TE")
    ]


    # Make sure all positions are filled
    if any(
        player is None
        for player, position in lineup
    ):

        st.warning(
            "Please select all 7 players before calculating."
        )


    # Prevent duplicate players
    elif len(
        [
            player["id"] or player["label"]
            for player, position in lineup
        ]
    ) != len(
        set(
            player["id"] or player["label"]
            for player, position in lineup
        )
    ):

        st.warning(
            "The same player cannot be used twice."
        )


    else:

        results = []

        for player, position in lineup:

            results.append(
                calculate_player(
                    player,
                    position
                )
            )


        # ------------------------------------------
        # TEAM HEADER
        # ------------------------------------------

        if period and team_number:

            st.success(
                f"Period {period} • "
                f"Team {team_number} • "
                f"Week {week}"
            )

        else:

            st.success(
                f"NFL Week {week}"
            )


        # ------------------------------------------
        # RESULTS TABLE
        # ------------------------------------------

        st.header("📊 Scoring Breakdown")


        display_data = []

        for result in results:

            display_data.append({
                "Position": result["position"],
                "Player": result["player"],
                "Stats": result["stats"],
                "Calculation": result["calculation"],
                "Points": result["score"]
            })


        st.dataframe(
            display_data,
            use_container_width=True,
            hide_index=True
        )


        # ------------------------------------------
        # INDIVIDUAL PLAYER WORK
        # ------------------------------------------

        st.subheader("🧮 Show the Math")


        for result in results:

            with st.expander(
                f"{result['position']} — "
                f"{result['player']} — "
                f"{result['score']} pts"
            ):

                st.write(
                    "**Stats:** "
                    + result["stats"]
                )

                st.write(
                    "**Calculation:**"
                )

                st.code(
                    result["calculation"],
                    language=None
                )


        # ------------------------------------------
        # FINAL SCORE
        # ------------------------------------------

        team_total = sum(
            result["score"]
            for result in results
        )


        st.divider()

        st.header("🏆 FINAL TEAM SCORE")

        st.metric(
            "TOTAL FANTASY POINTS",
            f"{team_total:.2f}"
        )

        st.balloons()


# --------------------------------------------------
# SCORING RULES
# --------------------------------------------------

st.divider()

with st.expander("📋 View Fantasy Football Scoring Rules"):

    st.markdown(
        """
### Quarterback
- **0.12** points per passing yard
- **4** points per passing touchdown
- **6** points per rushing touchdown
- **−2** points per interception

### Running Back
- **0.1** points per rushing yard
- **6** points per rushing touchdown
- **1** point per catch
- **0.1** points per receiving yard
- **6** points per receiving touchdown

### Wide Receiver & Tight End
- **0.1** points per receiving yard
- **6** points per receiving touchdown
"""
    )


st.caption(
    "Sports by the Numbers • Fantasy Football • 2026"
)
