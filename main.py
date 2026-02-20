import streamlit as st

# --- CONFIGURACIÓN GLOBAL ---
st.set_page_config(
    page_title="EpidemioManager - CMN 20 de Noviembre", 
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- BARRA LATERAL (ORDEN SUPERIOR) ---
st.sidebar.header("⚙️ Configuración")

# 1. El cargador de archivos ahora es lo primero que aparece
archivo_subido = st.sidebar.file_uploader(
    "Subir Censo HTML", 
    type=["html", "htm"],
    help="Arrastra aquí el archivo generado por el sistema del hospital."
)

# Guardar en memoria compartida
if archivo_subido:
    st.session_state['archivo_compartido'] = archivo_subido
    st.sidebar.success("✅ Censo cargado")
else:
    st.sidebar.info("👋 Por favor, sube un censo.")

# 2. Línea divisoria para separar la carga de la navegación
st.sidebar.divider()

# 3. Definición de las Pestañas (Aparecerán debajo del cargador)
pg = st.navigation([
    st.Page("modulos/censo_diario.py", title="Censo Epidemiológico", icon="📋"),
    st.Page("modulos/insumos.py", title="Censo de Insumos", icon="📦"),
])

pg.run()
