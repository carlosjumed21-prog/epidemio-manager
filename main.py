import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="EpidemioManager Web", layout="wide")

# --- LÓGICA DE CLASIFICACIÓN (Tu lógica original intacta) ---
MAPA_TERAPIAS = {
    "UNIDAD CORONARIA": "COORD_MODULARES", "U.C.I.N.": "COORD_PEDIATRIA",
    "U.T.I.P.": "COORD_PEDIATRIA", "TERAPIA POSQUIRURGICA": "COORD_MEDICINA",
    "UNIDAD DE QUEMADOS": "COORD_CIRUGIA", "UCIA": "COORD_MEDICINA"
}

CATALOGO = {
    "COORD_MEDICINA": ["DERMATO", "ENDOCRINO", "GERIAT", "INMUNO", "MEDICINA INTERNA", "PSIQ", "REUMA", "UCIA", "TERAPIA INTERMEDIA", "CLINICA DEL DOLOR", "TPQX", "TERAPIA POSQUIRURGICA"],
    "COORD_CIRUGIA": ["CIRUGIA GENERAL", "MAXILO", "RECONSTRUCTIVA", "PLASTICA", "GASTRO", "NEFROLOGIA", "OFTALMO", "ORTOPEDIA", "OTORRINO", "UROLOGIA", "TRASPLANTES", "QUEMADOS"],
    "COORD_MODULARES": ["ANGIOLOGIA", "VASCULAR", "CARDIOLOGIA", "CARDIOVASCULAR", "TORAX", "NEUMO", "HEMATO", "NEUROCIRUGIA", "NEUROLOGIA", "ONCOLOGIA", "CORONARIA"],
    "COORD_PEDIATRIA": ["PEDIATRI", "NEONATO", "CUNERO", "UTIP", "UCIN", "MEDICINA INTERNA PEDIATRICA"],
    "COORD_GINECOLOGIA": ["GINECO", "OBSTETRICIA", "MATERNO", "REPRODUCCION"]
}

def clasificar_especialidad(nombre_esp):
    n = nombre_esp.upper()
    if n in MAPA_TERAPIAS: return "COORD_TERAPIAS"
    if "PEDIATRICA" in n or "PEDIATRI" in n: return "COORD_PEDIATRIA"
    for c, kws in CATALOGO.items():
        if any(kw in n for kw in kws): return c
    return "OTRAS_ESPECIALIDADES"

def obtener_especialidad_real(cama, esp_html):
    c = str(cama).strip().upper()
    esp_html_clean = esp_html.replace("ESPECIALIDAD:", "").replace("&NBSP;", "").strip().upper()
    if c.startswith("64"): return "UNIDAD CORONARIA"
    if c.startswith("55"): return "U.C.I.N."
    if c.startswith("45"): return "NEONATOLOGIA"
    if c.startswith("85"): return "UNIDAD DE QUEMADOS"
    if c.startswith("73"): return "UCIA"
    return esp_html_clean

# --- INTERFAZ STREAMLIT ---
st.title("🏥 EpidemioManager - Control UNAM")
st.sidebar.header("Menú de Navegación")
opcion = st.sidebar.selectbox("Selecciona un Módulo", ["1. Censo Diario", "2. Captura Clínica"])

if opcion == "1. Censo Diario":
    st.header("Extracción de Censo")
    archivo_subido = st.file_uploader("Sube el archivo HTML del censo", type=["html", "htm"])

    if archivo_subido:
        tablas = pd.read_html(archivo_subido)
        df_completo = max(tablas, key=len)
        
        # Procesamiento rápido para mostrar estadísticas
        pacs_ini = 0
        especialidades_detectadas = set()
        col0_str = df_completo.iloc[:, 0].fillna("").astype(str).str.upper()
        
        esp_temp = "SIN_CLASIFICAR"
        for i, val in enumerate(col0_str):
            if "ESPECIALIDAD:" in val: esp_temp = val
            reg_val = str(df_completo.iloc[i, 1])
            if len(reg_val) >= 5 and any(char.isdigit() for char in reg_val):
                pacs_ini += 1
                especialidades_detectadas.add(obtener_especialidad_real(val, esp_temp))

        col1, col2 = st.columns(2)
        col1.metric("Pacientes Detectados", pacs_ini)
        col2.metric("Especialidades", len(especialidades_detectadas))

        # Selección de Coordinaciones
        st.subheader("Selecciona las Coordinaciones a exportar")
        coords_disponibles = ["COORD_MEDICINA", "COORD_CIRUGIA", "COORD_MODULARES", "COORD_PEDIATRIA", "COORD_GINECOLOGIA", "COORD_TERAPIAS"]
        seleccion = st.multiselect("Coordinaciones:", coords_disponibles, default=coords_disponibles)

        if st.button("Generar y Descargar Excel"):
            # Lógica de procesamiento final
            datos_finales = []
            fecha_hoy = datetime.now().strftime("%d/%m/%Y")
            
            # (Aquí se repite tu lógica de iteración sobre el DF que ya tienes)
            # Simplificado para el ejemplo:
            for _, row in df_completo.iterrows():
                # ... tu lógica de extracción de datos ...
                pass # Aquí insertarías el bloque de 'procesar_final' de tu código original

            # Crear el Excel en memoria
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # df_resultado.to_excel(writer, index=False, sheet_name='Censo')
                # (Simulación de DF para el ejemplo)
                pd.DataFrame([{"Aviso": "Procesamiento completado"}]).to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Descargar Reporte Excel",
                data=output.getvalue(),
                file_name=f"Censo_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

elif opcion == "2. Captura Clínica":
    st.info("Módulo de Captura Clínica en desarrollo para versión web.")