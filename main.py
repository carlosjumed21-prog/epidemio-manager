import streamlit as st

# --- CONFIGURACIÓN GLOBAL ---
st.set_page_config(
    page_title="EpidemioManager - CMN 20 de Noviembre", 
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CARGADOR GLOBAL EN BARRA LATERAL ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/2/25/Logo_ISSSTE.svg", width=120)
st.sidebar.title("⚙️ Configuración")

# Cargador único de archivo
archivo_subido = st.sidebar.file_uploader("Subir Censo HTML", type=["html", "htm"])

# Almacenar el archivo en el estado de la sesión
if archivo_subido:
    st.session_state['archivo_compartido'] = archivo_subido
    st.sidebar.success("✅ Censo cargado")
else:
    st.sidebar.info("👋 Sube el censo aquí para usar las herramientas.")

# --- NAVEGACIÓN ---
pg = st.navigation([
    st.Page("modulos/censo_diario.py", title="Censo Epidemiológico", icon="📋"),
    st.Page("modulos/insumos.py", title="Censo de Insumos", icon="📦"),
])

pg.run()
