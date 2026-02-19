import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime, timedelta
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="EpidemioManager - CMN 20 de Noviembre", layout="wide")

# --- REGLAS DE NEGOCIO ---
SERVICIOS_INSUMOS_FILTRO = [
    "ONCOLOGÍA PEDIATRICA", "NEONATOLOGIA", "INFECTOTOLOGIA PEDIATRICA", 
    "U.C.I.N.", "U.T.I.P.", "TERAPIA POSQUIRURGICA", 
    "UNIDAD DE QUEMADOS", "ONCOLOGIA MEDICA", "UCIA"
]

MAPA_TERAPIAS = {
    "UNIDAD CORONARIA": "COORD_MODULARES", "U.C.I.N.": "COORD_PEDIATRIA",
    "U.T.I.P.": "COORD_PEDIATRIA", "TERAPIA POSQUIRURGICA": "COORD_MEDICINA",
    "UNIDAD DE QUEMADOS": "COORD_CIRUGIA", "UCIA": "COORD_MEDICINA"
}

COLORES_INTERFAZ = {
    "⚠️ UNIDADES DE TERAPIA ⚠️": "#C0392B", "COORD_PEDIATRIA": "#5DADE2",
    "COORD_MEDICINA": "#1B4F72", "COORD_GINECOLOGIA": "#F06292",
    "COORD_MODULARES": "#E67E22", "OTRAS_ESPECIALIDADES": "#2C3E50", "COORD_CIRUGIA": "#117864"
}

# --- FUNCIONES DE FECHAS Y CLASIFICACIÓN ---
def get_report_dates():
    """Calcula la fecha de hoy y la fecha de vencimiento (7 días después)"""
    hoy = datetime.now()
    vencimiento = hoy + timedelta(days=7)
    return hoy.strftime("%d/%m/%y"), vencimiento.strftime("%d/%m/%y")

def obtener_especialidad_real(cama, esp_html):
    c = str(cama).strip().upper()
    esp_html_clean = esp_html.replace("ESPECIALIDAD:", "").replace("&NBSP;", "").strip().upper()
    if c.startswith("64"): return "UNIDAD CORONARIA"
    if c.startswith("55"): return "U.C.I.N."
    if c.startswith("45"): return "NEONATOLOGIA" 
    if c.startswith("56"): return "U.T.I.P."
    if c.startswith("85"): return "UNIDAD DE QUEMADOS"
    if c.startswith("73"): return "UCIA"
    if c.isdigit() and 7401 <= int(c) <= 7409: return "TERAPIA POSQUIRURGICA"
    return esp_html_clean

# --- SIDEBAR Y NAVEGACIÓN ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/b/b3/ISSSTE_logo.png", width=150)
    st.title("EpidemioManager")
    menu_opcion = st.radio("Módulos:", ["📋 Censo Diario", "📦 Censo de Insumos"])
    st.caption("CMN 20 de Noviembre")

# --- PROCESAMIENTO ---
st.header(menu_opcion)
archivo = st.file_uploader("📂 Cargar censo HTML", type=["html", "htm"])

if archivo:
    try:
        tablas = pd.read_html(archivo)
        df_completo = max(tablas, key=len)
        col0_str = df_completo.iloc[:, 0].fillna("").astype(str).str.upper()
        
        pacs_detectados = []
        esp_actual_temp = "SIN_ESPECIALIDAD"
        for i, val in enumerate(col0_str):
            if "ESPECIALIDAD:" in val:
                esp_actual_temp = val
                continue
            fila = [str(x).strip() for x in df_completo.iloc[i].values]
            if len(fila[1]) >= 5 and any(char.isdigit() for char in fila[1]):
                esp_real = obtener_especialidad_real(fila[0], esp_actual_temp)
                pacs_detectados.append({
                    "CAMA": fila[0], "REGISTRO": fila[1], "PACIENTE": fila[2], "SEXO": fila[3], 
                    "EDAD": "".join(re.findall(r'\d+', fila[4])), "DIAG": fila[6], 
                    "ING": fila[9], "esp_real": esp_real
                })

        if menu_opcion == "📦 Censo de Insumos":
            pacs_insumos = [p for p in pacs_detectados if p["esp_real"] in SERVICIOS_INSUMOS_FILTRO]
            servicios_en_insumos = sorted(list(set([p["esp_real"] for p in pacs_insumos])))

            if pacs_insumos:
                st.write(f"Pacientes para Insumos: **{len(pacs_insumos)}**")
                
                if st.button("🚀 GENERAR EXCEL DE INSUMOS", use_container_width=True, type="primary"):
                    fecha_captura, fecha_vencimiento = get_report_dates()
                    output = BytesIO()
                    
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        for serv in servicios_en_insumos:
                            pacs_serv = [p for p in pacs_insumos if p["esp_real"] == serv]
                            df_serv = pd.DataFrame(pacs_serv)
                            df_serv["TIPO DE PRECAUCIONES"] = df_serv["esp_real"].apply(lambda x: "ESTÁNDAR / PROTECTOR" if x == "ONCOLOGIA MEDICA" else "ESTÁNDAR")
                            df_serv["INSUMO"] = "JABÓN/SANITAS"
                            
                            cols_fin = ["CAMA", "REGISTRO", "PACIENTE", "SEXO", "EDAD", "ING", "TIPO DE PRECAUCIONES", "INSUMO"]
                            df_final = df_serv[cols_fin]
                            df_final.columns = ["CAMA", "REGISTRO", "PACIENTE", "SEXO", "EDAD", "FECHA DE INGRESO", "TIPO DE PRECAUCIONES", "INSUMO"]
                            
                            sheet_name = serv[:30].replace("/", "-")
                            df_final.to_excel(writer, index=False, sheet_name=sheet_name, startrow=1)
                            ws = writer.sheets[sheet_name]

                            # ENCABEZADO SUPERIOR CON FECHAS CORREGIDAS
                            header_text = f"{serv} DEL {fecha_captura} AL {fecha_vencimiento} (PARA LOS 3 TURNOS Y FINES DE SEMANA)"
                            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(cols_fin))
                            ws.cell(row=1, column=1, value=header_text).alignment = Alignment(horizontal="center", vertical="center")
                            ws.cell(row=1, column=1).font = Font(bold=True)

                            # PIE DE PÁGINA CON AJUSTE DE TEXTO (WRAP TEXT)
                            last_row = ws.max_row
                            ws.merge_cells(start_row=last_row + 1, start_column=1, end_row=last_row + 1, end_column=len(cols_fin))
                            cell_nom = ws.cell(row=last_row + 1, column=1, value="Comentario: de acuerdo con la Norma Oficial Mexicana NOM-045-SSA2-2005, Para la vigilancia epidemiológica, prevención y control de las infecciones nosocomiales. NINGUN RECIPIENTE QUE CONTENGA EL INSUMO DEVERÁ SER RELLENADO O REUTILIZADO.")
                            
                            # Configuración de ajuste de texto para que no se corte
                            cell_nom.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
                            cell_nom.font = Font(size=9, italic=True)
                            ws.row_dimensions[last_row + 1].height = 40 # Altura extra para el texto ajustado

                            # FIRMA AUTORIZÓ
                            ws.cell(row=last_row + 2, column=1, value="AUTORIZÓ: DRA. BRENDA CASTILLO MATUS").font = Font(bold=True)

                            # AUTO-AJUSTE DE COLUMNAS (Ignorando fila 1 para CAMA)
                            for i, col_name in enumerate(df_final.columns):
                                column_letter = get_column_letter(i + 1)
                                max_len = len(col_name)
                                for row in ws.iter_rows(min_row=2, max_row=last_row, min_col=i+1, max_col=i+1):
                                    for cell in row:
                                        cell.alignment = Alignment(horizontal="center", vertical="center")
                                        if cell.value: max_len = max(max_len, len(str(cell.value)))
                                ws.column_dimensions[column_letter].width = max_len + 3

                    st.download_button("💾 DESCARGAR REPORTE", data=output.getvalue(), file_name=f"Insumos_{fecha_captura.replace('/','-')}.xlsx", use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
