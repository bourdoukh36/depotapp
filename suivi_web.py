import os
import streamlit as st
import openpyxl
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------- CONFIG GOOGLE SHEETS ----------
SCOPE = ["https://spreadsheets.google.com/feeds",
         'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    r'C:\Users\hp\PycharmProjects\suivi des opérations\credentials.json', SCOPE
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
if not os.path.exists(EXCEL_PRODUITS):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Designation", "Dose", "Cible"])
    wb.save(EXCEL_PRODUITS)


def charger_produits():
    wb = openpyxl.load_workbook(EXCEL_PRODUITS)
    ws = wb.active
    return [row for row in ws.iter_rows(min_row=2, values_only=True) if row]


def ajouter_produit(designation, dose, cible):
    wb = openpyxl.load_workbook(EXCEL_PRODUITS)
    ws = wb.active
    ws.append([designation, dose, cible])
    wb.save(EXCEL_PRODUITS)


# ---------- INTERFACE STREAMLIT ----------
st.title("Suivi Opérations Pépinière")

# Serre / Delta / Culture
serre = st.selectbox("Serre", SERRES)
delta = st.selectbox("Delta", DELTAS)
culture = st.selectbox("Culture", CULTURES)
operation = st.selectbox("Opération", ["traitement", "irrigation"])

# --- Formulaire Traitement ---
if operation == "traitement":
    traitement = st.selectbox("Traitement", TRAITEMENTS)
    produits = charger_produits()
    produit_names = [p[0] for p in produits]
    produit = st.selectbox("Produit", produit_names)
    dose = st.text_input("Dose", value=[p[1] for p in produits if p[0] == produit][0])
    cible = st.text_input("Cible", value=[p[2] for p in produits if p[0] == produit][0])

# --- Formulaire Irrigation ---
else:
    solution = st.selectbox("Solution", SOLUTIONS_IRRI)
    ec = st.selectbox("EC", ECS)

# --- Ajouter Produit ---
st.subheader("Ajouter un nouveau produit")
new_des = st.text_input("Designation")
new_dose = st.text_input("Dose")
new_cible = st.text_input("Cible")
if st.button("Ajouter Produit"):
    if new_des and new_dose and new_cible:
        ajouter_produit(new_des, new_dose, new_cible)
        st.success(f"Produit {new_des} ajouté")
    else:
        st.error("Remplissez tous les champs pour ajouter un produit")

# --- Enregistrement dans Google Sheets ---
if st.button("Enregistrer opération"):
    sh = client.open(SHEET_NAME)
    feuille_nom = f"{serre}{delta}"
    try:
        sheet = sh.worksheet(feuille_nom)
    except gspread.WorksheetNotFound:
        sheet = sh.add_worksheet(title=feuille_nom, rows=1000, cols=20)
        # Headers
        if operation == "traitement":
            headers = ['Date', 'Serre', 'Delta', 'Culture', 'Operation', 'Traitement', 'Designation', 'Dose', 'Cible']
        else:
            headers = ['Date', 'Serre', 'Delta', 'Culture', 'Operation', 'Details']
        sheet.append_row(headers)

    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    if operation == "traitement":
        row = [date, serre, delta, culture, operation, traitement, produit, dose, cible]
    else:
        details = f"{solution} EC{ec}"
        row = [date, serre, delta, culture, operation, details]

    sheet.append_row(row)
    st.success(f"Enregistré dans feuille {feuille_nom} ✅")
