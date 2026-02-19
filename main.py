import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="EpidemioManager - CMN 20 de Noviembre", layout="wide")

# --- LÓGICA DE NEGOCIO (Respetando tus reglas de CMN 20 de Noviembre) ---
MAPA_TERAPIAS = {
    "UNIDAD CORONARIA": "COORD_MODULARES", "U.C.I.N.": "COORD_PEDIATRIA",
    "U.T.I.P.": "COORD_PEDIATRIA", "TERAPIA POSQUIRURGICA": "COORD_MEDICINA",
    "UNIDAD DE QUEMADOS": "COORD_CIRUGIA", "UCIA": "COORD_MEDICINA"
}

CATALOGO = {
    "COORD_MEDICINA": ["DERMATO", "ENDOCRINO", "GERIAT", "INMUNO", "MEDICINA INTERNA", "PSIQ", "REUMA", "UCIA", "TERAPIA INTERMEDIA", "CLINICA DEL DOLOR", "TPQX", "TERAPIA POSQUIRURGICA", "POSQUIRURGICA"],
    "COORD_CIRUGIA": ["CIRUGIA GENERAL", "CIR. GENERAL", "MAXILO", "RECONSTRUCTIVA", "PLASTICA", "GASTRO", "NEFROLOGIA", "OFTALMO", "ORTOPEDIA", "OTORRINO", "UROLOGIA", "TRASPLANTES", "QUEMADOS", "UNIDAD DE QUEMADOS"],
    "COORD_MODULARES": ["ANGIOLOGIA", "VASCULAR", "CARDIOLOGIA", "CARDIOVASCULAR", "TORAX", "NEUMO", "HEMATO", "NEUROCIRUGIA", "NEUROLOGIA", "ONCOLOGIA", "CORONARIA", "UNIDAD CORONARIA"],
    "COORD_PEDIATRIA": ["PEDIATRI", "PEDIATRICA", "NEONATO", "NEONATOLOGIA", "CUNERO", "UTIP", "U.T.I.P", "UCIN", "U.C.I.N", "MEDICINA INTERNA PEDIATRICA (5-4)"],
    "COORD_GINECOLOGIA": ["GINECO", "OBSTETRICIA", "MATERNO", "REPRODUCCION", "BIOLOGIA DE LA REPRO"]
}

def obtener_especialidad_real(cama, esp_html):
    c = str(cama).strip().upper()
    esp_html_clean = esp_html.replace("ESPECIALIDAD:", "").replace("&NBSP;", "").strip().upper()
    if c.startswith("64"): return "UNIDAD CORONARIA"
    if c.startswith("55"): return "U.C.I.N."
    if c.startswith("45"): return "NEONATOLOGIA" 
    if c.startswith("56"): return "U.T.I.P."
    if c.startswith("85"): return "UNIDAD DE QUEMADOS"
    if c.startswith("73"): return "UCIA"
    return esp_html_clean

# --- INTERFAZ ---
st.title("🏥 EpidemioManager - ISSSTE")
st.caption("Residente: Carlos | Epidemiología - CMN 20 de Noviembre")

archivo = st.file_uploader("Subir Censo HTML", type=["html", "htm"])

if archivo:
    try:
        tablas = pd.read_html(archivo)
        df_completo = max(tablas, key=len)
        col0_str = df_completo.iloc[:, 0].fillna("").astype(str).str.upper()
        
        pacs_detectados = []
        especialidades_encontradas = set()
        
        esp_actual_temp = "SIN_ESPECIALIDAD"
        for i, val in enumerate(col0_str):
            if "ESPECIALIDAD:" in val:
                esp_actual_temp = val
                continue
            fila = [str(x).strip() for x in df_completo.iloc[i].values]
            if len(fila[1]) >= 5 and any(char.isdigit() for char in fila[1]):
                esp_real = obtener_especialidad_real(fila[0], esp_actual_temp)
                especialidades_encontradas.add(esp_real)
                pacs_detectados.append({**dict(zip(["CAMA", "REG", "PAC", "SEXO", "EDAD", "D", "DIAG", "F", "H", "ING"], fila)), "esp_real": esp_real})

        # --- BUCKETS (Agrupación) ---
        buckets = {"⚠️ UNIDADES DE TERAPIA ⚠️": [e for e in especialidades_encontradas if e in MAPA_TERAPIAS]}
        # Agregar el resto de coordinaciones
        for cat, items in CATALOGO.items():
            found = [e for e in especialidades_encontradas if any(kw in e for kw in items) and e not in MAPA_TERAPIAS]
            if found: buckets[cat] = found

        st.write("---")
        st.subheader(f"2. Servicios Detectados ({len(pacs_detectados)} pacientes)")

        # --- LÓGICA DE SELECCIÓN MAESTRA ---
        for cat_name, servicios in buckets.items():
            # Estilo visual de la cabecera (Rojo para terapias, Gris para el resto)
            bg_color = "#C0392B" if "TERAPIA" in cat_name else "#2E4053"
            
            st.markdown(f"""<div style="background-color:{bg_color}; padding:10px; border-radius:5px; margin-bottom:5px;">
                <h4 style="color:white; margin:0;">{cat_name}</h4></div>""", unsafe_allow_html=True)
            
            # Checkbox Maestro
            master_key = f"master_{cat_name}"
            todo = st.checkbox(f"Seleccionar todo: {cat_name}", key=master_key)
            
            # Checkboxes Hijos
            for s in servicios:
                # El valor del hijo depende del maestro
                st.checkbox(s, value=todo, key=f"s_{s}")

        st.write("---")

        # --- BOTÓN GENERAR ---
        if st.button("🚀 GENERAR EXCEL", type="primary", use_container_width=True):
            # Recolección forzada del estado de las casillas
            seleccionados = [s for s in especialidades_encontradas if st.session_state.get(f"s_{s}")]
            
            if not seleccionados:
                st.error("⚠️ Debes seleccionar al menos un servicio arriba.")
            else:
                fecha_hoy = datetime.now()
                datos_excel = []
                for p in pacs_detectados:
                    if p["esp_real"] in seleccionados:
                        datos_excel.append({
                            "FECHA": fecha_hoy.strftime("%d/%m/%Y"),
                            "ESPECIALIDAD": p["esp_real"],
                            "CAMA": p["CAMA"], "REGISTRO": p["REG"],
                            "PACIENTE": p["PAC"], "DIAGNOSTICO": p["DIAG"],
                            "INGRESO": p["ING"]
                        })

                # Crear Excel
                output = BytesIO()
                pd.DataFrame(datos_excel).to_excel(output, index=False)
                output.seek(0)
                
                st.success(f"Excel listo con {len(datos_excel)} pacientes.")
                st.download_button("💾 DESCARGAR EXCEL", data=output.read(), 
                                   file_name=f"Censo_{fecha_hoy.strftime('%d%m%Y')}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        st.error(f"Error: {e}")
