import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Configuración de la página (Adaptado para celular)
st.set_page_config(page_title="Control Familiar", page_icon="💰", layout="centered")

st.title("💰 Finanzas Familiares")

# Conectar a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Nombre de la pestaña en tu Google Sheet
NOMBRE_HOJA = "Gastos_Familiares"

# Leer datos actuales
try:
    # ttl=0 para no usar caché y ver cambios en vivo
    df = conn.read(worksheet=NOMBRE_HOJA, ttl=0) 
    df = df.dropna(how="all") # Limpiar filas vacías
except Exception as e:
    st.error(f"Error al leer el archivo. Verifica que la pestaña de abajo en tu Google Sheet se llame exactamente '{NOMBRE_HOJA}' y que las credenciales estén bien.")
    st.stop()

# Si el dataframe está vacío o le faltan columnas, creamos la estructura
columnas_esperadas = ["Fecha", "Tipo", "Categoría", "Monto", "Descripción", "Persona"]
if df.empty or len(df.columns) == 0:
    df = pd.DataFrame(columns=columnas_esperadas)

# Asegurar que el Monto sea numérico
df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0)

# Crear pestañas para la UI móvil
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
        
        # Categorías dinámicas según si es ingreso o gasto
        categorias_gasto = ["Supermercado", "Servicios", "Alquiler/Hipoteca", "Transporte", "Comida Fuera", "Entretenimiento", "Salud", "Ropa", "Otros"]
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
                # Crear nuevo registro
                nuevo_dato = pd.DataFrame([{
                    "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Tipo": tipo,
                    "Categoría": categoria,
                    "Monto": monto,
                    "Descripción": descripcion,
                    "Persona": persona
                }])
                
                # Unir y guardar
                df_actualizado = pd.concat([df, nuevo_dato], ignore_index=True)
                conn.update(worksheet=NOMBRE_HOJA, data=df_actualizado)
                st.success("¡Movimiento guardado exitosamente!")
                st.rerun() # Recargar la página para actualizar gráficos

# ----------------- PESTAÑA 2: GRÁFICOS -----------------
with tab2:
    st.subheader("Resumen Financiero")
    
    if not df.empty and df["Monto"].sum() > 0:
        # Calcular totales
        total_ingresos = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
        total_gastos = df[df["Tipo"] == "Gasto"]["Monto"].sum()
        balance = total_ingresos - total_gastos
        
        # Tarjetas de métricas
        col1, col2, col3 = st.columns(3)
        col1.metric("Ingresos", f"${total_ingresos:,.2f}")
        col2.metric("Gastos", f"${total_gastos:,.2f}")
        col3.metric("Balance", f"${balance:,.2f}", delta=float(balance))
        
        st.divider()
        
        # Gráfico de Torta: Gastos por Categoría
        st.markdown("**Gastos por Categoría**")
        df_gastos = df[df["Tipo"] == "Gasto"]
        if not df_gastos.empty:
            gastos_cat = df_gastos.groupby("Categoría")["Monto"].sum().reset_index()
            fig_pie = px.pie(gastos_cat, values='Monto', names='Categoría', hole=0.4)
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0)) # Ajustar para móvil
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No hay gastos registrados aún.")
            
        # Gráfico de Barras: Quién gasta qué
        st.markdown("**Gastos por Persona**")
        if not df_gastos.empty:
            gastos_pers = df_gastos.groupby("Persona")["Monto"].sum().reset_index()
            fig_bar = px.bar(gastos_pers, x='Persona', y='Monto', color='Persona')
            fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.info("Agrega datos en la pestaña de Registro para ver los gráficos.")

# ----------------- PESTAÑA 3: HISTORIAL -----------------
with tab3:
    st.subheader("Últimos Movimientos")
    if not df.empty and len(df) > 0:
        # Mostrar los últimos 15 registros, ordenados del más nuevo al más viejo
        st.dataframe(df.sort_values(by="Fecha", ascending=False).head(15), use_container_width=True)
        
        # Botón para borrar el último registro por si se equivocan
        if st.button("Eliminar último registro (Deshacer)"):
            df_actualizado = df[:-1] # Quita la última fila
            conn.update(worksheet=NOMBRE_HOJA, data=df_actualizado)
            st.success("Último registro eliminado.")
            st.rerun()
    else:
        st.info("La base de datos está vacía.")
