import streamlit as st
import nflreadpy as nfl
import polars as pl

# ==================================================
# PAGE SETUP
# ==================================================

st.set_page_config(
    page_title="Sports by the Numbers Fantasy Football",
    page_icon="🏈",
    layout="wide"
)

st.title("🏈 Sports by the Numbers")
st.subheader("Fantasy Football Weekly Score Calculator")

st.info(
    "💡 TIP: Click a player box and start typing the player's "
    "name to search."
)

SEASON = 2026


# ==================================================
# LOAD NFL DATA
# ==================================================

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

    st.error("NFL data could not be loaded.")
    st.write(e)
    st.stop()


# ==================================================
# HELPER — FIND COLUMN
# ==================================================

def find_column(df, choices):

    for choice in choices:

        if choice in df.columns:
            return choice

    return None


# ==================================================
# WEEK
# ==================================================

available_weeks = (
    stats
    .select("week")
    .unique()
    .sort("week")
    .to_series()
    .to_list()
)

week = st.selectbox(
    "🏈 NFL Week",
    available_weeks,
    index=len(available_weeks) - 1
)


week_stats = stats.filter(
    pl.col("week") == week
)


# ==================================================
# ROSTER DATA
# ==================================================

if "week" in rosters.columns:

    week_rosters = rosters.filter(
        pl.col("week") == week
    )

else:

    week_rosters = rosters


roster_name_col = find_column(
    week_rosters,
    [
        "full_name",
        "player_name",
        "player_display_name",
        "football_name"
    ]
)

roster_position_col = find_column(
    week_rosters,
    [
        "position",
        "position_group"
    ]
)

roster_team_col = find_column(
    week_rosters,
    [
        "team",
        "team_abbr",
        "recent_team"
    ]
)

roster_id_col = find_column(
    week_rosters,
    [
        "gsis_id",
        "player_id"
    ]
)


# ==================================================
# STATS COLUMNS
# ==================================================

stats_name_col = find_column(
    week_stats,
    [
        "player_display_name",
        "player_name",
        "full_name"
    ]
)

stats_position_col = find_column(
    week_stats,
    [
        "position",
        "position_group"
    ]
)

stats_team_col = find_column(
    week_stats,
    [
        "recent_team",
        "team",
        "team_abbr"
    ]
)

stats_id_col = find_column(
    week_stats,
    [
        "player_id",
        "gsis_id"
    ]
)


# ==================================================
# BUILD MASTER PLAYER POOL
#
# Combines:
# 1. Weekly NFL roster
# 2. Players appearing in weekly stats
#
# This gives us a much broader search pool.
# ==================================================

def build_master_pool(position):

    players = {}


    # ----------------------------------------------
    # ADD PLAYERS FROM ROSTERS
    # ----------------------------------------------

    if (
        roster_name_col
        and roster_position_col
    ):

        roster_players = week_rosters.filter(
            pl.col(roster_position_col) == position
        )

        for row in roster_players.iter_rows(
            named=True
        ):

            name = row.get(
                roster_name_col
            )

            if not name:
                continue

            team = (
                row.get(roster_team_col)
                if roster_team_col
                else ""
            )

            player_id = (
                row.get(roster_id_col)
                if roster_id_col
                else None
            )

            key = (
                player_id
                if player_id
                else f"{name}-{team}"
            )

            players[key] = {
                "name": name,
                "team": team or "",
                "id": player_id,
                "position": position
            }


    # ----------------------------------------------
    # ADD PLAYERS FROM WEEKLY STATS
    # ----------------------------------------------

    if (
        stats_name_col
        and stats_position_col
    ):

        stat_players = week_stats.filter(
            pl.col(stats_position_col) == position
        )

        for row in stat_players.iter_rows(
            named=True
        ):

            name = row.get(
                stats_name_col
            )

            if not name:
                continue

            team = (
                row.get(stats_team_col)
                if stats_team_col
                else ""
            )

            player_id = (
                row.get(stats_id_col)
                if stats_id_col
                else None
            )

            key = (
                player_id
                if player_id
                else f"{name}-{team}"
            )

            if key not in players:

                players[key] = {
                    "name": name,
                    "team": team or "",
                    "id": player_id,
                    "position": position
                }


    # ----------------------------------------------
    # CREATE DISPLAY LABEL
    # ----------------------------------------------

    result = []

    for player in players.values():

        if player["team"]:

            player["label"] = (
                f"{player['name']} — "
                f"{player['team']}"
            )

        else:

            player["label"] = player["name"]

        result.append(player)


    return sorted(
        result,
        key=lambda x: x["label"]
    )


qb_pool = build_master_pool("QB")
rb_pool = build_master_pool("RB")
wr_pool = build_master_pool("WR")
te_pool = build_master_pool("TE")


# ==================================================
# CLASS INFORMATION
# ==================================================

st.divider()

st.subheader("🏫 Team Information")

c1, c2, c3 = st.columns(3)

with c1:

    period = st.text_input(
        "Period Number"
    )

with c2:

    team_number = st.text_input(
        "Team Number"
    )

with c3:

    team_name = st.text_input(
        "Fantasy Team Name"
    )


# ==================================================
# PLAYER SEARCH BOX
# ==================================================

def player_search(
    title,
    pool,
    key
):

    labels = [
        player["label"]
        for player in pool
    ]

    selected_label = st.selectbox(
        title,
        [""] + labels,
        key=key,
        index=0,
        placeholder="Type a player's name to search..."
    )

    if not selected_label:

        return None


    for player in pool:

        if player["label"] == selected_label:

            return player


    return None


# ==================================================
# LINEUP
# ==================================================

st.divider()

st.header("🏟️ Starting Lineup")

st.write(
    "**Click inside any player box and start typing.** "
    "The list will automatically search for matching players."
)


left, right = st.columns(2)


with left:

    st.subheader("QB / RB")

    qb = player_search(
        "🏈 Quarterback",
        qb_pool,
        "qb"
    )

    rb1 = player_search(
        "🏃 Running Back 1",
        rb_pool,
        "rb1"
    )

    rb2 = player_search(
        "🏃 Running Back 2",
        rb_pool,
        "rb2"
    )


with right:

    st.subheader("WR / TE")

    wr1 = player_search(
        "🙌 Wide Receiver 1",
        wr_pool,
        "wr1"
    )

    wr2 = player_search(
        "🙌 Wide Receiver 2",
        wr_pool,
        "wr2"
    )

    wr3 = player_search(
        "🙌 Wide Receiver 3",
        wr_pool,
        "wr3"
    )

    te = player_search(
        "💪 Tight End",
        te_pool,
        "te"
    )


# ==================================================
# PLAYER POOL INFO
# ==================================================

with st.expander(
    "🔎 Can't find a player?"
):

    st.write(
        "First, click the player's position box and "
        "start typing the player's **last name**."
    )

    st.write(
        "The search includes players from both the "
        f"Week {week} NFL roster data and Week {week} "
        "statistical data."
    )

    st.write(
        f"**Players currently searchable:** "
        f"{len(qb_pool)} QBs • "
        f"{len(rb_pool)} RBs • "
        f"{len(wr_pool)} WRs • "
        f"{len(te_pool)} TEs"
    )


# ==================================================
# SAFE STAT
# ==================================================

def safe_stat(
    row,
    column
):

    if column not in row:
        return 0

    value = row[column]

    if value is None:
        return 0

    return value


# ==================================================
# FIND PLAYER STATS
# ==================================================

def find_player_stats(
    player
):

    if player is None:
        return None


    # ----------------------------------------------
    # TRY PLAYER ID FIRST
    # ----------------------------------------------

    if (
        player["id"]
        and stats_id_col
    ):

        result = week_stats.filter(
            pl.col(stats_id_col)
            == player["id"]
        )

        if result.height > 0:
            return result


    # ----------------------------------------------
    # TRY NAME
    # ----------------------------------------------

    if stats_name_col:

        result = week_stats.filter(
            pl.col(stats_name_col)
            == player["name"]
        )

        if result.height > 0:
            return result


    return None


# ==================================================
# CALCULATE PLAYER
# ==================================================

def calculate_player(
    player,
    position
):

    player_data = find_player_stats(
        player
    )


    # ----------------------------------------------
    # PLAYER HAD NO RECORDED STATS
    # ----------------------------------------------

    if (
        player_data is None
        or player_data.height == 0
    ):

        return {
            "position": position,
            "player": player["label"],
            "stats": "No recorded statistics",
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


    # ----------------------------------------------
    # QB
    # ----------------------------------------------

    if position == "QB":

        score = (
            passing_yards * .12
            + passing_tds * 4
            + rushing_tds * 6
            - interceptions * 2
        )

        stats_text = (
            f"{passing_yards} Pass Yds • "
            f"{passing_tds} Pass TD • "
            f"{rushing_tds} Rush TD • "
            f"{interceptions} INT"
        )

        calculation = (
            f"({passing_yards} × .12) + "
            f"({passing_tds} × 4) + "
            f"({rushing_tds} × 6) − "
            f"({interceptions} × 2)"
        )


    # ----------------------------------------------
    # RB
    # ----------------------------------------------

    elif position == "RB":

        score = (
            rushing_yards * .1
            + rushing_tds * 6
            + receptions
            + receiving_yards * .1
            + receiving_tds * 6
        )

        stats_text = (
            f"{rushing_yards} Rush Yds • "
            f"{rushing_tds} Rush TD • "
            f"{receptions} Catches • "
            f"{receiving_yards} Rec Yds • "
            f"{receiving_tds} Rec TD"
        )

        calculation = (
            f"({rushing_yards} × .1) + "
            f"({rushing_tds} × 6) + "
            f"({receptions} × 1) + "
            f"({receiving_yards} × .1) + "
            f"({receiving_tds} × 6)"
        )


    # ----------------------------------------------
    # WR / TE
    # ----------------------------------------------

    else:

        score = (
            receiving_yards * .1
            + receiving_tds * 6
        )

        stats_text = (
            f"{receiving_yards} Rec Yds • "
            f"{receiving_tds} Rec TD"
        )

        calculation = (
            f"({receiving_yards} × .1) + "
            f"({receiving_tds} × 6)"
        )


    return {
        "position": position,
        "player": player["label"],
        "stats": stats_text,
        "calculation": calculation,
        "score": round(score, 2)
    }


# ==================================================
# CALCULATE
# ==================================================

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


    # ----------------------------------------------
    # CHECK MISSING PLAYERS
    # ----------------------------------------------

    if any(
        player is None
        for player, position in lineup
    ):

        st.warning(
            "⚠️ Please select all 7 players."
        )


    else:

        # ------------------------------------------
        # CHECK DUPLICATES
        # ------------------------------------------

        player_keys = [

            player["id"]
            or player["label"]

            for player, position
            in lineup

        ]


        if len(player_keys) != len(
            set(player_keys)
        ):

            st.warning(
                "⚠️ You cannot use the same "
                "player twice."
            )


        else:

            # --------------------------------------
            # CALCULATE
            # --------------------------------------

            results = [

                calculate_player(
                    player,
                    position
                )

                for player, position
                in lineup

            ]


            # --------------------------------------
            # HEADER
            # --------------------------------------

            st.success(
                f"🏈 Week {week} "
                f"• Period {period or '—'} "
                f"• Team {team_number or '—'} "
                f"{'• ' + team_name if team_name else ''}"
            )


            # --------------------------------------
            # RESULTS TABLE
            # --------------------------------------

            st.header(
                "📊 Team Scoring Breakdown"
            )


            table_data = [

                {

                    "Position":
                        result["position"],

                    "Player":
                        result["player"],

                    "Stats":
                        result["stats"],

                    "Points":
                        result["score"]

                }

                for result
                in results

            ]


            st.dataframe(
                table_data,
                use_container_width=True,
                hide_index=True
            )


            # --------------------------------------
            # SHOW MATH
            # --------------------------------------

            st.subheader(
                "🧮 Show the Math"
            )


            for result in results:

                with st.expander(

                    f"{result['position']} — "
                    f"{result['player']} — "
                    f"{result['score']:.2f} pts"

                ):

                    st.write(
                        "**Stats:**"
                    )

                    st.write(
                        result["stats"]
                    )

                    st.write(
                        "**Calculation:**"
                    )

                    st.code(
                        result["calculation"],
                        language=None
                    )


            # --------------------------------------
            # TEAM TOTAL
            # --------------------------------------

            team_total = sum(

                result["score"]

                for result
                in results

            )


            st.divider()

            st.header(
                "🏆 FINAL TEAM SCORE"
            )


            st.metric(
                "TOTAL FANTASY POINTS",
                f"{team_total:.2f}"
            )


            st.balloons()


# ==================================================
# SCORING RULES
# ==================================================

st.divider()


with st.expander(
    "📋 Fantasy Football Scoring Rules"
):

    st.markdown(
        """
### Quarterback

**Passing**
- 0.12 points per passing yard
- 4 points per passing touchdown
- −2 points per interception

**Rushing**
- 6 points per rushing touchdown


### Running Back

**Rushing**
- 0.1 points per rushing yard
- 6 points per rushing touchdown

**Receiving**
- 1 point per catch
- 0.1 points per receiving yard
- 6 points per receiving touchdown


### Wide Receiver & Tight End

- 0.1 points per receiving yard
- 6 points per receiving touchdown
"""
    )


st.caption(
    "Sports by the Numbers • Fantasy Football • 2026"
)
