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

# --- FUNCIÓN DE SINCRONIZACIÓN CORREGIDA ---
def sync_group(cat_name, servicios):
    """Marca o desmarca todos los servicios de una coordinación específica"""
    master_key = f"master_{cat_name}"
    master_val = st.session_state[master_key]
    for s in servicios:
        # La llave única ahora incluye el nombre de la coordinación
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
        col_m1, col_m2 = st.columns(2)
        with col_m1: st.subheader(f"📊 Pacientes: {len(pacs_detectados)}")
        with col_m2: st.subheader(f"🧪 Servicios: {len(especialidades_encontradas)}")
        st.write("---")

        # --- BUCKETS DE COORDINACIÓN ---
        buckets = {"⚠️ UNIDADES DE TERAPIA ⚠️": [e for e in especialidades_encontradas if e in MAPA_TERAPIAS]}
        for cat, items in CATALOGO.items():
            found = [e for e in especialidades_encontradas if any(kw in e for kw in items) and e not in MAPA_TERAPIAS]
            if found: buckets[cat] = found

        st.markdown("### 🛠️ Configuración del Reporte")
        
        cols = st.columns(3)
        for idx, (cat_name, servicios) in enumerate(buckets.items()):
            with cols[idx % 3]:
                # Estilo visual para Terapias
                header_style = "background-color:#C0392B; padding:5px; border-radius:5px; color:white;" if "TERAPIA" in cat_name else "color:inherit;"
                st.markdown(f'<div style="{header_style}"><b>{cat_name.replace("COORD_", "")}</b></div>', unsafe_allow_html=True)
                
                with st.container(border=True):
                    # Casilla MAESTRA con CALLBACK para forzar la selección
                    st.checkbox(f"Seleccionar todo", 
                                key=f"master_{cat_name}", 
                                on_change=sync_group, 
                                args=(cat_name, servicios))
                    
                    for s in servicios:
                        # La llave única serv_{cat_name}_{s} evita el error de duplicados
                        st.checkbox(s, key=f"serv_{cat_name}_{s}")

        st.write("---")

        # --- GENERAR EXCEL ---
        if st.button("📥 Generar y Descargar Excel", use_container_width=True, type="primary"):
            # Recolectar de session_state buscando en todos los buckets
            seleccionados_final = []
            for c_name, servs in buckets.items():
                for s in servs:
                    if st.session_state.get(f"serv_{c_name}_{s}"):
                        seleccionados_final.append(s)

            if not seleccionados_final:
                st.warning("⚠️ Debes seleccionar al menos un servicio arriba.")
            else:
                fecha_hoy = datetime.now()
                datos_finales = [p for p in pacs_detectados if p["esp_real"] in seleccionados_final]
                
                if datos_finales:
                    df_out = pd.DataFrame(datos_finales)
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_out.to_excel(writer, index=False, sheet_name='Epidemiologia')
                    
                    st.success(f"✅ Se han procesado {len(datos_finales)} pacientes correctamente.")
                    st.download_button(
                        label="💾 Guardar Archivo Excel",
                        data=output.getvalue(),
                        file_name=f"Censo_Epidemio_{fecha_hoy.strftime('%d%m%Y')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error("No se encontraron pacientes para la selección realizada.")

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
