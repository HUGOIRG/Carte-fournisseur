import streamlit as st
import pandas as pd
import folium
import geopandas as gpd
from collections import defaultdict
from streamlit_folium import st_folium

# ==========================================================
# CONFIG PAGE
# ==========================================================
st.set_page_config(
    page_title="Cartographie fournisseurs",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# STYLE CSS
# ==========================================================
st.markdown("""
<style>

.stApp {
    background-color: #f5f7fb;
}

h1 {
    color: #1f3b73;
    font-size: 36px !important;
    font-weight: 700;
    margin-bottom: 0px;
}

h3 {
    color: #5a6b87;
    font-weight: 400;
    margin-top: 0px;
}

iframe {
    border-radius: 18px !important;
    border: 2px solid #dbe2ea !important;
}

.logo-container {
    text-align: center;
    margin-bottom: 10px;
}

.logo-container img {
    width: 320px;
    max-width: 80%;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #1f3b73;
}

section[data-testid="stSidebar"] * {
    color: #f5f7fb !important;
}

section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] {
    background-color: #2c4c8a;
    border-radius: 8px;
}

section[data-testid="stSidebar"] input {
    background-color: #2c4c8a !important;
    border-radius: 8px;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background-color: white;
    border: 1px solid #dbe2ea;
    border-radius: 14px;
    padding: 14px 18px;
    box-shadow: 0 2px 6px rgba(31,59,115,0.06);
}

div[data-testid="stMetricLabel"] {
    color: #5a6b87;
}

div[data-testid="stMetricValue"] {
    color: #1f3b73;
}

</style>
""", unsafe_allow_html=True)

# ==========================================================
# CHARGEMENT (CACHE)
# ==========================================================
@st.cache_data(show_spinner="Chargement du référentiel départements...")
def load_departements():
    url = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"
    return gpd.read_file(url)


@st.cache_data(show_spinner="Lecture du fichier Excel...")
def load_excel(file_bytes):
    df = pd.read_excel(file_bytes, engine="openpyxl")
    df.columns = df.columns.str.strip().str.lower()
    return df


# ==========================================================
# LOGO + TITRE
# ==========================================================
st.markdown("""
<div style="text-align:center; margin-bottom:20px;">
    <img src="https://raw.githubusercontent.com/HUGOIRG/carte-fournisseur/main/Logo_Support_Long.png"
         width="300">
</div>
""", unsafe_allow_html=True)

st.markdown("""
# 📍 Cartographie fournisseurs
### Visualisation des implantations & couverture départementale
""")

# ==========================================================
# UPLOAD EXCEL (sidebar pour libérer l'espace principal)
# ==========================================================
with st.sidebar:
    st.markdown("## 🧭 Filtres")
    file = st.file_uploader("📂 Importer un fichier Excel", type=["xlsx"])

if file is None:
    st.info("⬅️ Importez un fichier Excel depuis le menu de gauche pour générer la carte.")
    st.stop()

df = load_excel(file)

# Colonnes obligatoires
COLONNES_REQUISES = {"entreprise", "statut", "lat", "lon"}
manquantes = COLONNES_REQUISES - set(df.columns)
if manquantes:
    st.error(f"❌ Colonnes manquantes dans le fichier : {', '.join(manquantes)}")
    st.stop()

# Nettoyage lat/lon invalides
lignes_invalides = df[df["lat"].isna() | df["lon"].isna()]
if len(lignes_invalides) > 0:
    st.warning(f"⚠️ {len(lignes_invalides)} ligne(s) sans coordonnées valides ont été ignorées.")
    df = df.dropna(subset=["lat", "lon"])

gdf = load_departements()

# ==========================================================
# COULEURS
# ==========================================================
COLOR_PALETTE = [
    "darkred", "blue", "green", "purple", "orange",
    "cadetblue", "darkgreen", "darkpurple", "pink", "lightblue",
    "gray", "black", "beige"
]


def get_color(statut):
    try:
        statut_int = int(statut)
        return COLOR_PALETTE[(statut_int - 1) % len(COLOR_PALETTE)]
    except Exception:
        return "gray"


# ==========================================================
# FILTRES SIDEBAR (statut, entreprise, département)
# ==========================================================
statuts_disponibles = sorted(df["statut"].dropna().unique().tolist())
entreprises_disponibles = sorted(df["entreprise"].dropna().unique().tolist())

# Liste de tous les départements présents dans les données
tous_deps = set()
if "deps" in df.columns:
    for v in df["deps"].dropna():
        for d in str(v).split(";"):
            d = d.strip()
            if d:
                tous_deps.add(d)
deps_disponibles = sorted(tous_deps)

with st.sidebar:
    statut_filtre = st.multiselect(
        "📊 Statut de négociation",
        options=statuts_disponibles,
        default=statuts_disponibles
    )

    entreprise_filtre = st.multiselect(
        "🏢 Entreprise(s)",
        options=entreprises_disponibles,
        default=[],
        placeholder="Toutes les entreprises"
    )

    dep_filtre = st.multiselect(
        "🗺️ Département(s)",
        options=deps_disponibles,
        default=[],
        placeholder="Tous les départements"
    )

    recherche = st.text_input("🔎 Recherche libre", placeholder="Nom, adresse, contact...")

    st.divider()
    afficher_zones_dep = st.checkbox("Afficher zones département par entreprise", value=False)
    afficher_heatmap = st.checkbox("Afficher la densité par département", value=True)

# Application des filtres
df_filtre = df[df["statut"].isin(statut_filtre)] if statut_filtre else df.iloc[0:0]

if entreprise_filtre:
    df_filtre = df_filtre[df_filtre["entreprise"].isin(entreprise_filtre)]

if dep_filtre and "deps" in df_filtre.columns:
    def match_dep(val):
        if pd.isna(val):
            return False
        deps_row = [d.strip() for d in str(val).split(";")]
        return any(d in dep_filtre for d in deps_row)
    df_filtre = df_filtre[df_filtre["deps"].apply(match_dep)]

if recherche:
    recherche_lower = recherche.lower()
    colonnes_recherche = [c for c in ["entreprise", "adresse", "contact", "email"] if c in df_filtre.columns]
    masque = pd.Series(False, index=df_filtre.index)
    for c in colonnes_recherche:
        masque = masque | df_filtre[c].astype(str).str.lower().str.contains(recherche_lower, na=False)
    df_filtre = df_filtre[masque]

if len(df_filtre) == 0:
    st.warning("⚠️ Aucun résultat ne correspond aux filtres sélectionnés.")
    st.stop()

# ==========================================================
# RECONSTRUCTION ENTREPRISES (à partir des données filtrées)
# ==========================================================
ENTREPRISES = []

for ent_name, group in df_filtre.groupby("entreprise"):
    ENTREPRISES.append({
        "nom": ent_name,
        "statut_nego": group["statut"].iloc[0],
        "implantations": [
            {
                "lat": row["lat"],
                "lon": row["lon"],
                "adresse": row.get("adresse", ""),
                "contact": row.get("contact", ""),
                "email": row.get("email", ""),
                "tel": row.get("tel", ""),
                "capacité": row.get("capacité", ""),
                "sharepoint": str(row.get("sharepoint", "")).strip(),
                "deps": str(row.get("deps", "")).split(";")
                if pd.notna(row.get("deps", "")) else []
            }
            for _, row in group.iterrows()
        ]
    })

# ==========================================================
# DATA DEPARTEMENTS
# ==========================================================
dep_data = defaultdict(list)

for ent in ENTREPRISES:
    for imp in ent["implantations"]:
        for dep in imp.get("deps", []):
            dep = dep.strip()
            if not dep:
                continue
            dep_data[dep].append({
                "entreprise": ent["nom"],
                "adresse": imp.get("adresse", ""),
                "contact": imp.get("contact", ""),
                "tel": imp.get("tel", ""),
                "email": imp.get("email", ""),
                "capacité": imp.get("capacité", "")
            })

# ==========================================================
# METRICS
# ==========================================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🏢 Entreprises", len(ENTREPRISES))

with col2:
    st.metric("📍 Implantations", len(df_filtre))

with col3:
    st.metric("🗺️ Départements couverts", len(dep_data))

with col4:
    pct = round(100 * len(df_filtre) / len(df), 1) if len(df) else 0
    st.metric("📈 % du référentiel affiché", f"{pct} %")

st.divider()

tab_carte, tab_donnees = st.tabs(["🗺️ Carte", "📄 Données filtrées"])

with tab_donnees:
    st.dataframe(df_filtre, use_container_width=True)

# ==========================================================
# HEATMAP
# ==========================================================
dep_count = {
    dep: len(set([x["entreprise"] for x in items]))
    for dep, items in dep_data.items()
}
max_count = max(dep_count.values()) if dep_count else 1


def heat_color(n):
    if n == 0:
        return "#f0f0f0"
    ratio = n / max_count
    if ratio < 0.2:
        return "#d4f0ff"
    elif ratio < 0.4:
        return "#7fc8f8"
    elif ratio < 0.6:
        return "#7fd37f"
    elif ratio < 0.8:
        return "#ffd966"
    elif ratio < 0.95:
        return "#f4a261"
    else:
        return "#d62828"


# ==========================================================
# MAP
# ==========================================================
with tab_carte:

    m = folium.Map(location=[46.7, 2.5], zoom_start=6, tiles=None)

    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google Maps",
        name="Google Maps"
    ).add_to(m)

    # DEPARTEMENTS + POPUP (avec heatmap optionnelle)
    fg_contours = folium.FeatureGroup(name="🗺️ Départements", show=True)

    for _, r in gdf.iterrows():
        code = r["code"]

        if code in dep_data:
            data = dep_data[code]
            html = f"""
            <h4>Département {code}</h4>
            <b>{len(data)} implantation(s)</b><br><br>
            <div style="max-height:400px; width:100%; overflow-y:auto; overflow-x:hidden; padding-right:8px;">
            """
            for d in data:
                html += f"""
                <div style="margin-bottom:15px;">
                    <b>{d['entreprise']}</b><br>
                    {d['adresse']}<br>
                    🏭 {d['capacité']}<br>
                    👤 {d['contact']}<br>
                    📞 {d['tel']}<br>
                    📧 {d['email']}
                </div>
                """
            html += "</div>"
        else:
            html = f"<h4>Département {code}</h4>Aucune implantation"

        fill = heat_color(dep_count.get(code, 0)) if afficher_heatmap else "#dbe2ea"
        opacity = 0.35 if afficher_heatmap else 0.05

        folium.GeoJson(
            r["geometry"],
            style_function=lambda x, fill=fill, opacity=opacity: {
                "fillColor": fill,
                "color": "black",
                "weight": 0.7,
                "fillOpacity": opacity
            },
            tooltip=f"Département {code}",
            popup=folium.Popup(html, max_width=450)
        ).add_to(fg_contours)

    fg_contours.add_to(m)

    # IMPLANTATIONS
    for ent in ENTREPRISES:
        color = get_color(ent["statut_nego"])
        fg = folium.FeatureGroup(name=f"🏢 {ent['nom']}", show=True)

        for imp in ent["implantations"]:
            popup_html = f"""
            <b style="color:{color};">{ent['nom']}</b><br>
            {imp.get('adresse','')}<br><br>
            🏭 <b>Capacité :</b> {imp.get('capacité','')}<br>
            👤 {imp.get('contact','')}<br>
            📧 <a href="mailto:{imp.get('email','')}">{imp.get('email','')}</a><br>
            📞 {imp.get('tel','')}<br>
            """

            sharepoint_link = imp.get("sharepoint", "")
            if sharepoint_link and str(sharepoint_link).startswith("http"):
                popup_html += f"""
                <br>
                🔗 <a href="{sharepoint_link}" target="_blank">Ouvrir Sharepoint</a>
                """

            folium.Marker(
                location=[imp["lat"], imp["lon"]],
                tooltip=ent["nom"],
                icon=folium.Icon(color=color),
                popup=folium.Popup(popup_html, max_width=350)
            ).add_to(fg)

        fg.add_to(m)

    # ZONES DEPARTEMENT PAR ENTREPRISE (optionnel, désactivé par défaut)
    if afficher_zones_dep:
        for ent in ENTREPRISES:
            fg_dep = folium.FeatureGroup(name=f"🟦 {ent['nom']} - Départements", show=False)
            deps_ent = set()
            for imp in ent["implantations"]:
                for dep in imp.get("deps", []):
                    deps_ent.add(dep.strip())

            for _, r in gdf.iterrows():
                code = r["code"]
                if code in deps_ent:
                    color = get_color(ent["statut_nego"])
                    folium.GeoJson(
                        r["geometry"],
                        style_function=lambda x, color=color: {
                            "fillColor": color,
                            "color": color,
                            "weight": 2,
                            "fillOpacity": 0.4
                        },
                        tooltip=f"{ent['nom']} • {code}"
                    ).add_to(fg_dep)

            fg_dep.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    st_folium(m, width=1400, height=750)

    m.save("carte_fournisseurs.html")
    with open("carte_fournisseurs.html", "rb") as f:
        st.download_button(
            "📥 Télécharger la carte HTML",
            f,
            "carte_fournisseurs.html",
            "text/html"
        )
