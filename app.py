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

/* LOGO HEADER */
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
# 🟢 LOGO IRISOLARIS (AJOUT ICI)
# ==========================================================
st.markdown("""
<div class="logo-container">
    <img src="https://www.bing.com/images/search?view=detailV2&ccid=npibC1Np&id=520172A6B498CBC4ECE46F5AFD767099ED0831B2&thid=OIP.npibC1NpyzXXUjUiY_0TzQAAAA&mediaurl=https%3a%2f%2fstatic.wixstatic.com%2fmedia%2fae40a5_6e4ea3bf61a6483fb68c686b1e74bac4%7emv2.png%2fv1%2ffill%2fw_336%2ch_57%2cal_c%2cusm_0.66_1.00_0.01%2fLOGO_ENTREPRISE_CORPO-01.png&cdnurl=https%3a%2f%2fth.bing.com%2fth%2fid%2fR.9e989b0b5369cb35d752352263fd13cd%3frik%3dsjEI7Zlwdv1abw%26pid%3dImgRaw%26r%3d0&exph=57&expw=336&q=irisolaris+logo&FORM=IRPRST&ck=87FBB8EF84D3D8EAB8CA1E3769039FF3&selectedIndex=3&itb=1">
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

# ==========================================================
# GEOJSON FRANCE
# ==========================================================
url = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"
gdf = gpd.read_file(url)

# ==========================================================
# COULEURS PAR STATUT NUMERIQUE
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
                "email": imp.get("email", "")
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

# ==========================================================
# DATAFRAME
# ==========================================================
with st.expander("📄 Données Excel"):
    st.dataframe(df, use_container_width=True)

# ==========================================================
# HEATMAP
# ==========================================================
def heat_color(n):
    if n == 0:
        return "#f0f0f0"
    elif n == 1:
        return "#2b83ba"
    elif n == 2:
        return "#abdda4"
    elif n == 3:
        return "#ffffbf"
    elif n == 4:
        return "#fdae61"
    else:
        return "#d7191c"

dep_count = {
    dep: len(set([x["entreprise"] for x in items]))
    for dep, items in dep_data.items()
}

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
# CONTOURS DEPARTEMENTS + POPUP
# ==========================================================
fg_contours = folium.FeatureGroup(name="🗺️ Départements", show=True)

for _, r in gdf.iterrows():

    code = r["code"]

    if code in dep_data:

        data = dep_data[code]

        html = f"<h4>Département {code}</h4>"
        html += f"<b>{len(data)} implantation(s)</b><br><br>"

        for d in data:
            html += f"""
            <b>{d['entreprise']}</b><br>
            {d['adresse']}<br>
            👤 {d['contact']}<br>
            📞 {d['tel']}<br>
            📧 {d['email']}<br><br>
            """

    else:
        html = f"<h4>Département {code}</h4>Aucune implantation"

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
        popup=folium.Popup(html, max_width=450)
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

        folium.Marker(
            location=[imp["lat"], imp["lon"]],
            tooltip=ent["nom"],
            icon=folium.Icon(color=color),
            popup=f"""
            <b style="color:{color};">{ent['nom']}</b><br>
            {imp.get('adresse','')}<br><br>
            👤 {imp.get('contact','')}<br>
            📧 {imp.get('email','')}<br>
            📞 {imp.get('tel','')}
            """
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
    
