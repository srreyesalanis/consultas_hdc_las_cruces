import streamlit as st
import pandas as pd
from supabase import create_client

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# CONFIGURACION PAGINA
# --------------------------------------------------

st.set_page_config(
    page_title="Consulta de Handicap",
    page_icon="⛳",
    layout="centered"
)

# --------------------------------------------------
# SUPABASE
# --------------------------------------------------

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]

supabase = create_client(url, key)

# --------------------------------------------------
# TITULO
# --------------------------------------------------

st.title("⛳ Las Cruces")
st.markdown("Consulta pública de jugadores")

# --------------------------------------------------
# OBTENER JUGADORES
# --------------------------------------------------

players_response = (
    supabase
    .table("players")
    .select("id, name, current_handicap")
    .order("name")
    .execute()
)

players_data = players_response.data

if not players_data:
    st.warning("No existen jugadores registrados")
    st.stop()

players_df = pd.DataFrame(players_data)

# --------------------------------------------------
# SELECTOR JUGADOR
# --------------------------------------------------

selected_player_name = st.selectbox(
    "Selecciona un jugador",
    players_df["name"]
)

selected_player = players_df[
    players_df["name"] == selected_player_name
].iloc[0]

player_id = selected_player["id"]

# --------------------------------------------------
# HANDICAP ACTUAL
# --------------------------------------------------

handicap = selected_player["current_handicap"]

if pd.notna(handicap):

    st.metric(
        label="Handicap Actual",
        value=round(float(handicap), 1)
    )

else:

    st.metric(
        label="Handicap Actual",
        value="5 (Temporal)"
    )

# --------------------------------------------------
# ULTIMAS RONDAS
# --------------------------------------------------

rounds_response = (
    supabase
    .table("rounds")
    .select("round_id, played_at, differential, total_adjusted")
    .eq("player_id", player_id)
    .order("played_at", desc=True)
    .limit(10)
    .execute()
)

rounds_data = rounds_response.data

rounds_df = pd.DataFrame(rounds_data)

st.subheader("Últimas Rondas")

event = st.dataframe(
    rounds_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row"
)

selected_rows = event.selection


if selected_rows["rows"]:

    selected_index = selected_rows["rows"][0]

    selected_round = rounds_df.iloc[selected_index]

    selected_date = selected_round["played_at"]

    st.subheader(f"Detalle de la ronda - {selected_date}")

    # Obtener round_id real
    round_id = rounds_data[selected_index]["round_id"]

    # CONSULTA DETALLE
    detail_response = (
        supabase
        .table("round_holes")
        .select("hole_number, strokes")
        .eq("round_id", round_id)
        .order("hole_number")
        .execute()
    )

    detail_data = detail_response.data

    if detail_data:

        detail_df = pd.DataFrame(detail_data)

        detail_df = detail_df.rename(columns={
            "hole_number": "Hoyo",
            "strokes": "Golpes"
        })

        # Centrar tabla
        left, center, right = st.columns([2, 1, 2])

        with center:

            st.dataframe(
                detail_df,
                hide_index=True,
                use_container_width=False,
                width=220,
                column_config={
                    "Hoyo": st.column_config.NumberColumn(
                        "Hoyo",
                        width="small"
                    ),
                    "Golpes": st.column_config.NumberColumn(
                        "Golpes",
                        width="small"
                    )
                }
            )

    else:

        st.info("No existe detalle para esta ronda")

# --------------------------------------------------
# RANKING
# --------------------------------------------------

st.subheader("Ranking")

ranking_df = players_df.copy()

ranking_df = ranking_df.sort_values(
    by="current_handicap",
    ascending=True
)

ranking_df = ranking_df.rename(columns={
    "name": "Jugador",
    "current_handicap": "Handicap"
})

ranking_df = ranking_df[["Jugador", "Handicap"]]

ranking_df.index = ranking_df.index + 1

st.dataframe(
    ranking_df,
    use_container_width=True
)

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown("---")
st.caption("Sistema público de consulta de handicap")
