import streamlit as st

# 1. Configuración de página
st.set_page_config(
    page_title="EpidemioManager - CMN 20 de Noviembre",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded" # Esto obliga a que la barra lateral aparezca abierta
)

# 2. Cargador de archivos en la barra lateral
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/2/25/Logo_ISSSTE.svg", width=150)
st.sidebar.title("📁 Carga de Censo")
archivo = st.sidebar.file_uploader("Sube el HTML del censo aquí", type=["html", "htm"])

# Guardar en el estado de la sesión para que los módulos lo usen
if archivo:
    st.session_state['archivo_compartido'] = archivo
    st.sidebar.success("✅ Archivo cargado correctamente")
else:
    st.sidebar.warning("⚠️ Esperando archivo HTML...")

# 3. Definición de la Navegación
pg = st.navigation([
    st.Page("modulos/censo_diario.py", title="Censo Epidemiológico", icon="📋"),
    st.Page("modulos/insumos.py", title="Censo de Insumos", icon="📦"),
])

pg.run()
