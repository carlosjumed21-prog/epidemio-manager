import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="EpidemioManager Web", layout="wide")

# Estilo para que se vea más profesional (similar a tu modo dark)
st.markdown("""
    <style>
    .main { background-color: #1a1a1a; color: white; }
    .stMetric { background-color: #262730; padding: 15px; border-radius: 10px; border: 1px solid #444; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES Y LÓGICA ORIGINAL ---
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
    if "TERAPIA INTENSIVA AD" in esp_html_clean: return "UCIA"
    if any(x in esp_html_clean for x in ["CARDIOLOGIA PEDIATRICA", "GASTROENTEROLOGIA PEDIATRICA", "NEUMOLOGIA PEDIATRICA", "MEDICINA INTERNA PEDIATRICA"]):
        return "MEDICINA INTERNA PEDIATRICA (5-4)"
    return esp_html_clean

# --- INTERFAZ ---
st.title("🛡️ EpidemioManager - Control UNAM")
st.markdown("---")

archivo = st.file_uploader("📂 Selecciona el archivo HTML del Censo Diario", type=["html", "htm"])

if archivo:
    try:
        tablas = pd.read_html(archivo)
        df_completo = max(tablas, key=len)
        col0_str = df_completo.iloc[:, 0].fillna("").astype(str).str.upper()
        
        # 1. ANALIZAR ESPECIALIDADES DISPONIBLES
        pacs_ini = 0
        lista_esp_detectadas = set()
        esp_actual_temp = "SIN_CLASIFICAR"
        IGNORAR = ["PACIENTES", "TOTAL", "SUBTOTAL", "PÁGINA", "IMPRESIÓN", "1111"]

        for i, val in enumerate(col0_str):
            if "ESPECIALIDAD:" in val:
                esp_actual_temp = val
                continue
            reg_val = str(df_completo.iloc[i, 1])
            if any(x in val for x in IGNORAR): continue
            if len(reg_val) >= 5 and any(char.isdigit() for char in reg_val):
                pacs_ini += 1
                esp_real = obtener_especialidad_real(val, esp_actual_temp)
                lista_esp_detectadas.add(esp_real)

        # Dashboard de Stats
        c1, c2 = st.columns(2)
        c1.metric("TOTAL PACIENTES", pacs_ini)
        c2.metric("ESPECIALIDADES DETECTADAS", len(lista_esp_detectadas))

        # 2. SELECCIÓN VISUAL (Buckets)
        st.subheader("Selección por Coordinación")
        buckets = {k: [] for k in ["COORD_TERAPIAS", "COORD_MEDICINA", "COORD_CIRUGIA", "COORD_GINECOLOGIA", "COORD_PEDIATRIA", "COORD_MODULARES", "OTRAS_ESPECIALIDADES"]}
        
        for e in sorted(lista_esp_detectadas):
            cat = clasificar_especialidad(e)
            buckets[cat].append(e)

        seleccion_final = []
        cols = st.columns(3)
        for idx, (cat_name, items) in enumerate(buckets.items()):
            if not items: continue
            with cols[idx % 3]:
                with st.expander(f"📦 {cat_name}", expanded=True):
                    todo = st.checkbox(f"Seleccionar todo {cat_name}", key=cat_name)
                    for it in items:
                        if st.checkbox(it, value=todo, key=it):
                            seleccion_final.append(it)

        # 3. PROCESAR EXCEL
        if st.button("🚀 Generar Excel para Coordinación", use_container_width=True):
            if not seleccion_final:
                st.warning("Selecciona al menos una especialidad.")
            else:
                datos = []
                fecha_reporte_obj = datetime.now()
                
                # RECORRIDO COMPLETO IGUAL AL ORIGINAL
                esp_actual_html = ""
                for _, row in df_completo.iterrows():
                    celda_0 = str(row.iloc[0]).strip().upper()
                    if "ESPECIALIDAD:" in celda_0:
                        esp_actual_html = celda_0
                        continue
                    
                    f = [str(x).strip() for x in row.values]
                    t = " ".join(f).upper()
                    if any(x in t for x in IGNORAR): continue
                    
                    cama, reg = f[0], f[1]
                    if "1111" in cama or "CAMA" in cama or len(reg) < 5: continue
                    
                    esp_real = obtener_especialidad_real(cama, esp_actual_html)
                    
                    if esp_real in seleccion_final:
                        # Cálculo de estancia
                        try:
                            fecha_ing_obj = datetime.strptime(f[9], "%d/%m/%Y")
                            dias = (datetime(fecha_reporte_obj.year, fecha_reporte_obj.month, fecha_reporte_obj.day) - 
                                    datetime(fecha_ing_obj.year, fecha_ing_obj.month, fecha_ing_obj.day)).days + 1
                        except: dias = "Rev. Fecha"

                        datos.append({
                            "FECHA_REPORTE": fecha_reporte_obj.strftime("%d/%m/%Y"),
                            "ESPECIALIDAD": esp_real,
                            "CAMA": cama, "REGISTRO": reg, "PACIENTE": f[2],
                            "SEXO": f[3], "EDAD": "".join(re.findall(r'\d+', f[4])),
                            "DIAGNOSTICO": f[6], "FECHA_INGRESO": f[9], "DIAS_ESTANCIA": dias
                        })

                # Crear el archivo Excel
                output = BytesIO()
                df_final = pd.DataFrame(datos)
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False, sheet_name='Censo')
                    
                # Formateo de tabla (Openpyxl)
                output.seek(0)
                wb = load_workbook(output)
                ws = wb.active
                if len(datos) > 0:
                    ws.add_table(Table(displayName="CensoTable", ref=ws.dimensions, 
                                       tableStyleInfo=TableStyleInfo(name="TableStyleMedium9", showRowStripes=True)))
                    for col in ws.columns:
                        ws.column_dimensions[get_column_letter(col[0].column)].width = 20
                
                final_output = BytesIO()
                wb.save(final_output)
                
                st.success("✅ Excel generado con éxito")
                st.download_button(
                    label="📥 Descargar Reporte Epidemiológico",
                    data=final_output.getvalue(),
                    file_name=f"Censo_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"Hubo un error procesando el archivo: {e}")
