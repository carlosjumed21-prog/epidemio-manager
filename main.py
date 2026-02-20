import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment

# --- REGLAS DE NEGOCIO (Igual que antes) ---
ORDEN_TERAPIAS_EXCEL = ["UNIDAD CORONARIA", "UCIA", "TERAPIA POSQUIRURGICA", "U.C.I.N.", "U.T.I.P.", "UNIDAD DE QUEMADOS"]
MAPA_TERAPIAS = {"UNIDAD CORONARIA": "COORD_MODULARES", "U.C.I.N.": "COORD_PEDIATRIA", "U.T.I.P.": "COORD_PEDIATRIA", "TERAPIA POSQUIRURGICA": "COORD_MEDICINA", "UNIDAD DE QUEMADOS": "COORD_CIRUGIA", "UCIA": "COORD_MEDICINA"}
VINCULO_AUTO_INCLUSION = {"COORD_MEDICINA": ["UCIA", "TERAPIA POSQUIRURGICA"], "COORD_CIRUGIA": ["UNIDAD DE QUEMADOS"], "COORD_MODULARES": ["UNIDAD CORONARIA"], "COORD_PEDIATRIA": ["U.C.I.N.", "U.T.I.P."]}
COLORES_INTERFAZ = {"⚠️ UNIDADES DE TERAPIA ⚠️": "#C0392B", "COORD_PEDIATRIA": "#5DADE2", "COORD_MEDICINA": "#1B4F72", "COORD_GINECOLOGIA": "#F06292", "COORD_MODULARES": "#E67E22", "OTRAS_ESPECIALIDADES": "#2C3E50", "COORD_CIRUGIA": "#117864"}
CATALOGO = {"COORD_MEDICINA": ["DERMATO", "ENDOCRINO", "GERIAT", "INMUNO", "MEDICINA INTERNA", "REUMA", "UCIA", "TERAPIA INTERMEDIA", "CLINICA DEL DOLOR", "TPQX", "TERAPIA POSQUIRURGICA", "POSQUIRURGICA"], "COORD_CIRUGIA": ["CIRUGIA GENERAL", "CIR. GENERAL", "MAXILO", "RECONSTRUCTIVA", "PLASTICA", "GASTRO", "NEFROLOGIA", "OFTALMO", "ORTOPEDIA", "OTORRINO", "UROLOGIA", "TRASPLANTES", "QUEMADOS", "UNIDAD DE QUEMADOS"], "COORD_MODULARES": ["ANGIOLOGIA", "VASCULAR", "CARDIOLOGIA", "CARDIOVASCULAR", "TORAX", "NEUMO", "HEMATO", "NEUROCIRUGIA", "NEUROLOGIA", "ONCOLOGIA", "CORONARIA", "UNIDAD CORONARIA", "PSIQ", "PSIQUIATRIA"], "COORD_PEDIATRIA": ["PEDIATRI", "PEDIATRICA", "NEONATO", "NEONATOLOGIA", "CUNERO", "UTIP", "U.T.I.P", "UCIN", "U.C.I.N"], "COORD_GINECOLOGIA": ["GINECO", "OBSTETRICIA", "MATERNO", "REPRODUCCION", "BIOLOGIA DE LA REPRO"]}

def obtener_especialidad_real(cama, esp_html):
    c = str(cama).strip().upper()
    esp_html_clean = esp_html.replace("ESPECIALIDAD:", "").replace("&NBSP;", "").strip().upper()
    if c.startswith("64"): return "UNIDAD CORONARIA"; 
    if c.startswith("55"): return "U.C.I.N."; 
    if c.startswith("45"): return "NEONATOLOGIA"; 
    if c.startswith("56"): return "U.T.I.P."; 
    if c.startswith("85"): return "UNIDAD DE QUEMADOS"; 
    if c.startswith("73"): return "UCIA"
    if c.isdigit() and 7401 <= int(c) <= 7409: return "TERAPIA POSQUIRURGICA"
    return esp_html_clean

def sync_group(cat_name, servicios):
    master_val = st.session_state[f"master_{cat_name}"]
    for s in servicios: st.session_state[f"serv_{cat_name}_{s}"] = master_val

st.title("📋 Censo Epidemiológico Diario")

# VERIFICAR SI HAY ARCHIVO
if 'archivo_compartido' not in st.session_state:
    st.warning("⚠️ Por favor, sube un archivo HTML en la barra lateral.")
else:
    try:
        tablas = pd.read_html(st.session_state['archivo_compartido'])
        df_completo = max(tablas, key=len)
        col0_str = df_completo.iloc[:, 0].fillna("").astype(str).str.upper()
        
        pacs_detectados = []
        especialidades_encontradas = set()
        IGNORAR = ["PACIENTES", "TOTAL", "SUBTOTAL", "PÁGINA", "IMPRESIÓN", "1111"]
        
        esp_actual_temp = "SIN_ESPECIALIDAD"
        for i, val in enumerate(col0_str):
            if "ESPECIALIDAD:" in val: esp_actual_temp = val; continue
            fila = [str(x).strip() for x in df_completo.iloc[i].values]
            if any(x in fila[0] for x in IGNORAR): continue
            if len(fila[1]) >= 5 and any(char.isdigit() for char in fila[1]):
                esp_real = obtener_especialidad_real(fila[0], esp_actual_temp)
                especialidades_encontradas.add(esp_real)
                pacs_detectados.append({"CAMA": fila[0], "REG": fila[1], "PAC": fila[2], "SEXO": fila[3], "EDAD": "".join(re.findall(r'\d+', fila[4])), "DIAG": fila[6], "ING": fila[9], "esp_real": esp_real})

        # --- LÓGICA DE BUCKETS Y RENDERIZADO (Se mantiene igual) ---
        # ... (Aquí sigue todo el código de buckets y los checkboxes que ya tienes)
        # IMPORTANTE: st.session_state mantendrá los checkboxes marcados si no cambias los nombres de las llaves
        
        st.info(f"Pacientes cargados: {len(pacs_detectados)}")
        # (Resto del código de generación de excel del Censo Diario)

    except Exception as e:
        st.error(f"Error: {e}")
