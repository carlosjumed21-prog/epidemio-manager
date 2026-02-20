import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime, timedelta
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

# --- FILTRO OFICIAL ---
SERVICIOS_INSUMOS_FILTRO = ["HEMATOLOGIA", "HEMATOLOGIA PEDIATRICA", "ONCOLOGIA PEDIATRICA", "NEONATOLOGIA", "INFECTOLOGIA PEDIATRICA", "U.C.I.N.", "U.T.I.P.", "TERAPIA POSQUIRURGICA", "UNIDAD DE QUEMADOS", "ONCOLOGIA MEDICA", "UCIA"]

def obtener_especialidad_real(cama, esp_html):
    # (Misma función de detección que usas en el otro archivo)
    c = str(cama).strip().upper()
    if c.startswith("55"): return "U.C.I.N."
    if c.startswith("45"): return "NEONATOLOGIA" 
    if c.startswith("56"): return "U.T.I.P."
    if c.startswith("85"): return "UNIDAD DE QUEMADOS"
    if c.startswith("73"): return "UCIA"
    if c.isdigit() and 7401 <= int(c) <= 7409: return "TERAPIA POSQUIRURGICA"
    return esp_html.replace("ESPECIALIDAD:", "").strip().upper()

st.title("📦 Censo de Insumos")

if 'archivo_compartido' not in st.session_state:
    st.warning("⚠️ Sube el censo en la barra lateral para generar el reporte de insumos.")
else:
    try:
        tablas = pd.read_html(st.session_state['archivo_compartido'])
        df_completo = max(tablas, key=len)
        col0_str = df_completo.iloc[:, 0].fillna("").astype(str).str.upper()
        
        pacs_detectados = []
        esp_actual_temp = "SIN_ESPECIALIDAD"
        for i, val in enumerate(col0_str):
            if "ESPECIALIDAD:" in val: esp_actual_temp = val; continue
            fila = [str(x).strip() for x in df_completo.iloc[i].values]
            if len(fila) > 1 and len(fila[1]) >= 5 and any(char.isdigit() for char in fila[1]):
                esp_real = obtener_especialidad_real(fila[0], esp_actual_temp)
                if esp_real in SERVICIOS_INSUMOS_FILTRO:
                    pacs_detectados.append({"CAMA": fila[0], "REG": fila[1], "PAC": fila[2], "SEXO": fila[3], "EDAD": "".join(re.findall(r'\d+', fila[4])), "ING": fila[9], "esp_real": esp_real})

        if not pacs_detectados:
            st.warning("No hay pacientes para insumos en este censo.")
        else:
            # (Resto de tu lógica de generación de excel de Insumos)
            st.success(f"Listo para procesar {len(pacs_detectados)} pacientes críticos.")
            # ... (Código del Excel con las precauciones estándar/protector corregidas)

    except Exception as e:
        st.error(f"Error: {e}")
