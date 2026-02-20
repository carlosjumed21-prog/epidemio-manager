import streamlit as st

# --- CONFIGURACIÓN GLOBAL ---
st.set_page_config(
    page_title="EpidemioManager - CMN 20 de Noviembre", 
    page_icon="🏥",
    layout="wide"
)

# --- NAVEGACIÓN EN BARRA LATERAL ---
# Cada Page apunta a un archivo dentro de la carpeta 'modulos'
pg = st.navigation([
    st.Page("modulos/censo_diario.py", title="Censo Epidemiológico", icon="📋"),
    st.Page("modulos/insumos.py", title="Censo de Insumos", icon="📦"),
])

# Ejecución
pg.run()
