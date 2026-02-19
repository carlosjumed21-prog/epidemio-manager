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

# Lógica de colores y estilos
st.markdown("""
    <style>
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE NEGOCIO (TU CÓDIGO ORIGINAL) ---
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
st.title("🏥 EpidemioManager - ISSSTE")
st.subheader("Control Epidemiológico CMN 20 de Noviembre")

archivo = st.file_uploader("Sube el archivo HTML del Censo", type=["html", "htm"])

if archivo:
    try:
        tablas = pd.read_html(archivo)
        df_completo = max(tablas, key=len)
        col0_str = df_completo.iloc[:, 0].fillna("").astype(str).str.upper()
        
        # --- ANÁLISIS PROFUNDO DE DATOS ---
        pacs_detectados = []
        especialidades_encontradas = set()
        IGNORAR = ["PACIENTES", "TOTAL", "SUBTOTAL", "PÁGINA", "IMPRESIÓN", "1111"]
        
        esp_actual_temp = "SIN_ESPECIALIDAD"
        for i, val in enumerate(col0_str):
            if "ESPECIALIDAD:" in val:
                esp_actual_temp = val
                continue
            
            fila = [str(x).strip() for x in df_completo.iloc[i].values]
            cama, registro = fila[0], fila[1]
            
            if any(x in cama for x in IGNORAR): continue
            
            # Validación de paciente real (tu regla de oro)
            if len(registro) >= 5 and any(char.isdigit() for char in registro):
                esp_real = obtener_especialidad_real(cama, esp_actual_temp)
                especialidades_encontradas.add(esp_real)
                
                # Guardamos los datos temporalmente
                pacs_detectados.append({
                    "cama": cama, "registro": registro, "paciente": fila[2],
                    "sexo": fila[3], "edad": "".join(re.findall(r'\d+', fila[4])),
                    "diag": fila[6], "ingreso": fila[9], "esp_real": esp_real
                })

        # --- MÉTRICAS ---
        m1, m2 = st.columns(2)
        m1.metric("Pacientes en Censo", len(pacs_detectados))
        m2.metric("Servicios Detectados", len(especialidades_encontradas))

        # --- ORGANIZACIÓN DE MENÚS (BUCKETS) ---
        buckets = {k: [] for k in ["COORD_TERAPIAS", "COORD_MEDICINA", "COORD_CIRUGIA", "COORD_MODULARES", "COORD_PEDIATRIA", "COORD_GINECOLOGIA", "OTRAS_ESPECIALIDADES"]}
        
        for e in sorted(especialidades_encontradas):
            cat = clasificar_especialidad(e)
            buckets[cat].append(e)

        st.markdown("### Selecciona las áreas para el reporte")
        
        # Generar columnas para las coordinaciones
        seleccion_usuario = []
        cols = st.columns(3)
        
        # Iteramos sobre todas las coordinaciones, incluso si están vacías no las mostramos
        for idx, (cat_name, lista_servicios) in enumerate(buckets.items()):
            if not lista_servicios: continue
            
            with cols[idx % 3]:
                with st.expander(f"📁 {cat_name.replace('_', ' ')}", expanded=True):
                    todo = st.checkbox(f"Toda la {cat_name}", key=f"all_{cat_name}")
                    for s in lista_servicios:
                        if st.checkbox(s, value=todo, key=f"chk_{s}"):
                            seleccion_usuario.append(s)

        # --- GENERACIÓN DE EXCEL ---
        if st.button("📥 Generar Excel Seleccionado", use_container_width=True):
            if not seleccion_usuario:
                st.error("Por favor selecciona al menos un servicio.")
            else:
                fecha_hoy = datetime.now()
                datos_finales = []
                
                for p in pacs_detectados:
                    if p["esp_real"] in seleccion_usuario:
                        # Cálculo de estancia
                        try:
                            f_ing = datetime.strptime(p["ingreso"], "%d/%m/%Y")
                            dias = (datetime(fecha_hoy.year, fecha_hoy.month, fecha_hoy.day) - 
                                    datetime(f_ing.year, f_ing.month, f_ing.day)).days + 1
                        except: dias = "Revisar"

                        datos_finales.append({
                            "FECHA_REPORTE": fecha_hoy.strftime("%d/%m/%Y"),
                            "ESPECIALIDAD": p["esp_real"],
                            "CAMA": p["cama"], "REGISTRO": p["registro"],
                            "PACIENTE": p["paciente"], "SEXO": p["sexo"],
                            "EDAD": p["edad"], "DIAGNOSTICO": p["diag"],
                            "FECHA_INGRESO": p["ingreso"], "DIAS_ESTANCIA": dias
                        })

                if datos_finales:
                    df_out = pd.DataFrame(datos_finales)
                    output = BytesIO()
                    
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_out.to_excel(writer, index=False, sheet_name='Epidemiologia')
                        
                    # Formato Excel
                    output.seek(0)
                    wb = load_workbook(output)
                    ws = wb.active
                    ws.add_table(Table(displayName="CensoTable", ref=ws.dimensions, 
                                       tableStyleInfo=TableStyleInfo(name="TableStyleMedium9", showRowStripes=True)))
                    
                    for col in ws.columns:
                        ws.column_dimensions[get_column_letter(col[0].column)].width = 22
                    
                    final_io = BytesIO()
                    wb.save(final_io)
                    
                    st.success(f"Reporte listo con {len(datos_finales)} pacientes.")
                    st.download_button(
                        "Descargar Archivo Excel",
                        data=final_io.getvalue(),
                        file_name=f"Censo_Epidemio_{fecha_hoy.strftime('%d%m%Y')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("No hay datos para la selección actual.")

    except Exception as e:
        st.error(f"Error crítico: {e}")
