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
    layout="wide"
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
    font-size: 42px !important;
    font-weight: 700;
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

</style>
""", unsafe_allow_html=True)

# ==========================================================
# LOGO
# ==========================================================
st.markdown("""
<div style="text-align:center; margin-bottom:30px;">
    <img src="https://raw.githubusercontent.com/HUGOIRG/carte-fournisseur/main/Logo_Support_Long.png"
         width="350">
</div>
""", unsafe_allow_html=True)

# ==========================================================
# TITRE
# ==========================================================
st.markdown("""
# 📍 Cartographie fournisseurs
### Visualisation des implantations & départements
""")

# ==========================================================
# UPLOAD EXCEL
# ==========================================================
file = st.file_uploader("📂 Import Excel", type=["xlsx"])

if file is None:
    st.info("Upload Excel pour générer la carte")
    st.stop()

df = pd.read_excel(file, engine="openpyxl")

# NORMALISATION COLONNES (IMPORTANT)
df.columns = df.columns.str.strip().str.lower()

# ==========================================================
# GEOJSON FRANCE
# ==========================================================
url = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"
gdf = gpd.read_file(url)

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
    except:
        return "gray"

# ==========================================================
# RECONSTRUCTION ENTREPRISES
# ==========================================================
ENTREPRISES = []

for ent_name, group in df.groupby("entreprise"):

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
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("🏢 Entreprises", len(ENTREPRISES))

with col2:
    st.metric("📍 Implantations", len(df))

with col3:
    st.metric("🗺️ Départements", len(dep_data))

st.divider()

with st.expander("📄 Données Excel"):
    st.dataframe(df, use_container_width=True)

# ==========================================================
# HEATMAP
# ==========================================================
max_count = max(dep_count.values()) if dep_count else 1

def heat_color(n):
    if n == 0:
        return "#f0f0f0"

    ratio = n / max_count

    if ratio < 0.2:
        return "#d4f0ff"      # bleu très clair
    elif ratio < 0.4:
        return "#7fc8f8"      # bleu
    elif ratio < 0.6:
        return "#7fd37f"      # vert
    elif ratio < 0.8:
        return "#ffd966"      # jaune
    elif ratio < 0.95:
        return "#f4a261"      # orange
    else:
        return "#d62828"      # rouge

dep_count = { dep: len(set([x["entreprise"] for x in items])) for dep, items in dep_data.items() }

# ==========================================================
# MAP
# ==========================================================
m = folium.Map(location=[46.7, 2.5], zoom_start=6, tiles=None)

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
    attr="Google Maps",
    name="Google Maps"
).add_to(m)

# ==========================================================
# ==========================================================
# DEPARTEMENTS + POPUP
# ==========================================================
fg_contours = folium.FeatureGroup(name="🗺️ Départements", show=True)

for _, r in gdf.iterrows():

    code = r["code"]

    if code in dep_data:

        data = dep_data[code]

        html = f"""
        <h4>Département {code}</h4>
        <b>{len(data)} implantation(s)</b><br><br>

        <div style="
            max-height:400px;
            width:100%;
            overflow-y:auto;
            overflow-x:hidden;
            padding-right:8px;
        ">
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

        html = f"""
        <h4>Département {code}</h4>
        Aucune implantation
        """

    fill = heat_color(dep_count.get(code, 0))

    folium.GeoJson(
        r["geometry"],
        style_function=lambda x, fill=fill: {
            "fillColor": fill,
            "color": "black",
            "weight": 0.7,
            "fillOpacity": 0.2
        },
        tooltip=f"Département {code}",
        popup=folium.Popup(
            html,
            max_width=450
        )
    ).add_to(fg_contours)

fg_contours.add_to(m)

# ==========================================================
# IMPLANTATIONS
# ==========================================================
for ent in ENTREPRISES:

    color = get_color(ent["statut_nego"])

    fg = folium.FeatureGroup(
        name=f"🏢 {ent['nom']}",
        show=True
    )

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
            🔗 <a href="{sharepoint_link}" target="_blank">
                Ouvrir Sharepoint
            </a>
            """

        folium.Marker(
            location=[imp["lat"], imp["lon"]],
            tooltip=ent["nom"],
            icon=folium.Icon(color=color),
            popup=folium.Popup(popup_html, max_width=350)
        ).add_to(fg)

    fg.add_to(m)

# ==========================================================
# DEPARTEMENTS PAR ENTREPRISE
# ==========================================================
for ent in ENTREPRISES:

    fg_dep = folium.FeatureGroup(
        name=f"🟦 {ent['nom']} - Départements",
        show=False
    )

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

# ==========================================================
# CONTROL LAYERS
# ==========================================================
folium.LayerControl(collapsed=False).add_to(m)

# ==========================================================
# DISPLAY
# ==========================================================
st_folium(m, width=1400, height=800)

# ==========================================================
# EXPORT HTML
# ==========================================================
m.save("carte_fournisseurs.html")

with open("carte_fournisseurs.html", "rb") as f:
    st.download_button(
        "📥 Télécharger la carte HTML",
        f,
        "carte_fournisseurs.html",
        "text/html"
    )
