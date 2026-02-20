import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

SERVICIOS_INSUMOS_FILTRO = [
    "HEMATOLOGIA", "HEMATOLOGIA PEDIATRICA", "ONCOLOGIA PEDIATRICA",
    "NEONATOLOGIA", "INFECTOLOGIA PEDIATRICA", "U.C.I.N.",
    "U.T.I.P.", "TERAPIA POSQUIRURGICA", "UNIDAD DE QUEMADOS",
    "ONCOLOGIA MEDICA", "UCIA"
]

def obtener_especialidad_real(cama, esp_html):
    c = str(cama).strip().upper()
    if c.startswith("55"): return "U.C.I.N."
    if c.startswith("45"): return "NEONATOLOGIA" 
    if c.startswith("56"): return "U.T.I.P."
    if c.startswith("85"): return "UNIDAD DE QUEMADOS"
    if c.startswith("73"): return "UCIA"
    if c.isdigit() and 7401 <= int(c) <= 7409: return "TERAPIA POSQUIRURGICA"
    return esp_html.replace("ESPECIALIDAD:", "").replace("&NBSP;", "").strip().upper()

st.title("📦 Censo de Insumos")

if 'archivo_compartido' not in st.session_state:
    st.info("👈 Por favor, sube el censo en la barra lateral.")
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
            st.warning("No hay pacientes para insumos.")
        else:
            servicios_encontrados = sorted(list(set([p["esp_real"] for p in pacs_detectados])))
            for serv in servicios_encontrados:
                with st.expander(f"🔍 Vista Previa: {serv}"):
                    df_p = pd.DataFrame([p for p in pacs_detectados if p["esp_real"] == serv])
                    df_p["TIPO DE PRECAUCIONES"] = df_p["esp_real"].apply(lambda x: "ESTÁNDAR / PROTECTOR" if "ONCOLOGIA" in x or "QUEMADOS" in x else "ESTÁNDAR")
                    st.table(df_p[["CAMA", "REG", "PAC", "SEXO", "EDAD", "ING", "TIPO DE PRECAUCIONES"]])

            if st.button("🚀 GENERAR EXCEL DE INSUMOS", use_container_width=True, type="primary"):
                hoy = datetime.now(); venc = hoy + timedelta(days=7)
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    for serv in servicios_encontrados:
                        df_s = pd.DataFrame([p for p in pacs_detectados if p["esp_real"] == serv])
                        df_s["TIPO DE PRECAUCIONES"] = df_s["esp_real"].apply(lambda x: "ESTÁNDAR / PROTECTOR" if "ONCOLOGIA" in x or "QUEMADOS" in x else "ESTÁNDAR")
                        df_s["INSUMO"] = "JABÓN/SANITAS"
                        df_final = df_s[["CAMA", "REG", "PAC", "SEXO", "EDAD", "ING", "TIPO DE PRECAUCIONES", "INSUMO"]]
                        df_final.columns = ["CAMA", "REGISTRO", "PACIENTE", "SEXO", "EDAD", "FECHA DE INGRESO", "TIPO DE PRECAUCIONES", "INSUMO"]
                        
                        sheet_name = serv[:30].replace("/", "-")
                        df_final.to_excel(writer, index=False, sheet_name=sheet_name, startrow=1)
                        ws = writer.sheets[sheet_name]
                        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)
                        cell_h = ws.cell(row=1, column=1, value=f"{serv} DEL {hoy.strftime('%d/%m/%Y')} AL {venc.strftime('%d/%m/%Y')}")
                        cell_h.alignment = Alignment(horizontal="center"); cell_h.font = Font(bold=True)
                        
                        lr = ws.max_row
                        ws.merge_cells(start_row=lr + 1, start_column=1, end_row=lr + 1, end_column=8)
                        ws.cell(row=lr + 1, column=1, value="Comentario NOM-045...").font = Font(size=9, italic=True)
                        ws.cell(row=lr + 3, column=1, value="AUTORIZÓ: DRA. BRENDA CASTILLO MATUS").font = Font(bold=True)

                        for col in ws.columns:
                            L = get_column_letter(col[0].column)
                            ws.column_dimensions[L].width = 20
                st.download_button(label="💾 DESCARGAR INSUMOS", data=output.getvalue(), file_name=f"Insumos_{hoy.strftime('%d%m%Y')}.xlsx", use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")
