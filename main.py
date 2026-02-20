import streamlit as st

# --- CONFIGURACIÓN GLOBAL (Solo se define aquí) ---
st.set_page_config(page_title="EpidemioManager - CMN 20 de Noviembre", layout="wide")

# --- NAVEGACIÓN ---
# Aquí puedes ir agregando más páginas conforme crees más archivos en la carpeta modulos
pg = st.navigation([
    st.Page("modulos/censo_diario.py", title="Censo Epidemiológico", icon="📋"),
    # Ejemplo: st.Page("modulos/tesis_iaas.py", title="Modelo IAAS", icon="🔬"),
])

# Ejecutar la aplicación
pg.run()
