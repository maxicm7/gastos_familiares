import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Control Familiar", page_icon="💰", layout="centered")

st.title("💰 Finanzas Familiares")

# Conectar a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# El nombre de la pestaña abajo en tu Excel
NOMBRE_HOJA = "Hoja 1"

# Leer datos actuales
try:
    df = conn.read(worksheet=NOMBRE_HOJA, ttl=0) 
    df = df.dropna(how="all") # Limpiar filas vacías
except Exception as e:
    st.error("Error al leer el archivo. Verifica los secretos de Google.")
    st.stop()

# Si el Excel está vacío (como en tu foto), creamos las columnas internamente
columnas = ["Fecha", "Tipo", "Categoría", "Monto", "Descripción", "Persona"]
if df.empty or len(df.columns) == 0:
    df = pd.DataFrame(columns=columnas)

# Asegurar que el Monto sea numérico
df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0)

# Crear pestañas para la app
tab1, tab2, tab3 = st.tabs(["📝 Registrar", "📊 Resumen", "📋 Historial"])

# ----------------- PESTAÑA 1: REGISTRO -----------------
with tab1:
    st.subheader("Nuevo Movimiento")
    with st.form("registro_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", datetime.today())
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
        with col2:
            persona = st.selectbox("¿Quién?", ["Esposo", "Esposa", "Ambos"])
            monto = st.number_input("Monto ($)", min_value=0.0, step=100.0)
        
        categorias_gasto = ["Supermercado", "Tasa Municipal","ARCA", "ATM", "Cuota Colegio", "Combustible", "Seguros", "Merienda Colegio","Farmacia" , "Alquiler/Hipoteca", "Comida Fuera", "Entretenimiento", "Salud", "Ropa","Salario",  "Otros"]
        categorias_ingreso = ["Sueldo", "Bono", "Ventas", "Otros"]
        
        if tipo == "Gasto":
            categoria = st.selectbox("Categoría", categorias_gasto)
        else:
            categoria = st.selectbox("Categoría", categorias_ingreso)
            
        descripcion = st.text_input("Descripción (Opcional)")
        
        submit = st.form_submit_button("Guardar en la Nube ☁️", use_container_width=True)
        
        if submit:
            if monto <= 0:
                st.warning("El monto debe ser mayor a 0.")
            else:
                nuevo_dato = pd.DataFrame([{
                    "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Tipo": tipo,
                    "Categoría": categoria,
                    "Monto": monto,
                    "Descripción": descripcion,
                    "Persona": persona
                }])
                
                df_actualizado = pd.concat([df, nuevo_dato], ignore_index=True)
                conn.update(worksheet=NOMBRE_HOJA, data=df_actualizado)
                st.success("¡Guardado!")
                st.rerun()

# ----------------- PESTAÑA 2: GRÁFICOS -----------------
with tab2:
    st.subheader("Resumen Financiero")
    
    if not df.empty and df["Monto"].sum() > 0:
        total_ingresos = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
        total_gastos = df[df["Tipo"] == "Gasto"]["Monto"].sum()
        balance = total_ingresos - total_gastos
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Ingresos", f"${total_ingresos:,.2f}")
        col2.metric("Gastos", f"${total_gastos:,.2f}")
        col3.metric("Balance", f"${balance:,.2f}", delta=float(balance))
        
        st.divider()
        
        st.markdown("**Gastos por Categoría**")
        df_gastos = df[df["Tipo"] == "Gasto"]
        if not df_gastos.empty:
            gastos_cat = df_gastos.groupby("Categoría")["Monto"].sum().reset_index()
            fig_pie = px.pie(gastos_cat, values='Monto', names='Categoría', hole=0.4)
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
            
        st.markdown("**Gastos por Persona**")
        if not df_gastos.empty:
            gastos_pers = df_gastos.groupby("Persona")["Monto"].sum().reset_index()
            fig_bar = px.bar(gastos_pers, x='Persona', y='Monto', color='Persona')
            fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Agrega datos para ver los gráficos.")

# ----------------- PESTAÑA 3: HISTORIAL -----------------
with tab3:
    st.subheader("Últimos Movimientos")
    if not df.empty and len(df) > 0:
        st.dataframe(df.sort_values(by="Fecha", ascending=False).head(15), use_container_width=True)
        if st.button("Eliminar último registro"):
            df_actualizado = df[:-1]
            conn.update(worksheet=NOMBRE_HOJA, data=df_actualizado)
            st.success("Eliminado.")
            st.rerun()
    else:
        st.info("No hay movimientos.")
