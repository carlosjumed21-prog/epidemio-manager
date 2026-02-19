import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="EpidemioManager - CMN 20 de Noviembre", layout="wide")

# --- LÓGICA DE NEGOCIO (REGLAS DE CARLOS) ---
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
    if c.startswith("56"): return "U.T.I.P."
    if c.startswith("85"): return "UNIDAD DE QUEMADOS"
    if c.startswith("73"): return "UCIA"
    if c.isdigit():
        val = int(c)
        if 7401 <= val <= 7409: return "TERAPIA POSQUIRURGICA"
    return esp_html_clean

# --- SINCRONIZACIÓN DE CASILLAS ---
def sync_group(cat_name, servicios):
    master_val = st.session_state[f"master_{cat_name}"]
    for s in servicios:
        st.session_state[f"serv_{cat_name}_{s}"] = master_val

# --- INTERFAZ ---
st.title("🏥 EpidemioManager - ISSSTE")
st.caption("Residencia de Epidemiología - CMN 20 de Noviembre")

archivo = st.file_uploader("Sube el reporte HTML del censo", type=["html", "htm"])

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
                    "CAMA": fila[0], "REG": fila[1], "PAC": fila[2], "SEXO": fila[3], 
                    "EDAD": "".join(re.findall(r'\d+', fila[4])), "DIAG": fila[6], 
                    "ING": fila[9], "esp_real": esp_real
                })

        st.write("---")
        st.subheader(f"📊 Pacientes Detectados: {len(pacs_detectados)}")
        st.write("---")

        # --- ORGANIZACIÓN DE SELECCIÓN ---
        buckets = {"⚠️ UNIDADES DE TERAPIA ⚠️": [e for e in especialidades_encontradas if e in MAPA_TERAPIAS]}
        for cat, items in CATALOGO.items():
            found = [e for e in especialidades_encontradas if any(kw in e for kw in items) and e not in MAPA_TERAPIAS]
            if found: buckets[cat] = found

        cols = st.columns(3)
        for idx, (cat_name, servicios) in enumerate(buckets.items()):
            with cols[idx % 3]:
                header_style = "background-color:#C0392B; padding:5px; border-radius:5px; color:white;" if "TERAPIA" in cat_name else "color:inherit;"
                st.markdown(f'<div style="{header_style}"><b>{cat_name.replace("COORD_", "")}</b></div>', unsafe_allow_html=True)
                with st.container(border=True):
                    st.checkbox(f"Seleccionar todo", key=f"master_{cat_name}", on_change=sync_group, args=(cat_name, servicios))
                    for s in servicios:
                        st.checkbox(s, key=f"serv_{cat_name}_{s}")

        st.write("---")

        # --- GENERACIÓN DE EXCEL CON FORMATO ---
        if st.button("🚀 GENERAR Y DESCARGAR EXCEL", use_container_width=True, type="primary"):
            seleccionados = []
            for c_name, servs in buckets.items():
                for s in servs:
                    if st.session_state.get(f"serv_{c_name}_{s}"):
                        seleccionados.append(s)

            if not seleccionados:
                st.warning("⚠️ Selecciona al menos un servicio.")
            else:
                fecha_hoy = datetime.now()
                datos_finales = []
                for p in pacs_detectados:
                    if p["esp_real"] in seleccionados:
                        # Cálculo de estancia
                        try:
                            f_ing = datetime.strptime(p["ING"], "%d/%m/%Y")
                            dias = (datetime(fecha_hoy.year, fecha_hoy.month, fecha_hoy.day) - 
                                    datetime(f_ing.year, f_ing.month, f_ing.day)).days + 1
                        except: dias = "Rev. Fecha"

                        datos_finales.append({
                            "FECHA_REPORTE": fecha_hoy.strftime("%d/%m/%Y"),
                            "ESPECIALIDAD": p["esp_real"],
                            "CAMA": p["CAMA"], "REGISTRO": p["REG"],
                            "PACIENTE": p["PAC"], "SEXO": p["SEXO"],
                            "EDAD": p["EDAD"], "DIAGNOSTICO": p["DIAG"],
                            "FECHA_INGRESO": p["ING"], "DIAS_ESTANCIA": dias
                        })

                if datos_finales:
                    df_out = pd.DataFrame(datos_finales)
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_out.to_excel(writer, index=False, sheet_name='Censo_Epidemio')
                    
                    # --- APLICAR FORMATO DE TABLA Y ANCHO DE COLUMNAS ---
                    output.seek(0)
                    wb = load_workbook(output)
                    ws = wb.active
                    
                    # Añadir Tabla Estilizada
                    ws.add_table(Table(displayName="CensoTable", ref=ws.dimensions, 
                                       tableStyleInfo=TableStyleInfo(name="TableStyleMedium9", showRowStripes=True)))
                    
                    # Ajustar ancho de columnas automáticamente
                    for col in ws.columns:
                        max_length = 0
                        column = col[0].column_letter
                        for cell in col:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except: pass
                        ws.column_dimensions[column].width = max_length + 4

                    final_io = BytesIO()
                    wb.save(final_io)
                    
                    st.success(f"✅ Excel generado con {len(datos_finales)} pacientes.")
                    st.download_button(
                        label="💾 GUARDAR ARCHIVO EXCEL",
                        data=final_io.getvalue(),
                        file_name=f"Censo_Epidemio_{fecha_hoy.strftime('%d%m%Y')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.error("No hay pacientes para esta selección.")

    except Exception as e:
        st.error(f"Error crítico: {e}")
