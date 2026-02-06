import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import base64


# ---------------- FONCTION LOGO MOBILE COMPATIBLE ----------------
@st.cache_data
def get_logo_base64():
    logo_path = "logo.png"
    try:
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        st.error("❌ logo.png manquant dans le dossier app")
        return None


# ---------------- CONFIG ----------------
SERRES = ['B', 'C', 'D', 'E', 'F', 'G', 'H']
DELTAS = [str(i) for i in range(1, 33)]
CULTURES = ['tomate', 'pastèque', 'poivron', 'concombre', 'laitue', 'ciboulette', 'courgette', 'herbes aromatiques']
OPERATIONS = ['traitement', 'irrigation']
SOLUTIONS_IRRI = ['AB', 'CD', 'M', 'Urée', 'enracineur', 'désinfectant']
ECS = ['1.6', '1.8', '2', '2.5', '3', '3.5', '4']

# ---------------- CSS ----------------
st.markdown("""
<style>
.main { background-color: #f0f8f0; }
.stSelectbox > div > div > div,
.stTextInput > div > div > input {
    background-color: #e8f5e8 !important;
    border: 2px solid #4caf50 !important;
    border-radius: 8px !important;
}
.stButton > button {
    background: linear-gradient(45deg, #4caf50, #45a049) !important;
    color: white !important;
    border-radius: 25px !important;
    font-weight: bold !important;
}
</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="Suivi Opérations", layout="centered")

# ---------------- LOGO ----------------
logo_base64 = get_logo_base64()
if logo_base64:
    st.markdown(f"""
    <div style="text-align:center">
        <img src="data:image/png;base64,{logo_base64}" width="200">
    </div>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center;color:#2e7d32'>Suivi des opérations – Pépinière</h1>", unsafe_allow_html=True)

# ---------------- GOOGLE SHEET ----------------
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
SPREADSHEET_NAME = "suivi des opérations"


# ---------------- PRODUITS EXCEL ----------------
@st.cache_data
def load_produits():
    try:
        df = pd.read_excel("produits.xlsx")
        df = df.dropna(subset=['Designation']).reset_index(drop=True)
        return df
    except (FileNotFoundError, ValueError):
        df = pd.DataFrame(columns=['Designation', 'dose', 'cible', 'mode_d_application'])
        df.to_excel("produits.xlsx", index=False)  # Crée Sheet1 par défaut
        return df


# ---------------- UI PRINCIPALE ----------------
col1, col2, col3, col4 = st.columns(4)
with col1: serre = st.selectbox("**Serre**", SERRES)
with col2: deltas = st.multiselect("**Delta(s)**", DELTAS)
with col3: culture = st.selectbox("**Culture**", CULTURES)
with col4: operation = st.selectbox("**Opération**", OPERATIONS)

details = ""

# ---------------- TRAITEMENT ----------------
if operation == "traitement":
    produits_df = load_produits()
    produits_list = produits_df['Designation'].dropna().unique().tolist()
    produits_selectionnes = st.multiselect("**🧪 Produits**", produits_list)

    details_list = []
    if produits_selectionnes:
        for i, produit in enumerate(produits_selectionnes):
            row = produits_df[produits_df['Designation'] == produit].iloc[0]
            c1, c2, c3 = st.columns(3)
            with c1: st.text_input(f"Dose ({produit})", row['dose'], disabled=True, key=f"d{i}")
            with c2: st.text_input(f"Cible ({produit})", row['cible'], disabled=True, key=f"c{i}")
            with c3: st.text_input(f"Mode ({produit})", row['mode_d_application'], disabled=True, key=f"m{i}")
            details_list.append(f"{produit} - {row['dose']} - {row['cible']}")

    details = " | ".join(details_list)


# ---------------- IRRIGATION ----------------
elif operation == "irrigation":
    c1, c2 = st.columns(2)
    with c1:
        solution = st.selectbox("Solution", SOLUTIONS_IRRI)
    with c2:
        ec = st.selectbox("EC", ECS)
    details = f"{solution} EC {ec}"

# ---------------- ENREGISTRER ----------------
if deltas and details and st.button("💾 ENREGISTRER"):
    try:
        sh = client.open(SPREADSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = client.create(SPREADSHEET_NAME)

    for delta in deltas:
        feuille = f"{serre}{delta}"
        try:
            ws = sh.worksheet(feuille)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=feuille, rows=1000, cols=10)
            ws.append_row(["Date", "Serre", "Delta", "Culture", "Operation", "Details"])

        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            serre, delta, culture, operation, details
        ])

    st.success(f"✅ Enregistré dans {len(deltas)} feuille(s): {serre + deltas[0]}...")
    st.rerun()

# ---------------- AJOUT PRODUIT CORRIGÉ (SIMPLE & SÛR) ----------------
st.divider()
with st.form("ajout_produit"):
    c1, c2, c3, c4 = st.columns(4)
    with c1: designation = st.text_input("Nom produit")
    with c2: dose = st.text_input("Dose")
    with c3: cible = st.text_input("Cible")
    with c4: mode = st.selectbox("Mode", ["feuilles", "racines", "sol", "général"])

    if st.form_submit_button("➕ Ajouter"):
        # MÉTHODE SIMPLE : Lire → Ajouter ligne → Réécrire
        df = load_produits()
        new_row = [designation, dose, cible, mode]
        df.loc[len(df)] = new_row  # Ajoute directement
        df.to_excel("produits.xlsx", index=False)  # Réécrit TOUT (Sheet1 auto)

        st.cache_data.clear()
        st.success(f"✅ '{designation}' ajouté ! ({len(df)} produits total)")
        st.rerun()

# ---------------- VISUALISER ----------------
with st.expander("📋 Produits"):
    st.dataframe(load_produits(), use_container_width=True)

if st.button("🔄 Vider cache produits"):
    st.cache_data.clear()
    st.rerun()
