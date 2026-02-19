import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="EpidemioManager - ISSSTE", layout="wide")

# Eliminamos el CSS oscuro personalizado para evitar los "recuadros negros" 
# y que use el tema nativo de Streamlit (que es muy limpio).

# --- LÓGICA DE NEGOCIO ---
MAPA_TERAPIAS = {
    "UNIDAD CORONARIA": "COORD_MODULARES", "U.C.I.N.": "COORD_PEDIATRIA",
    "U.T.I.P.": "COORD_PEDIATRIA", "TERAPIA POSQUIRURGICA": "COORD_MEDICINA",
    "UNIDAD DE QUEMADOS": "COORD_CIRUGIA", "UCIA": "COORD_MEDICINA"
}

CATALOGO = {
    "COORD_MEDICINA": ["DERMATO", "ENDOCRINO", "GERIAT", "INMUNO", "MEDICINA INTERNA", "PSIQ", "REUMA", "UCIA", "TERAPIA INTERMEDIA", "CLINICA DEL DOLOR", "TPQX", "TERAPIA POSQUIRURGICA", "POSQUIRURGICA"],
    "COORD_CIRUGIA": ["CIRUGIA GENERAL", "CIR. GENERAL", "MAXILO", "RECONSTRUCTIVA", "PLASTICA", "GASTRO", "NEFROLOGIA", "OFTALMO", "ORTOPEDIA", "ORTOPEDIA", "OTORRINO", "UROLOGIA", "TRASPLANTES", "QUEMADOS", "UNIDAD DE QUEMADOS"],
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

# --- INTERFAZ ---
st.title("🏥 EpidemioManager - ISSSTE")
st.info("Carga el archivo HTML para comenzar el análisis.")

archivo = st.file_uploader("Subir Censo", type=["html", "htm"])

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
            cama, registro = fila[0], fila[1]
            
            if any(x in cama for x in IGNORAR): continue
            
            # Validación de paciente
            if len(registro) >= 5 and any(char.isdigit() for char in registro):
                esp_real = obtener_especialidad_real(cama, esp_actual_temp)
                especialidades_encontradas.add(esp_real)
                pacs_detectados.append({
                    "cama": cama, "registro": registro, "paciente": fila[2],
                    "sexo": fila[3], "edad": "".join(re.findall(r'\d+', fila[4])),
                    "diag": fila[6], "ingreso": fila[9], "esp_real": esp_real
                })

        # --- MÉTRICAS (Sin CSS para que se vean bien) ---
        st.write("---")
        m1, m2 = st.columns(2)
        m1.metric(label="Pacientes Detectados", value=len(pacs_detectados))
        m2.metric(label="Especialidades en el Censo", value=len(especialidades_encontradas))
        st.write("---")

        # --- BUCKETS ---
        buckets = {k: [] for k in ["COORD_TERAPIAS", "COORD_MEDICINA", "COORD_CIRUGIA", "COORD_MODULARES", "COORD_PEDIATRIA", "COORD_GINECOLOGIA", "OTRAS_ESPECIALIDADES"]}
        for e in sorted(especialidades_encontradas):
            cat = clasificar_especialidad(e)
            buckets[cat].append(e)

        st.markdown("### 📂 Selección por Coordinación")
        
        # Guardaremos la selección en una lista
        seleccion_final = []
        
        cols = st.columns(3)
        for idx, (cat_name, lista_servicios) in enumerate(buckets.items()):
            if not lista_servicios: continue
            
            with cols[idx % 3]:
                st.markdown(f"**{cat_name}**")
                # El truco para el "Seleccionar todo":
                # Si este checkbox es True, los hijos heredan el valor
                todo = st.checkbox(f"Toda la {cat_name.split('_')[-1]}", key=f"all_{cat_name}")
                
                for s in lista_servicios:
                    # El valor del checkbox individual depende de 'todo'
                    if st.checkbox(s, value=todo, key=f"chk_{s}"):
                        seleccion_final.append(s)
        
        st.write("---")
        
        if st.button("🚀 Generar Excel Epidemiológico", use_container_width=True):
            if not seleccion_final:
                st.error("⚠️ No has seleccionado ningún servicio.")
            else:
                # Filtrar pacientes seleccionados
                datos_excel = [p for p in pacs_detectados if p["esp_real"] in seleccion_final]
                
                if datos_excel:
                    df_final = pd.DataFrame(datos_excel)
                    # Renombrar columnas para el Excel
                    df_final.columns = ["CAMA", "REGISTRO", "PACIENTE", "SEXO", "EDAD", "DIAGNOSTICO", "FECHA_INGRESO", "ESPECIALIDAD"]
                    
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_final.to_excel(writer, index=False)
                    
                    st.success(f"¡Éxito! Se procesaron {len(datos_excel)} pacientes.")
                    st.download_button(
                        label="⬇️ Descargar Excel",
                        data=output.getvalue(),
                        file_name=f"Censo_{datetime.now().strftime('%d%m%Y')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("No hay datos que coincidan con la selección.")

    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
