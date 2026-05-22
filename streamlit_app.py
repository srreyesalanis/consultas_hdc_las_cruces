import streamlit as st
import pandas as pd
from supabase import create_client

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

st.title("⛳ Consulta de Handicap")
st.markdown("Consulta pública de jugadores")

# --------------------------------------------------
# OBTENER JUGADORES
# --------------------------------------------------

try:

    players_response = (
        supabase
        .table("players")
        .select("id, name, handicap_index")
        .order("name")
        .execute()
    )

    st.write(players_response)

except Exception as e:
    st.write(e)

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

st.metric(
    label="Handicap Actual",
    value=round(selected_player["handicap_index"], 1)
)

# --------------------------------------------------
# ULTIMAS RONDAS
# --------------------------------------------------

rounds_response = (
    supabase
    .table("rounds")
    .select("date_played, score_differential, adjusted_total")
    .eq("player_id", player_id)
    .order("date_played", desc=True)
    .limit(10)
    .execute()
)

rounds_data = rounds_response.data

st.subheader("Últimas Rondas")

if rounds_data:

    rounds_df = pd.DataFrame(rounds_data)

    rounds_df = rounds_df.rename(columns={
        "date_played": "Fecha",
        "score_differential": "Differential",
        "adjusted_total": "Score"
    })

    st.dataframe(
        rounds_df,
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("No existen rondas registradas")

# --------------------------------------------------
# RANKING
# --------------------------------------------------

st.subheader("Ranking")

ranking_df = players_df.copy()

ranking_df = ranking_df.sort_values(
    by="handicap_index",
    ascending=True
)

ranking_df = ranking_df.rename(columns={
    "name": "Jugador",
    "handicap_index": "Handicap"
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
