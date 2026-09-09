import streamlit as st
import datetime
import holidays
from fpdf import FPDF

# ==========================================
# 1. MOTOR DE CÁLCULO
# ==========================================
def es_vacancia_judicial(fecha):
    if (fecha.month == 12 and fecha.day >= 20) or (fecha.month == 1 and fecha.day <= 10):
        return True
    return False

def es_dia_habil(fecha):
    festivos_colombia = holidays.CO(years=fecha.year)
    if fecha.weekday() >= 5 or fecha in festivos_colombia or es_vacancia_judicial(fecha):
        return False
    return True

def calcular_vencimiento(fecha_inicio, dias_plazo, tipo_conteo="habil"):
    fecha_actual = fecha_inicio
    dias_transcurridos = 0
    while dias_transcurridos < dias_plazo:
        fecha_actual += datetime.timedelta(days=1)
        if tipo_conteo == "habil":
            if es_dia_habil(fecha_actual):
                dias_transcurridos += 1
        elif tipo_conteo == "calendario":
            dias_transcurridos += 1
    return fecha_actual

# ==========================================
# 2. EXPORTACIÓN (PDF y CALENDARIO)
# ==========================================
def generar_ics(tramite, fecha_vencimiento, base_legal):
    fecha_str = fecha_vencimiento.strftime("%Y%m%d")
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Vencimiento: {tramite}
DTSTART;VALUE=DATE:{fecha_str}
DTEND;VALUE=DATE:{fecha_str}
DESCRIPTION:Vencimiento de términos procesales.\\nBase Legal: {base_legal}\\n\\nGenerado por Terralegal S.A.S.
END:VEVENT
END:VCALENDAR"""
    return ics_content

def generar_pdf(tramite, base_legal, dias, tipo_conteo, fecha_notif, fecha_venc, rango=False, fecha_max=None):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "REPORTE DE VENCIMIENTO DE TERMINOS", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("helvetica", "I", 10)
    pdf.cell(0, 10, "Generado por Terralegal S.A.S.", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, f"Actuacion Procesal: {tramite.encode('latin-1', 'replace').decode('latin-1')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Fundamento Juridico: {base_legal}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Fecha del Acto/Notificacion: {fecha_notif.strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")
    
    if rango:
        pdf.cell(0, 8, f"Termino Legal: Entre {dias} y {tipo_conteo}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, f"VENCIMIENTO MINIMO: {fecha_venc.strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 10, f"VENCIMIENTO MAXIMO: {fecha_max.strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 8, f"Termino Legal: {dias} dias {tipo_conteo}s", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, f"FECHA EXACTA DE VENCIMIENTO: {fecha_venc.strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")
    
    return bytes(pdf.output())

# ==========================================
# 3. DICCIONARIOS DE TÉRMINOS (ACTUALIZADOS Y COMPLETOS)
# ==========================================
terminos_ordinarios = {
    # --- RECURSOS ORDINARIOS Y EXTRAORDINARIOS ---
    "Apelación de Autos (Sustentación)": {"dias": 5, "tipo_conteo": "habil", "base_legal": "Art. 177 CPP", "duplicable": False},
    "Apelación de Sentencias (Sustentación)": {"dias": 5, "tipo_conteo": "habil", "base_legal": "Art. 179 CPP", "duplicable": False},
    "Presentación Demanda de Casación": {"dias": 30, "tipo_conteo": "habil", "base_legal": "Art. 183 CPP", "duplicable": False},
    
    # --- FASE DE INVESTIGACIÓN Y JUZGAMIENTO ---
    "Presentación Escrito Acusación": {"dias": 60, "tipo_conteo": "calendario", "base_legal": "Art. 175 CPP", "duplicable": True},
    "Fijación Audiencia de Acusación": {"dias": 3, "tipo_conteo": "habil", "base_legal": "Art. 338 CPP", "duplicable": False},
    "Fijación Audiencia Preparatoria": {"dias_min": 15, "dias_max": 30, "tipo_conteo": "habil", "base_legal": "Art. 343 CPP", "duplicable": False},
    "Fijación Inicio Juicio Oral": {"dias_min": 15, "dias_max": 30, "tipo_conteo": "habil", "base_legal": "Art. 365 CPP", "duplicable": False},
    "Emisión Sentencia (Desde sentido de fallo)": {"dias": 15, "tipo_conteo": "habil", "base_legal": "Art. 446 CPP", "duplicable": False},

    # --- INCIDENTE DE REPARACIÓN INTEGRAL (IRI) ---
    "Solicitud de Incidente (Desde firmeza sentencia)": {"dias": 30, "tipo_conteo": "habil", "base_legal": "Art. 106 CPP", "duplicable": False},
    "Audiencia de Reparación (Desde aceptación)": {"dias_min": 8, "dias_max": 15, "tipo_conteo": "habil", "base_legal": "Art. 103 CPP", "duplicable": False},

    # --- VENCIMIENTO DE TÉRMINOS (LIBERTAD - ART 317) ---
    "Libertad: Imputación a Acusación": {"dias": 60, "tipo_conteo": "calendario", "base_legal": "Art. 317 Num. 4 CPP", "duplicable": True},
    "Libertad: Acusación a Juicio Oral": {"dias": 120, "tipo_conteo": "calendario", "base_legal": "Art. 317 Num. 5 CPP", "duplicable": True},
    "Libertad: Juicio Oral a Sentencia": {"dias": 150, "tipo_conteo": "calendario", "base_legal": "Art. 317 Num. 6 CPP", "duplicable": True}
}

terminos_abreviados = {
    "Traslado del Escrito de Acusación": {"dias": 60, "tipo_conteo": "calendario", "base_legal": "Art. 536 CPP", "duplicable": True},
    "Fijación Audiencia Concentrada": {"dias": 10, "tipo_conteo": "habil", "base_legal": "Art. 543 CPP", "duplicable": False},
    "Fijación Inicio Juicio Oral": {"dias": 30, "tipo_conteo": "habil", "base_legal": "Art. 544 CPP", "duplicable": False},
    "Emisión de Sentencia": {"dias": 10, "tipo_conteo": "habil", "base_legal": "Art. 545 CPP", "duplicable": False},
    "Libertad: Traslado a Concentrada": {"dias": 60, "tipo_conteo": "calendario", "base_legal": "Art. 540 y 317", "duplicable": True},
    "Libertad: Concentrada a Juicio Oral": {"dias": 120, "tipo_conteo": "calendario", "base_legal": "Art. 540 y 317 Num. 5", "duplicable": True}
}

# ==========================================
# 4. INTERFAZ GRÁFICA (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Calculadora Penal", page_icon="⚖️", layout="centered")

st.title("⚖️ Calculadora de Términos Penales")
st.markdown("Cómputo automatizado de plazos procesales para litigio estratégico.")
st.divider()

regimen = st.radio("📜 Seleccione el Régimen Procesal:", 
                   ["Procedimiento Ordinario (Ley 906)", "Procedimiento Abreviado (Ley 1826)"], 
                   horizontal=True)

terminos_activos = terminos_ordinarios if "906" in regimen else terminos_abreviados

col1, col2 = st.columns(2)
with col1:
    fecha_notificacion = st.date_input("📅 Fecha del acto o notificación", datetime.date.today())
with col2:
    opcion_tramite = st.selectbox("📂 Seleccione la actuación procesal", list(terminos_activos.keys()))

st.divider()
es_especializada = st.checkbox("Activar: Justicia Especializada, GDO o Pluralidad de Imputados (Duplica términos)")
st.divider()

if st.button("Calcular Vencimiento", type="primary"):
    tramite = terminos_activos[opcion_tramite]
    
    # --- LÓGICA PARA PLAZOS FIJOS ---
    if "dias" in tramite:
        dias_calc = tramite["dias"] * 2 if (es_especializada and tramite["duplicable"]) else tramite["dias"]
        fecha_vencimiento = calcular_vencimiento(fecha_notificacion, dias_calc, tramite["tipo_conteo"])
        
        st.success("Cálculo realizado con éxito")
        st.metric(label="Fecha Exacta de Vencimiento", value=fecha_vencimiento.strftime('%d/%m/%Y'))
        st.write(f"**Término Aplicado:** {dias_calc} días {tramite['tipo_conteo']}s. | **Base Legal:** {tramite['base_legal']}")
        
        st.markdown("### 💾 Guardar Resultados")
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            pdf_bytes = generar_pdf(opcion_tramite, tramite['base_legal'], dias_calc, tramite['tipo_conteo'], fecha_notificacion, fecha_vencimiento)
            st.download_button(label="📄 Descargar en PDF", data=pdf_bytes, file_name=f"Vencimiento_{opcion_tramite}.pdf", mime="application/pdf")
        with b_col2:
            ics_str = generar_ics(opcion_tramite, fecha_vencimiento, tramite['base_legal'])
            st.download_button(label="📅 Agregar al Calendario", data=ics_str, file_name="vencimiento.ics", mime="text/calendar")

    # --- LÓGICA PARA RANGOS ---
    elif "dias_min" in tramite:
        fecha_min = calcular_vencimiento(fecha_notificacion, tramite["dias_min"], tramite["tipo_conteo"])
        fecha_max = calcular_vencimiento(fecha_notificacion, tramite["dias_max"], tramite["tipo_conteo"])
        
        st.success("Cálculo de rango realizado con éxito")
        c1, c2 = st.columns(2)
        c1.metric(label="Vencimiento Mínimo", value=fecha_min.strftime('%d/%m/%Y'))
        c2.metric(label="Vencimiento Máximo", value=fecha_max.strftime('%d/%m/%Y'))
        
        st.markdown("### 💾 Guardar Resultados")
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            texto_rango = f"{tramite['dias_min']} a {tramite['dias_max']} días {tramite['tipo_conteo']}s"
            pdf_bytes = generar_pdf(opcion_tramite, tramite['base_legal'], tramite['dias_min'], texto_rango, fecha_notificacion, fecha_min, rango=True, fecha_max=fecha_max)
            st.download_button(label="📄 Descargar en PDF", data=pdf_bytes, file_name="Vencimiento_Rango.pdf", mime="application/pdf")
        with b_col2:
            ics_str = generar_ics(opcion_tramite + " (Límite Máximo)", fecha_max, tramite['base_legal'])
            st.download_button(label="📅 Agregar al Calendario (Límite)", data=ics_str, file_name="vencimiento.ics", mime="text/calendar")