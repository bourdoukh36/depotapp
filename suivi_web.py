import os
import streamlit as st
import openpyxl
from openpyxl import Workbook
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------- CONFIG GOOGLE SHEETS ----------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"],
    SCOPE
)

client = gspread.authorize(creds)
SHEET_NAME = "suivi des opérations"

# ---------- DONNÉES FIXES ----------
SERRES = ['B', 'C', 'D', 'E', 'F', 'G', 'H']
DELTAS = [str(i) for i in range(1, 33)]
CULTURES = ['tomate', 'pastèque', 'poivron', 'concombre', 'laitue', 'ciboulette', 'courgette', 'herbes aromatiques']
TRAITEMENTS = ['fongicide', 'insecticide', 'acaricide', 'insecticide/acaricide', 'raticide', 'bio-stimulant',
               'désinfectant', 'engrais foliaire']
SOLUTIONS_IRRI = ['AB', 'CD', 'M', 'Urée', 'enracineur', 'désinfectant']
ECS = ['1.6', '1.8', '2', '2.5', '3', '3.5', '4']

EXCEL_PRODUITS = "produits.xlsx"

# ---------- CREATION AUTOMATIQUE PRODUITS.XLSX ----------
def creer_excel_produits():
    if not os.path.exists(EXCEL_PRODUITS):
        wb = Workbook()
        ws = wb.active
        ws.title = "Produits"
        ws.append(["Designation", "Dose", "Cible"])
        # Produits par défaut
        ws.append(["Vertimec", "50 cc/hl", "Acariens"])
        ws.append(["Confidor", "30 cc/hl", "Insectes"])
        wb.save(EXCEL_PRODUITS)

creer_excel_produits()

# ---------- FONCTIONS PRODUITS ----------
def charger_produits():
    wb = openpyxl.load_workbook(EXCEL_PRODUITS)
    ws = wb.active
    return [row for row in ws.iter_rows(min_row=2, values_only=True) if row]

def ajouter_produit(designation, dose, cible):
    wb = openpyxl.load_workbook(EXCEL_PRODUITS)
    ws = wb.active
    ws.append([designation, dose, cible])
    wb.save(EXCEL_PRODUITS)
    st.success(f"Produit ajouté : {designation} | {dose} | {cible}")

def modifier_produit(index, designation, dose, cible):
    wb = openpyxl.load_workbook(EXCEL_PRODUITS)
    ws = wb.active
    ws.delete_rows(index + 2)  # +2 pour sauter l'entête
    ws.append([designation, dose, cible])
    wb.save(EXCEL_PRODUITS)
    st.success(f"Produit modifié : {designation} | {dose} | {cible}")

def supprimer_produit(index):
    wb = openpyxl.load_workbook(EXCEL_PRODUITS)
    ws = wb.active
    ws.delete_rows(index + 2)  # +2 pour l'entête
    wb.save(EXCEL_PRODUITS)
    st.success("Produit supprimé")

# ---------- UI STREAMLIT ----------
st.title("Suivi des opérations - Pépinière")

# Selection principale
serre = st.selectbox("Serre", SERRES)
delta = st.selectbox("Delta", DELTAS)
culture = st.selectbox("Culture", CULTURES)
operation = st.selectbox("Opération", ["traitement", "irrigation"])

st.subheader("Détails de l'opération")

# Gestion produit pour traitement
if operation == "traitement":
    produits = charger_produits()
    if produits:
        st.subheader("Produits existants")
        for i, p in enumerate(produits):
            col1, col2, col3, col4, col5 = st.columns([3,2,2,1,1])
            col1.write(p[0])
            col2.write(p[1])
            col3.write(p[2])
            if col4.button("Modifier", key=f"mod_{i}"):
                with st.form(f"mod_form_{i}"):
                    new_des = st.text_input("Désignation", p[0])
                    new_dose = st.text_input("Dose", p[1])
                    new_cible = st.text_input("Cible", p[2])
                    submit = st.form_submit_button("Enregistrer modification")
                    if submit:
                        modifier_produit(i, new_des, new_dose, new_cible)
                        st.experimental_rerun()
            if col5.button("Supprimer", key=f"sup_{i}"):
                supprimer_produit(i)
                st.experimental_rerun()
    else:
        st.info("Aucun produit enregistré pour le moment.")

    # Ajouter un nouveau produit
    st.subheader("Ajouter un nouveau produit")
    with st.form("form_ajout_produit"):
        new_des = st.text_input("Désignation")
        new_dose = st.text_input("Dose")
        new_cible = st.text_input("Cible")
        submit = st.form_submit_button("Ajouter Produit")
        if submit:
            if new_des and new_dose and new_cible:
                ajouter_produit(new_des, new_dose, new_cible)
                st.experimental_rerun()
            else:
                st.error("Remplissez tous les champs pour ajouter un produit.")

    # Sélection du produit pour l'opération
    produits = charger_produits()
    produit_sel = st.selectbox("Sélectionner un produit pour le traitement",
                               [p[0] for p in produits])

    traitement = st.selectbox("Type de traitement", TRAITEMENTS)

# Gestion irrigation
elif operation == "irrigation":
    solution = st.selectbox("Solution", SOLUTIONS_IRRI)
    ec = st.selectbox("EC", ECS)

# ---------- FONCTION GOOGLE SHEETS ----------
def get_or_create_sheet(serre, delta):
    try:
        sh = client.open(SHEET_NAME)
        try:
            ws = sh.worksheet(f"{serre}{delta}")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=f"{serre}{delta}", rows=1000, cols=20)
            ws.append_row(['Date', 'Serre', 'Delta', 'Culture', 'Operation', 'Details'])
        return ws
    except gspread.SpreadsheetNotFound:
        sh = client.create(SHEET_NAME)
        sh.share(None, perm_type='anyone', role='writer')
        ws = sh.sheet1
        ws.append_row(['Date', 'Serre', 'Delta', 'Culture', 'Operation', 'Details'])
        return ws

# ---------- ENREGISTREMENT ----------
if st.button("Enregistrer l'opération"):
    ws = get_or_create_sheet(serre, delta)
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    if operation == "traitement":
        # Détails produit sélectionné
        for p in charger_produits():
            if p[0] == produit_sel:
                details = f"{traitement} - {p[0]} | {p[1]} | {p[2]}"
                break
        else:
            details = f"{traitement} - {produit_sel}"
    else:
        details = f"{solution} EC {ec}"

    ws.append_row([date, serre, delta, culture, operation, details])
    st.success(f"Enregistré dans feuille {serre}{delta}")
