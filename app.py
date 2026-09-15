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
    "Select the NFL week and your team's starting lineup. "
    "The calculator will use the real NFL statistics from that week "
    "and calculate your team's score."
)

SEASON = 2026


# --------------------------------------------------
# LOAD NFL DATA
# --------------------------------------------------

@st.cache_data(ttl=3600)
def load_stats():
    data = nfl.load_player_stats(
        seasons=[SEASON],
        summary_level="week"
    )
    return data


try:
    stats = load_stats()

except Exception as e:
    st.error("The NFL statistics could not be loaded right now.")
    st.write("Please try again later.")
    st.stop()


# --------------------------------------------------
# CHOOSE WEEK
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

week_stats = stats.filter(pl.col("week") == week)


# --------------------------------------------------
# CLASS INFORMATION
# --------------------------------------------------

st.divider()

st.subheader("Your Team")

col1, col2 = st.columns(2)

with col1:
    period = st.text_input("Period Number")

with col2:
    team_number = st.text_input("Team Number")


# --------------------------------------------------
# PLAYER LISTS
# --------------------------------------------------

def player_list(position):

    players = (
        week_stats
        .filter(pl.col("position") == position)
        .select("player_display_name")
        .drop_nulls()
        .unique()
        .sort("player_display_name")
        .to_series()
        .to_list()
    )

    return ["-- Select Player --"] + players


qb_players = player_list("QB")
rb_players = player_list("RB")
wr_players = player_list("WR")
te_players = player_list("TE")


# --------------------------------------------------
# LINEUP
# --------------------------------------------------

st.divider()

st.header("🏟️ Starting Lineup")

col1, col2 = st.columns(2)

with col1:

    qb = st.selectbox(
        "QB",
        qb_players
    )

    rb1 = st.selectbox(
        "RB 1",
        rb_players
    )

    rb2 = st.selectbox(
        "RB 2",
        rb_players
    )

    te = st.selectbox(
        "TE",
        te_players
    )


with col2:

    wr1 = st.selectbox(
        "WR 1",
        wr_players
    )

    wr2 = st.selectbox(
        "WR 2",
        wr_players
    )

    wr3 = st.selectbox(
        "WR 3",
        wr_players
    )


# --------------------------------------------------
# SAFE STAT FUNCTION
# --------------------------------------------------

def get_stat(row, column):

    if column not in row:
        return 0

    value = row[column]

    if value is None:
        return 0

    return value


# --------------------------------------------------
# CALCULATE PLAYER SCORE
# --------------------------------------------------

def calculate_player(player, position):

    player_data = week_stats.filter(
        pl.col("player_display_name") == player
    )

    if player_data.height == 0:
        return None

    row = player_data.row(0, named=True)

    passing_yards = get_stat(row, "passing_yards")
    passing_tds = get_stat(row, "passing_tds")
    interceptions = get_stat(row, "interceptions")

    rushing_yards = get_stat(row, "rushing_yards")
    rushing_tds = get_stat(row, "rushing_tds")

    receptions = get_stat(row, "receptions")
    receiving_yards = get_stat(row, "receiving_yards")
    receiving_tds = get_stat(row, "receiving_tds")


    # QB SCORING

    if position == "QB":

        score = (
            passing_yards * 0.12
            + passing_tds * 4
            + rushing_tds * 6
            - interceptions * 2
        )

        stats_text = (
            f"{passing_yards} Pass Yds | "
            f"{passing_tds} Pass TD | "
            f"{rushing_tds} Rush TD | "
            f"{interceptions} INT"
        )

        calculation = (
            f"({passing_yards} × .12) + "
            f"({passing_tds} × 4) + "
            f"({rushing_tds} × 6) - "
            f"({interceptions} × 2)"
        )


    # RUNNING BACK SCORING

    elif position == "RB":

        score = (
            rushing_yards * 0.1
            + rushing_tds * 6
            + receptions
            + receiving_yards * 0.1
            + receiving_tds * 6
        )

        stats_text = (
            f"{rushing_yards} Rush Yds | "
            f"{rushing_tds} Rush TD | "
            f"{receptions} Rec | "
            f"{receiving_yards} Rec Yds | "
            f"{receiving_tds} Rec TD"
        )

        calculation = (
            f"({rushing_yards} × .1) + "
            f"({rushing_tds} × 6) + "
            f"({receptions} × 1) + "
            f"({receiving_yards} × .1) + "
            f"({receiving_tds} × 6)"
        )


    # WR / TE SCORING

    else:

        score = (
            receiving_yards * 0.1
            + receiving_tds * 6
        )

        stats_text = (
            f"{receiving_yards} Rec Yds | "
            f"{receiving_tds} Rec TD"
        )

        calculation = (
            f"({receiving_yards} × .1) + "
            f"({receiving_tds} × 6)"
        )


    return {
        "player": player,
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

    if any(player == "-- Select Player --" for player, position in lineup):

        st.warning(
            "Please select all 7 players before calculating your score."
        )

    else:

        results = []

        for player, position in lineup:

            result = calculate_player(
                player,
                position
            )

            if result:
                results.append(result)


        # ------------------------------------------
        # RESULTS
        # ------------------------------------------

        st.success(
            f"Period {period} — Team {team_number} — Week {week}"
        )

        st.header("📊 Scoring Breakdown")


        for result in results:

            st.subheader(
                f"{result['position']} — {result['player']}"
            )

            st.write(
                "**Stats:**",
                result["stats"]
            )

            st.write(
                "**Calculation:**",
                result["calculation"]
            )

            st.metric(
                "Fantasy Points",
                result["score"]
            )

            st.divider()


        # ------------------------------------------
        # TEAM TOTAL
        # ------------------------------------------

        team_total = sum(
            result["score"]
            for result in results
        )

        st.header("🏆 FINAL TEAM SCORE")

        st.metric(
            "TOTAL FANTASY POINTS",
            round(team_total, 2)
        )

        st.balloons()


# --------------------------------------------------
# SCORING REFERENCE
# --------------------------------------------------

st.divider()

st.subheader("📋 Scoring Rules")

st.markdown(
    """
**Quarterback**

- 0.12 points per passing yard
- 4 points per passing touchdown
- 6 points per rushing touchdown
- -2 points per interception

**Running Back**

- 0.1 points per rushing yard
- 6 points per rushing touchdown
- 1 point per reception
- 0.1 points per receiving yard
- 6 points per receiving touchdown

**Wide Receiver / Tight End**

- 0.1 points per receiving yard
- 6 points per receiving touchdown
"""
)

st.caption(
    "Sports by the Numbers • Fantasy Football"
)
