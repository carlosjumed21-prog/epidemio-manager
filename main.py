import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime, timedelta
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="EpidemioManager - CMN 20 de Noviembre", layout="wide")

# --- REGLAS DE NEGOCIO ---
SERVICIOS_INSUMOS_FILTRO = [
    "ONCOLOGÍA PEDIATRICA", "NEONATOLOGIA", "INFECTOTOLOGIA PEDIATRICA", 
    "U.C.I.N.", "U.T.I.P.", "TERAPIA POSQUIRURGICA", 
    "UNIDAD DE QUEMADOS", "ONCOLOGIA MEDICA", "UCIA"
]

ORDEN_TERAPIAS_EXCEL = ["UNIDAD CORONARIA", "UCIA", "TERAPIA POSQUIRURGICA", "U.C.I.N.", "U.T.I.P.", "UNIDAD DE QUEMADOS"]

MAPA_TERAPIAS = {
    "UNIDAD CORONARIA": "COORD_MODULARES", "U.C.I.N.": "COORD_PEDIATRIA",
    "U.T.I.P.": "COORD_PEDIATRIA", "TERAPIA POSQUIRURGICA": "COORD_MEDICINA",
    "UNIDAD DE QUEMADOS": "COORD_CIRUGIA", "UCIA": "COORD_MEDICINA"
}

VINCULO_AUTO_INCLUSION = {
    "COORD_MEDICINA": ["UCIA", "TERAPIA POSQUIRURGICA"],
    "COORD_CIRUGIA": ["UNIDAD DE QUEMADOS"],
    "COORD_MODULARES": ["UNIDAD CORONARIA"],
    "COORD_PEDIATRIA": ["U.C.I.N.", "U.T.I.P."]
}

COLORES_INTERFAZ = {
    "⚠️ UNIDADES DE TERAPIA ⚠️": "#C0392B", "COORD_PEDIATRIA": "#5DADE2",
    "COORD_MEDICINA": "#1B4F72", "COORD_GINECOLOGIA": "#F06292",
    "COORD_MODULARES": "#E67E22", "OTRAS_ESPECIALIDADES": "#2C3E50", "COORD_CIRUGIA": "#117864"
}

CATALOGO = {
    "COORD_MEDICINA": ["DERMATO", "ENDOCRINO", "GERIAT", "INMUNO", "MEDICINA INTERNA", "REUMA", "UCIA", "TERAPIA INTERMEDIA", "CLINICA DEL DOLOR", "TPQX", "TERAPIA POSQUIRURGICA", "POSQUIRURGICA"],
    "COORD_CIRUGIA": ["CIRUGIA GENERAL", "CIR. GENERAL", "MAXILO", "RECONSTRUCTIVA", "PLASTICA", "GASTRO", "NEFROLOGIA", "OFTALMO", "ORTOPEDIA", "OTORRINO", "UROLOGIA", "TRASPLANTES", "QUEMADOS", "UNIDAD DE QUEMADOS"],
    "COORD_MODULARES": ["ANGIOLOGIA", "VASCULAR", "CARDIOLOGIA", "CARDIOVASCULAR", "TORAX", "NEUMO", "HEMATO", "NEUROCIRUGIA", "NEUROLOGIA", "ONCOLOGIA", "CORONARIA", "UNIDAD CORONARIA", "PSIQ", "PSIQUIATRIA"],
    "COORD_PEDIATRIA": ["PEDIATRI", "PEDIATRICA", "NEONATO", "NEONATOLOGIA", "CUNERO", "UTIP", "U.T.I.P", "UCIN", "U.C.I.N"],
    "COORD_GINECOLOGIA": ["GINECO", "OBSTETRICIA", "MATERNO", "REPRODUCCION", "BIOLOGIA DE LA REPRO"]
}

# --- FUNCIONES ---
def get_monday_dates():
    hoy = datetime.now()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    lunes_siguiente = lunes_actual + timedelta(days=7)
    return lunes_actual.strftime("%d/%m/%Y"), lunes_siguiente.strftime("%d/%m/%Y")

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

def sync_group(cat_name, servicios):
    master_val = st.session_state[f"master_{cat_name}"]
    for s in servicios:
        st.session_state[f"serv_{cat_name}_{s}"] = master_val

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/b/b3/ISSSTE_logo.png", width=150)
    st.title("EpidemioManager")
    st.write("---")
    menu_opcion = st.radio("Módulos:", ["📋 Censo Diario", "📦 Censo de Insumos"], index=0)
    st.write("---")
    st.caption("CMN 20 de Noviembre")

# --- CARGA GLOBAL ---
st.header(menu_opcion)
archivo = st.file_uploader("📂 Cargar archivo HTML del censo", type=["html", "htm"])

if archivo:
    try:
        tablas = pd.read_html(archivo)
        df_completo = max(tablas, key=len)
        col0_str = df_completo.iloc[:, 0].fillna("").astype(str).str.upper()
        pacs_detectados = []
        especialidades_encontradas = set()
        IGNORAR = ["PACIENTES", "TOTAL", "SUBTOTAL", "PÁGINA", "IMPRESIÓN", "1111"]
        
        esp_actual_temp = "SIN_ESPECIALIDAD"
        for i, val in enumerate(col0_str):
            if "ESPECIALIDAD:" in val:
                esp_actual_temp = val
                continue
            fila = [str(x).strip() for x in df_completo.iloc[i].values]
            if any(x in fila[0] for x in IGNORAR): continue
            if len(fila[1]) >= 5 and any(char.isdigit() for char in fila[1]):
                esp_real = obtener_especialidad_real(fila[0], esp_actual_temp)
                especialidades_encontradas.add(esp_real)
                pacs_detectados.append({
                    "CAMA": fila[0], "REGISTRO": fila[1], "PACIENTE": fila[2], "SEXO": fila[3], 
                    "EDAD": "".join(re.findall(r'\d+', fila[4])), "DIAGNOSTICO": fila[6], 
                    "FECHA DE INGRESO": fila[9], "esp_real": esp_real
                })

        # --- MÓDULO 1: CENSO DIARIO ---
        if menu_opcion == "📋 Censo Diario":
            st.subheader(f"📊 Pacientes Detectados: {len(pacs_detectados)}")
            buckets = {}
            asignadas = set()
            terapias_list = sorted([e for e in especialidades_encontradas if e in MAPA_TERAPIAS])
            if terapias_list:
                buckets["⚠️ UNIDADES DE TERAPIA ⚠️"] = terapias_list
                asignadas.update(terapias_list)
            
            ped_list = sorted([e for e in especialidades_encontradas if e not in asignadas and ("PEDIATRI" in e or "PEDIATRICA" in e or "NEONATO" in e or "NEONATOLOGIA" in e)])
            if ped_list:
                buckets["COORD_PEDIATRIA"] = ped_list
                asignadas.update(ped_list)

            for cat, kws in CATALOGO.items():
                if cat == "COORD_PEDIATRIA": continue
                found = sorted([e for e in especialidades_encontradas if e not in asignadas and any(kw in e for kw in kws)])
                if found:
                    buckets[cat] = found
                    asignadas.update(found)
            
            cols = st.columns(3)
            for idx, (cat_name, servicios) in enumerate(buckets.items()):
                with cols[idx % 3]:
                    color = COLORES_INTERFAZ.get(cat_name, "#5D6D7E")
                    st.markdown(f'<div style="background-color:{color}; padding:8px; border-radius:5px 5px 0px 0px; color:white; text-align:center;"><b>{cat_name.replace("COORD_", "")}</b></div>', unsafe_allow_html=True)
                    with st.container(border=True):
                        st.checkbox(f"Seleccionar todo", key=f"master_{cat_name}", on_change=sync_group, args=(cat_name, servicios))
                        for s in servicios:
                            st.checkbox(s, key=f"serv_{cat_name}_{s}")

            if st.button("🚀 GENERAR EXCEL GENERAL", use_container_width=True, type="primary"):
                especialidades_finales = set()
                for c_name, servs in buckets.items():
                    if st.session_state.get(f"master_{c_name}"):
                        if c_name in VINCULO_AUTO_INCLUSION:
                            for t in VINCULO_AUTO_INCLUSION[c_name]:
                                if t in especialidades_encontradas: especialidades_finales.add(t)
                    for s in servs:
                        if st.session_state.get(f"serv_{c_name}_{s}"): especialidades_finales.add(s)

                if especialidades_finales:
                    fecha_hoy = datetime.now()
                    datos_excel = []
                    for p in pacs_detectados:
                        if p["esp_real"] in especialidades_finales:
                            datos_excel.append({"FECHA_REPORTE": fecha_hoy.strftime("%d/%m/%Y"), "ESPECIALIDAD": p["esp_real"], "CAMA": p["CAMA"], "REGISTRO": p["REGISTRO"], "PACIENTE": p["PACIENTE"], "SEXO": p["SEXO"], "EDAD": p["EDAD"], "DIAGNOSTICO": p["DIAGNOSTICO"], "FECHA_INGRESO": p["FECHA DE INGRESO"]})

                    df_out = pd.DataFrame(datos_excel)
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_out.to_excel(writer, index=False)
                    st.download_button(label="💾 DESCARGAR EXCEL", data=output.getvalue(), file_name=f"Censo_Gral_{fecha_hoy.strftime('%d%m%Y')}.xlsx", use_container_width=True)

        # --- MÓDULO 2: CENSO DE INSUMOS ---
        elif menu_opcion == "📦 Censo de Insumos":
            pacs_insumos = [p for p in pacs_detectados if p["esp_real"] in SERVICIOS_INSUMOS_FILTRO]
            servicios_en_insumos = sorted(list(set([p["esp_real"] for p in pacs_insumos])))

            if not pacs_insumos:
                st.warning("⚠️ No se detectaron pacientes en los servicios críticos para insumos.")
            else:
                for serv in servicios_en_insumos:
                    with st.expander(f"🔍 Previsualización: {serv}", expanded=False):
                        df_preview = pd.DataFrame([p for p in pacs_insumos if p["esp_real"] == serv])
                        df_preview["TIPO DE PRECAUCIONES"] = df_preview["esp_real"].apply(lambda x: "ESTÁNDAR / PROTECTOR" if x == "ONCOLOGIA MEDICA" else "ESTÁNDAR")
                        df_preview["INSUMO"] = "JABÓN/SANITAS"
                        st.table(df_preview[["CAMA", "REGISTRO", "PACIENTE", "SEXO", "EDAD", "FECHA DE INGRESO", "TIPO DE PRECAUCIONES", "INSUMO"]])

                if st.button("🚀 GENERAR EXCEL DE INSUMOS (NOM-045)", use_container_width=True, type="primary"):
                    lunes_ini, lunes_fin = get_monday_dates()
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        for serv in servicios_en_insumos:
                            pacs_serv = [p for p in pacs_insumos if p["esp_real"] == serv]
                            df_serv = pd.DataFrame(pacs_serv)
                            df_serv["TIPO DE PRECAUCIONES"] = df_serv["esp_real"].apply(lambda x: "ESTÁNDAR / PROTECTOR" if x == "ONCOLOGIA MEDICA" else "ESTÁNDAR")
                            df_serv["INSUMO"] = "JABÓN/SANITAS"
                            
                            cols_finales = ["CAMA", "REGISTRO", "PACIENTE", "SEXO", "EDAD", "FECHA DE INGRESO", "TIPO DE PRECAUCIONES", "INSUMO"]
                            df_final = df_serv[cols_finales]
                            
                            sheet_name = serv[:30].replace("/", "-")
                            df_final.to_excel(writer, index=False, sheet_name=sheet_name, startrow=1)
                            ws = writer.sheets[sheet_name]
                            
                            # TÍTULO SUPERIOR
                            header_text = f"{serv} VIGENCIA DEL {lunes_ini} AL {lunes_fin} (PARA LOS 3 TURNOS Y FINES DE SEMANA)"
                            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(cols_finales))
                            cell_h = ws.cell(row=1, column=1, value=header_text)
                            cell_h.alignment = Alignment(horizontal="center", vertical="center")
                            cell_h.font = Font(bold=True, size=11)

                            # PIES DE PÁGINA
                            last_data_row = ws.max_row
                            ws.merge_cells(start_row=last_data_row + 1, start_column=1, end_row=last_data_row + 1, end_column=len(cols_finales))
                            cell_f1 = ws.cell(row=last_data_row + 1, column=1, value="Comentario: de acuerdo con la Norma Oficial Mexicana NOM-045-SSA2-2005, Para la vigilancia epidemiológica, prevención y control de las infecciones nosocomiales. NINGUN RECIPIENTE QUE CONTENGA EL INSUMO DEVERÁ SER RELLENADO O REUTILIZADO.")
                            cell_f1.alignment = Alignment(horizontal="center", vertical="center")
                            cell_f1.font = Font(size=9, italic=True)
                            ws.cell(row=last_data_row + 2, column=1, value="AUTORIZÓ: DRA. BRENDA CASTILLO MATUS")
                            ws.cell(row=last_data_row + 2, column=1).font = Font(bold=True)
                            
                            # AUTO-AJUSTE Y CENTRADO ESTRICTO
                            for i, col_name in enumerate(cols_finales):
                                column_letter = get_column_letter(i + 1)
                                max_length = len(col_name)
                                # Solo revisamos desde la fila 2 para ignorar el encabezado combinado de la fila 1
                                for row in ws.iter_rows(min_row=2, max_row=last_data_row, min_col=i+1, max_col=i+1):
                                    for cell in row:
                                        cell.alignment = Alignment(horizontal="center", vertical="center")
                                        if cell.value:
                                            max_length = max(max_length, len(str(cell.value)))
                                ws.column_dimensions[column_letter].width = max_length + 3

                    st.success("✅ Censo de Insumos generado.")
                    st.download_button("💾 DESCARGAR REPORTE", data=output.getvalue(), file_name=f"Insumos_{datetime.now().strftime('%d%m%Y')}.xlsx", use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
