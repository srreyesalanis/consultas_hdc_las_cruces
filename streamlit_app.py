import streamlit as st
import pandas as pd
from supabase import create_client
from fpdf import FPDF

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
    "Ver detalle de rondas de un jugador",
    players_df["name"],
    index=None,
    placeholder="Seleccione un jugador..."
)

if selected_player_name is not None:

    selected_player = players_df[
        players_df["name"] == selected_player_name
    ].iloc[0]

    player_id = selected_player["id"]

    # Handicap
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
        .limit(20)
        .execute()
    )

    rounds_data = rounds_response.data

    # DATAFRAME ORIGINAL
    rounds_df = pd.DataFrame(rounds_data)

    # DATAFRAME SOLO PARA MOSTRAR
    rounds_df["differential"] = rounds_df["differential"].round(1)

    display_df = rounds_df[[
        "played_at",
        "differential",
        "total_adjusted"
    ]].rename(columns={
        "played_at": "Fecha",
        "differential": "Score Diferencial",
        "total_adjusted": "Score Ajustado"
    })

    st.subheader("Últimas Rondas")

    # Identificar las 8 mejores diferenciales (usadas para el cálculo)
    if "differential" in rounds_df.columns and rounds_df["differential"].notna().sum() > 0:
        best_8_idx = rounds_df["differential"].nsmallest(8).index
    else:
        best_8_idx = []

    def highlight_best(row):
        if row.name in best_8_idx:
            return ["background-color: #c8f7c5; color: #1a7a1a; font-weight: bold"] * len(row)
        return [""] * len(row)

    event = st.dataframe(
        display_df.style.apply(highlight_best, axis=1),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Score Diferencial": st.column_config.NumberColumn(format="%.1f"),
        }
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

            detail_df = pd.DataFrame(detail_data).rename(columns={
                "hole_number": "Hoyo",
                "strokes": "Golpes"
            })

            # Agregar fila total Front (despues del hoyo 9)
            front_df = detail_df[detail_df["Hoyo"] <= 9]
            back_df  = detail_df[detail_df["Hoyo"] >= 10]

            front_total = pd.DataFrame([{"Hoyo": "Front", "Golpes": front_df["Golpes"].sum()}])
            back_total  = pd.DataFrame([{"Hoyo": "Back",  "Golpes": back_df["Golpes"].sum()}])
            total_row   = pd.DataFrame([{"Hoyo": "Total", "Golpes": detail_df["Golpes"].sum()}])

            display_detail = pd.concat([
                front_df,
                front_total,
                back_df,
                back_total,
                total_row
            ], ignore_index=True)

            # Centrar tabla
            left, center, right = st.columns([1, 2, 1])

            with center:

                bold_rows = display_detail.index[display_detail["Hoyo"].isin(["Front", "Back", "Total"])].tolist()

                def highlight_totals(row):
                    if row.name in bold_rows:
                        return ["font-weight: bold"] * len(row)
                    return [""] * len(row)

                st.dataframe(
                    display_detail.style.apply(highlight_totals, axis=1),
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Hoyo": st.column_config.TextColumn("Hoyo", width="small"),
                        "Golpes": st.column_config.NumberColumn("Golpes", width="small")
                    }
                )

        else:

            st.info("No existe detalle para esta ronda")

# --------------------------------------------------
# GRAFICA EVOLUCION HANDICAP
# --------------------------------------------------

    if selected_player_name is not None:

        st.subheader("Evolución del Handicap")

        import plotly.graph_objects as go

        hdc_history = (
            supabase
            .table("handicaps")
            .select("handicap_index, calculated_at")
            .eq("player_id", player_id)
            .order("calculated_at", desc=False)
            .execute()
        )

        hdc_raw = pd.DataFrame(hdc_history.data)
        hdc_df = hdc_raw.dropna(subset=["handicap_index"]) if "handicap_index" in hdc_raw.columns else pd.DataFrame()

        if len(hdc_df) >= 1:
            hdc_df["calculated_at"] = pd.to_datetime(hdc_df["calculated_at"])
            hdc_df["handicap_index"] = hdc_df["handicap_index"].astype(float).round(1)
            hdc_df["fecha_str"] = hdc_df["calculated_at"].dt.strftime("%d %b %Y")

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hdc_df["calculated_at"],
                y=hdc_df["handicap_index"],
                mode="lines+markers",
                line=dict(color="#2E86AB", width=2),
                marker=dict(size=7, color="#2E86AB"),
                hovertemplate="<b>%{x|%d %b %Y}</b><br>Handicap: %{y}<extra></extra>"
            ))
            fig.update_layout(
                xaxis_title="",
                yaxis_title="Handicap Index",
                margin=dict(l=10, r=10, t=10, b=60),
                height=320,
                hovermode="x unified",
                xaxis=dict(
                    tickformat="%d/%m/%y",
                    tickangle=-90,
                    tickmode="array",
                    tickvals=hdc_df["calculated_at"]
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin historial de handicap registrado.")

# --------------------------------------------------
# RANKING
# --------------------------------------------------

st.subheader("Ranking")

ranking_df = (
    players_df
    .dropna(subset=["current_handicap"])
    .sort_values(by="current_handicap", ascending=True)
    .reset_index(drop=True)
)

ranking_df["Ranking"] = ranking_df.index + 1

ranking_df = ranking_df.rename(columns={
    "name": "Jugador",
    "current_handicap": "Handicap"
})

ranking_df["Handicap"] = ranking_df["Handicap"].round(1)

ranking_df = ranking_df[[
    "Ranking",
    "Jugador",
    "Handicap"
]]

st.dataframe(
    ranking_df,
    use_container_width=True,
    hide_index=True
)

# --------------------------------------------------
# BOTON DESCARGAR PDF
# --------------------------------------------------

def generar_pdf_ranking(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Las Cruces - Ranking de Handicap", ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(34, 139, 34)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(25, 8, "#", border=1, fill=True, align="C")
    pdf.cell(120, 8, "Jugador", border=1, fill=True, align="C")
    pdf.cell(35, 8, "Handicap", border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    for i, row in df.iterrows():
        fill = i % 2 == 0
        if fill:
            pdf.set_fill_color(240, 248, 240)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.cell(25, 7, str(int(row["Ranking"])), border=1, fill=fill, align="C")
        pdf.cell(120, 7, str(row["Jugador"]), border=1, fill=fill)
        pdf.cell(35, 7, str(row["Handicap"]), border=1, fill=fill, align="C")
        pdf.ln()
    return bytes(pdf.output())

pdf_bytes = generar_pdf_ranking(ranking_df)

st.download_button(
    label="⬇️ Descargar Ranking PDF",
    data=pdf_bytes,
    file_name="ranking_las_cruces.pdf",
    mime="application/pdf",
    use_container_width=True
)