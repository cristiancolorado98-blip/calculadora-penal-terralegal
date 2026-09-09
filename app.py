import streamlit as st
import datetime
from dateutil.relativedelta import relativedelta
import holidays
from fpdf import FPDF
from supabase import create_client, Client

# ==========================================
# 0. CONEXIÓN A LA BASE DE DATOS (SUPABASE)
# ==========================================
@st.cache_resource
def iniciar_conexion():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = iniciar_conexion()

# ==========================================
# 1. MOTOR DE CÁLCULO Y FECHAS
# ==========================================
@st.cache_data
def obtener_festivos(anio):
    """Guarda los festivos en memoria para no recalcularlos y evitar que la app se ponga lenta"""
    return holidays.CO(years=anio)

def es_vacancia_judicial(fecha):
    if (fecha.month == 12 and fecha.day >= 20) or (fecha.month == 1 and fecha.day <= 10):
        return True
    return False

def es_dia_habil(fecha):
    if fecha.weekday() >= 5 or es_vacancia_judicial(fecha):
        return False
    festivos_colombia = obtener_festivos(fecha.year)
    if fecha in festivos_colombia:
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

# NUEVO: Traductor de fechas a español
def formatear_fecha_es(fecha):
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{dias[fecha.weekday()]}, {fecha.day} de {meses[fecha.month - 1]} de {fecha.year}"

# NUEVO: Calculadora de días hábiles restantes (Para el semáforo)
def calcular_dias_habiles_restantes(fecha_vencimiento):
    hoy = datetime.date.today()
    if fecha_vencimiento < hoy:
        return -1 # Ya venció
    dias = 0
    fecha_actual = hoy
    while fecha_actual < fecha_vencimiento:
        fecha_actual += datetime.timedelta(days=1)
        if es_dia_habil(fecha_actual):
            dias += 1
    return dias

# NUEVO: Función visual del semáforo para la plataforma
def mostrar_semaforo(fecha_vencimiento):
    dias = calcular_dias_habiles_restantes(fecha_vencimiento)
    if dias < 0:
        st.error(f"🚨 **¡TÉRMINO VENCIDO!** La fecha límite ya pasó.")
    elif dias <= 10:
        st.error(f"🔴 **SEMÁFORO ROJO:** Urgente, quedan solo **{dias} días hábiles**.")
    elif dias <= 30:
        st.warning(f"🟡 **SEMÁFORO AMARILLO:** Atención, quedan **{dias} días hábiles**.")
    else:
        st.success(f"🟢 **SEMÁFORO VERDE:** Aún quedan **{dias} días hábiles**.")

# ==========================================
# 2. EXPORTACIÓN (PDF y CALENDARIO)
# ==========================================
def generar_ics(tramite, fecha_vencimiento, base_legal):
    fecha_str = fecha_vencimiento.strftime("%Y%m%d")
    ics_content = f"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:Vencimiento: {tramite}\nDTSTART;VALUE=DATE:{fecha_str}\nDTEND;VALUE=DATE:{fecha_str}\nDESCRIPTION:Vencimiento procesal.\\nBase Legal: {base_legal}\\n\\nGenerado por Terralegal S.A.S.\nEND:VEVENT\nEND:VCALENDAR"
    return ics_content

def generar_pdf(tramite, base_legal, dias, tipo_conteo, fecha_notif, fecha_venc, rango=False, fecha_max=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "REPORTE DE VENCIMIENTO DE TERMINOS", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("helvetica", "I", 10)
    pdf.cell(0, 10, "Generado por Terralegal S.A.S.", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    hoy = datetime.date.today()
    dias_restantes = calcular_dias_habiles_restantes(fecha_venc)
    
    pdf.set_font("helvetica", "", 12)
    # Agregamos la fecha de consulta
    pdf.cell(0, 8, f"Fecha de consulta: {formatear_fecha_es(hoy)}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Actuacion Procesal: {tramite.encode('latin-1', 'replace').decode('latin-1')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Fundamento Juridico: {base_legal}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Fecha del Acto/Notificacion: {formatear_fecha_es(fecha_notif)}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    if rango:
        pdf.cell(0, 8, f"Termino Legal: Entre {dias} y {tipo_conteo}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, f"VENCIMIENTO MINIMO: {formatear_fecha_es(fecha_venc)}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 10, f"VENCIMIENTO MAXIMO: {formatear_fecha_es(fecha_max)}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 8, f"Termino Legal: {dias} dias {tipo_conteo}s", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, f"FECHA EXACTA: {formatear_fecha_es(fecha_venc)}", new_x="LMARGIN", new_y="NEXT")

    # SEMAFORO EN PDF CON COLORES
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 12)
    if dias_restantes < 0:
        pdf.set_text_color(255, 0, 0) # Rojo
        pdf.cell(0, 10, "ESTADO: TERMINO VENCIDO", new_x="LMARGIN", new_y="NEXT")
    elif dias_restantes <= 10:
        pdf.set_text_color(255, 0, 0) # Rojo
        pdf.cell(0, 10, f"SEMAFORO ROJO: Urgente, quedan {dias_restantes} dias habiles", new_x="LMARGIN", new_y="NEXT")
    elif dias_restantes <= 30:
        pdf.set_text_color(255, 140, 0) # Naranja oscuro
        pdf.cell(0, 10, f"SEMAFORO AMARILLO: Quedan {dias_restantes} dias habiles", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_text_color(0, 128, 0) # Verde
        pdf.cell(0, 10, f"SEMAFORO VERDE: Quedan {dias_restantes} dias habiles", new_x="LMARGIN", new_y="NEXT")
        
    pdf.set_text_color(0, 0, 0) # Restaurar color negro
    return bytes(pdf.output())

# ==========================================
# 3. DICCIONARIOS DE TÉRMINOS
# ==========================================
terminos_ordinarios = {
    "Apelación de Autos (Sustentación)": {"dias": 5, "tipo_conteo": "habil", "base_legal": "Art. 177 CPP", "duplicable": False},
    "Apelación de Sentencias (Sustentación)": {"dias": 5, "tipo_conteo": "habil", "base_legal": "Art. 179 CPP", "duplicable": False},
    "Presentación Demanda de Casación": {"dias": 30, "tipo_conteo": "habil", "base_legal": "Art. 183 CPP", "duplicable": False},
    "Presentación Escrito Acusación": {"dias": 60, "tipo_conteo": "calendario", "base_legal": "Art. 175 CPP", "duplicable": True},
    "Fijación Audiencia de Acusación": {"dias": 3, "tipo_conteo": "habil", "base_legal": "Art. 338 CPP", "duplicable": False},
    "Fijación Audiencia Preparatoria": {"dias_min": 15, "dias_max": 30, "tipo_conteo": "habil", "base_legal": "Art. 343 CPP", "duplicable": False},
    "Fijación Inicio Juicio Oral": {"dias_min": 15, "dias_max": 30, "tipo_conteo": "habil", "base_legal": "Art. 365 CPP", "duplicable": False},
    "Emisión Sentencia (Desde sentido de fallo)": {"dias": 15, "tipo_conteo": "habil", "base_legal": "Art. 446 CPP", "duplicable": False},
    "Solicitud de Incidente de Reparación": {"dias": 30, "tipo_conteo": "habil", "base_legal": "Art. 106 CPP", "duplicable": False},
    "Audiencia de Reparación (Desde aceptación)": {"dias_min": 8, "dias_max": 15, "tipo_conteo": "habil", "base_legal": "Art. 103 CPP", "duplicable": False},
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
# 4. INTERFAZ GRÁFICA (FRONTEND COMPLETO)
# ==========================================
st.set_page_config(page_title="Plataforma LegalTech - Terralegal", page_icon="logo.png", layout="wide")

ocultar_elementos_streamlit = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {
                padding-top: 2rem;
                padding-bottom: 8rem;
            }
            </style>
            """
st.markdown(ocultar_elementos_streamlit, unsafe_allow_html=True)

st.image("logo.png", width=300) 
st.title("Gestor Procesal Automático")
st.markdown("Plataforma avanzada para el control de términos y prescripción de la acción penal.")
st.divider()

tab1, tab2, tab3 = st.tabs([
    "📅 Cómputo de Términos (Ley 906/1826)", 
    "⏳ Cálculo de Prescripción (Ley 599)", 
    "📂 Gestor de Casos"
])

# --- PESTAÑA 1: CÓMPUTO DE TÉRMINOS ---
with tab1:
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
    
    if st.button("Calcular Vencimiento", type="primary", key="btn_terminos"):
        tramite = terminos_activos[opcion_tramite]
        if "dias" in tramite:
            dias_calc = tramite["dias"] * 2 if (es_especializada and tramite["duplicable"]) else tramite["dias"]
            fecha_vencimiento = calcular_vencimiento(fecha_notificacion, dias_calc, tramite["tipo_conteo"])
            
            st.success("Cálculo realizado con éxito")
            st.metric(label="Fecha Exacta de Vencimiento", value=formatear_fecha_es(fecha_vencimiento))
            st.write(f"**Término Aplicado:** {dias_calc} días {tramite['tipo_conteo']}s. | **Base Legal:** {tramite['base_legal']}")
            mostrar_semaforo(fecha_vencimiento)
            
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                pdf_bytes = generar_pdf(opcion_tramite, tramite['base_legal'], dias_calc, tramite['tipo_conteo'], fecha_notificacion, fecha_vencimiento)
                st.download_button(label="📄 Descargar en PDF", data=pdf_bytes, file_name=f"Vencimiento_{opcion_tramite}.pdf", mime="application/pdf")
            with b_col2:
                ics_str = generar_ics(opcion_tramite, fecha_vencimiento, tramite['base_legal'])
                st.download_button(label="📅 Agregar al Calendario", data=ics_str, file_name="vencimiento.ics", mime="text/calendar")

        elif "dias_min" in tramite:
            fecha_min = calcular_vencimiento(fecha_notificacion, tramite["dias_min"], tramite["tipo_conteo"])
            fecha_max = calcular_vencimiento(fecha_notificacion, tramite["dias_max"], tramite["tipo_conteo"])
            
            st.success("Cálculo de rango realizado con éxito")
            c1, c2 = st.columns(2)
            c1.metric(label="Vencimiento Mínimo", value=formatear_fecha_es(fecha_min))
            c2.metric(label="Vencimiento Máximo", value=formatear_fecha_es(fecha_max))
            mostrar_semaforo(fecha_min)
            
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                texto_rango = f"{tramite['dias_min']} a {tramite['dias_max']} días {tramite['tipo_conteo']}s"
                pdf_bytes = generar_pdf(opcion_tramite, tramite['base_legal'], tramite['dias_min'], texto_rango, fecha_notificacion, fecha_min, rango=True, fecha_max=fecha_max)
                st.download_button(label="📄 Descargar en PDF", data=pdf_bytes, file_name="Vencimiento_Rango.pdf", mime="application/pdf")
            with b_col2:
                ics_str = generar_ics(opcion_tramite + " (Límite Máximo)", fecha_max, tramite['base_legal'])
                st.download_button(label="📅 Agregar al Calendario (Límite)", data=ics_str, file_name="vencimiento.ics", mime="text/calendar")

# --- PESTAÑA 2: CÁLCULO DE PRESCRIPCIÓN ---
with tab2:
    st.markdown("### Algoritmo de Prescripción de la Acción Penal")
    st.info("💡 Este módulo calcula los tiempos de caducidad aplicando las reglas de los artículos 83 y 86 del Código Penal.")
    
    catalogo_delitos = {
        "Homicidio simple (Art. 103)": 450,
        "Homicidio agravado (Art. 104)": 600,
        "Feminicidio simple (Art. 104A)": 500,
        "Feminicidio agravado (Art. 104B)": 600,
        "Lesiones personales (Ej. Incapacidad > 90 días)": 120,
        "Acceso carnal violento (Art. 205)": 360,
        "Actos sexuales con menor de 14 años (Art. 209)": 156,
        "Hurto simple (Art. 239)": 108,
        "Hurto calificado (Art. 240)": 168,
        "Hurto agravado (Art. 241)": 180,
        "Estafa (Art. 246)": 144,
        "Abuso de confianza (Art. 249)": 54,
        "Extorsión (Art. 244)": 288,
        "Violencia intrafamiliar (Art. 229)": 96,
        "Inasistencia alimentaria (Art. 233)": 54,
        "Falsedad ideológica en doc. público (Art. 286)": 144,
        "Falsedad material en doc. público (Art. 287)": 108,
        "Falsedad en documento privado (Art. 289)": 108,
        "Concierto para delinquir simple (Art. 340)": 108,
        "Concierto para delinquir agravado (Art. 340 inc. 2)": 216,
        "Porte ilegal de armas de fuego (Art. 365)": 144,
        "Tráfico, fab. o porte de estupefacientes (Art. 376)": 360,
        "Peculado por apropiación (Art. 397)": 270,
        "Concusión (Art. 404)": 180,
        "Cohecho propio (Art. 405)": 180,
        "Celebración indebida de contratos (Art. 410)": 216,
        "Prevaricato por acción (Art. 413)": 144,
        "Lavado de activos (Art. 323)": 360,
        "Secuestro extorsivo (Art. 169)": 504,
        "OTRO (Ingreso manual / Concurso de delitos)": 0
    }
    
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        fecha_hechos = st.date_input("📅 Fecha de consumación de los hechos", datetime.date.today())
        delito_seleccionado = st.selectbox("⚖️ Seleccione el Delito", list(catalogo_delitos.keys()))
        
        if delito_seleccionado == "OTRO (Ingreso manual / Concurso de delitos)":
            pena_max_meses = st.number_input("Ingrese la pena máxima en meses", min_value=1, value=108, step=1)
        else:
            pena_max_meses = catalogo_delitos[delito_seleccionado]
            st.success(f"**Pena máxima aplicada automáticamente:** {pena_max_meses} meses.")
            
    with c_p2:
        hubo_imputacion = st.checkbox("¿Se formuló imputación? (Interrupción del término - Art. 86)")
        fecha_imputacion = None
        if hubo_imputacion:
            fecha_imputacion = st.date_input("📅 Fecha de Formulación de Imputación", datetime.date.today())
            
        es_servidor_publico = st.checkbox("El sujeto activo es Servidor Público (Aumenta el término prescriptivo)")
        
    if st.button("Ejecutar Algoritmo de Prescripción", type="primary", key="btn_presc"):
        pena_anios = pena_max_meses / 12.0
        termino_base_anios = max(5.0, min(20.0, pena_anios))
        
        if es_servidor_publico:
            termino_base_anios = termino_base_anios * 1.5 
            
        anios_base = int(termino_base_anios)
        meses_base = int(round((termino_base_anios - anios_base) * 12))
        
        fecha_presc_inicial = fecha_hechos + relativedelta(years=anios_base, months=meses_base)
        
        if not hubo_imputacion:
            st.warning("⚠️ **Fase de Indagación:** El término no ha sido interrumpido.")
            st.write(f"**Término aplicable (Art. 83 CP):** {termino_base_anios:.2f} años.")
            st.metric(label="Fecha Exacta de Prescripción", value=formatear_fecha_es(fecha_presc_inicial))
            mostrar_semaforo(fecha_presc_inicial)
        else:
            termino_interrumpido_anios = termino_base_anios / 2.0
            termino_final_anios = max(3.0, min(10.0, termino_interrumpido_anios))
            
            anios_final = int(termino_final_anios)
            meses_final = int(round((termino_final_anios - anios_final) * 12))
            
            fecha_presc_final = fecha_imputacion + relativedelta(years=anios_final, months=meses_final)
            
            st.error("🛑 **Fase de Investigación/Juicio:** Término interrumpido por imputación.")
            st.write(f"**Nuevo término reducido (Art. 86 CP):** {termino_final_anios:.2f} años (Contados desde la imputación).")
            st.metric(label="Fecha Exacta de Prescripción", value=formatear_fecha_es(fecha_presc_final))
            mostrar_semaforo(fecha_presc_final)

# --- PESTAÑA 3: GESTOR DE CASOS CON BASE DE DATOS ---
with tab3:
    st.markdown("### 🗄️ Archivo Digital de Expedientes")
    st.info("Guarda los resultados directamente en la base de datos cifrada de Terralegal.")
    
    with st.form("formulario_nuevo_caso", clear_on_submit=True):
        col_form1, col_form2 = st.columns(2)
        
        with col_form1:
            radicado_input = st.text_input("Número de Radicado (21 dígitos)")
            delito_input = st.text_input("Delito Investigado")
            
        with col_form2:
            actuacion_input = st.text_input("Actuación Procesal Pendiente")
            fecha_venc_input = st.date_input("Fecha de Vencimiento Estimada")
            abogado_email = st.text_input("Correo del Abogado a Cargo", value="camilo@terralegal.com") 
            
        boton_guardar = st.form_submit_button("💾 Guardar Caso en la Nube")
        
        if boton_guardar:
            if radicado_input and delito_input:
                try:
                    datos_caso = {
                        "usuario_email": abogado_email,
                        "radicado": radicado_input,
                        "delito": delito_input,
                        "actuacion_pendiente": actuacion_input,
                        "fecha_vencimiento": fecha_venc_input.isoformat()
                    }
                    
                    respuesta = supabase.table("casos_penales").insert(datos_caso).execute()
                    
                    st.success(f"¡Caso {radicado_input} guardado exitosamente en la base de datos!")
                except Exception as e:
                    st.error(f"Hubo un error al guardar: {e}")
            else:
                st.warning("⚠️ Debes llenar al menos el radicado y el delito.")