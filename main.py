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

# --- LÓGICA DE NEGOCIO ---
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

# --- INTERFAZ ---
st.title("🏥 EpidemioManager")
st.markdown("### Residencia de Epidemiología | CMN 20 de Noviembre")

archivo = st.file_uploader("Sube el archivo HTML del censo", type=["html", "htm"])

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
            
            if len(registro) >= 5 and any(char.isdigit() for char in registro):
                esp_real = obtener_especialidad_real(cama, esp_actual_temp)
                especialidades_encontradas.add(esp_real)
                pacs_detectados.append({
                    "CAMA": cama, "REGISTRO": registro, "PACIENTE": fila[2],
                    "SEXO": fila[3], "EDAD": "".join(re.findall(r'\d+', fila[4])),
                    "DIAGNOSTICO": fila[6], "FECHA_INGRESO": fila[9], "esp_real": esp_real
                })

        # --- CONTADORES (Visibles y claros) ---
        st.write("---")
        c1, c2 = st.columns(2)
        c1.info(f"**Pacientes totales detectados:** {len(pacs_detectados)}")
        c2.success(f"**Servicios identificados:** {len(especialidades_encontradas)}")
        st.write("---")

        # --- ORGANIZACIÓN DE SELECCIÓN ---
        buckets = {k: [] for k in ["COORD_TERAPIAS", "COORD_MEDICINA", "COORD_CIRUGIA", "COORD_MODULARES", "COORD_PEDIATRIA", "COORD_GINECOLOGIA", "OTRAS_ESPECIALIDADES"]}
        for e in sorted(especialidades_encontradas):
            cat = clasificar_especialidad(e)
            buckets[cat].append(e)

        st.markdown("#### Selecciona los servicios para el Excel")
        
        # Diccionario para guardar qué servicios se quedan seleccionados
        seleccion_final = []
        
        grid = st.columns(3)
        for idx, (cat_name, servicios) in enumerate(buckets.items()):
            if not servicios: continue
            
            with grid[idx % 3]:
                with st.container(border=True):
                    nombre_label = cat_name.replace("COORD_", "").replace("_", " ")
                    # Casilla MAESTRA
                    master_key = f"master_{cat_name}"
                    todo = st.checkbox(f"TODO {nombre_label}", key=master_key)
                    
                    # Casillas HIJAS
                    for s in servicios:
                        # Si 'todo' es True, forzamos la selección de la hija
                        if st.checkbox(s, value=todo, key=f"s_{s}"):
                            seleccion_final.append(s)

        st.write("---")

        # --- BOTÓN DE GENERACIÓN ---
        if st.button("📊 GENERAR ARCHIVO EXCEL", type="primary", use_container_width=True):
            # Aquí es donde validamos si hay algo seleccionado
            if not seleccion_final:
                st.error("⚠️ Error: No has seleccionado ningún servicio. Marca las casillas arriba.")
            else:
                fecha_hoy = datetime.now()
                datos_filtrados = []
                
                for p in pacs_detectados:
                    if p["esp_real"] in seleccion_final:
                        try:
                            f_ing = datetime.strptime(p["FECHA_INGRESO"], "%d/%m/%Y")
                            dias = (datetime(fecha_hoy.year, fecha_hoy.month, fecha_hoy.day) - 
                                    datetime(f_ing.year, f_ing.month, f_ing.day)).days + 1
                        except: dias = "N/D"

                        datos_filtrados.append({
                            "FECHA_REPORTE": fecha_hoy.strftime("%d/%m/%Y"),
                            "COORDINACION": clasificar_especialidad(p["esp_real"]),
                            "ESPECIALIDAD": p["esp_real"],
                            "CAMA": p["CAMA"], "REGISTRO": p["REGISTRO"],
                            "PACIENTE": p["PACIENTE"], "SEXO": p["SEXO"],
                            "EDAD": p["EDAD"], "DIAGNOSTICO": p["DIAGNOSTICO"],
                            "FECHA_INGRESO": p["FECHA_INGRESO"], "DIAS_ESTANCIA": dias
                        })

                if datos_filtrados:
                    df_out = pd.DataFrame(datos_filtrados)
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_out.to_excel(writer, index=False, sheet_name='Censo_Epidemio')
                    
                    # Ajustes finales al Excel
                    output.seek(0)
                    wb = load_workbook(output)
                    ws = wb.active
                    ws.add_table(Table(displayName="CensoTable", ref=ws.dimensions, 
                                       tableStyleInfo=TableStyleInfo(name="TableStyleMedium9", showRowStripes=True)))
                    for col in ws.columns:
                        ws.column_dimensions[get_column_letter(col[0].column)].width = 25
                    
                    final_io = BytesIO()
                    wb.save(final_io)
                    
                    st.balloons()
                    st.success(f"¡Listo! Se incluyeron {len(datos_filtrados)} pacientes en el reporte.")
                    st.download_button(
                        label="💾 DESCARGAR EXCEL AHORA",
                        data=final_io.getvalue(),
                        file_name=f"Censo_Epidemio_{fecha_hoy.strftime('%d%m%Y')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.warning("No se encontraron pacientes para los servicios seleccionados.")

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
