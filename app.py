import streamlit as st
import pandas as pd
import db
import email_service
import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Gestor de Proyectos", layout="wide")

# 1. Inicialización de tareas en segundo plano (Ya no se llama a db.init_db())
@st.cache_resource
def init_background_tasks():
    return email_service.iniciar_scheduler()

init_background_tasks()

# 2. Gestión de Sesión (Login)
if 'usuario_id' not in st.session_state:
    st.session_state['usuario_id'] = None
    st.session_state['usuario_nombre'] = None

def logout():
    st.session_state['usuario_id'] = None
    st.session_state['usuario_nombre'] = None
    st.rerun()

# Pantalla de Login
if st.session_state['usuario_id'] is None:
    st.title("Acceso al Kanban")
    with st.form("login_form"):
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Ingresar")
        
        if submitted:
            usuario = db.verificar_login(email, password)
            if usuario:
                st.session_state['usuario_id'] = usuario[0]
                st.session_state['usuario_nombre'] = usuario[1]
                st.success("Acceso concedido")
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

# Pantalla Principal (Solo si está logueado)
else:
    st.sidebar.write(f"👤 Conectado como: **{st.session_state['usuario_nombre']}**")
    st.sidebar.button("Cerrar Sesión", on_click=logout)

    tab_kanban, tab_dashboard, tab_equipo = st.tabs(["📋 Tablero Kanban", "📊 Dashboard", "👥 Equipo"])

    with tab_kanban:
        # Auto-recarga cada 10 segundos para ver cambios de otros usuarios en tiempo real
        st_autorefresh(interval=10000, key="kanban_refresh")
        
        st.header("Tablero de Proyecto")
        TABLERO_ID = 1 
        
        with st.expander("➕ Añadir Nueva Tarea"):
            with st.form("form_nueva_tarea"):
                col1, col2 = st.columns(2)
                titulo = col1.text_input("Título de la tarea")
                desc = col1.text_area("Descripción")
                fecha = col2.date_input("Fecha límite")
                prioridad = col2.selectbox("Prioridad", ["Alta", "Media", "Baja"])
                
                usuarios_df = pd.read_sql("SELECT * FROM Usuarios", db.get_conn())
                usuarios_dict = dict(zip(usuarios_df['nombre'], usuarios_df['id']))
                responsable = col2.selectbox("Responsable", options=list(usuarios_dict.keys()))
                
                if st.form_submit_button("Crear Tarea") and titulo:
                    db.add_tarea(TABLERO_ID, 1, titulo, desc, fecha.strftime('%Y-%m-%d'), prioridad, usuarios_dict[responsable])
                    st.success("Tarea creada.")
                    st.rerun()

        st.divider()

        columnas_df = db.get_columnas(TABLERO_ID)
        tareas_df = db.get_tareas(TABLERO_ID)
        cols_ui = st.columns(len(columnas_df))
        
        for idx, col_data in columnas_df.iterrows():
            col_id = col_data['id']
            col_nombre = col_data['nombre']
            
            with cols_ui[idx]:
                st.subheader(col_nombre)
                tareas_columna = tareas_df[tareas_df['columna_id'] == col_id]
                
                for _, tarea in tareas_columna.iterrows():
                    with st.container():
                        color_prio = {"Alta": "🔴", "Media": "🟡", "Baja": "🟢"}.get(tarea['prioridad'], "⚪")
                        st.markdown(f"""
                        <div style="border: 1px solid #ddd; border-radius: 8px; padding: 10px; margin-bottom: 10px; background-color: #f9f9f9; color: black;">
                            <h4>{tarea['titulo']}</h4>
                            <p style="font-size: 14px;">{tarea['descripcion']}</p>
                            <small><b>Prioridad:</b> {color_prio} {tarea['prioridad']} | <b>Vence:</b> {tarea['fecha_limite']}</small><br>
                            <small>👤 {tarea['responsable_nombre']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        opciones_cols = columnas_df['nombre'].tolist()
                        idx_actual = opciones_cols.index(col_nombre)
                        
                        nuevo_estado = st.selectbox(
                            "Mover a:", 
                            opciones_cols, 
                            index=idx_actual, 
                            key=f"move_{tarea['id']}",
                            label_visibility="collapsed"
                        )
                        
                        if nuevo_estado != col_nombre:
                            nuevo_col_id = columnas_df[columnas_df['nombre'] == nuevo_estado]['id'].values[0]
                            db.mover_tarea(tarea['id'], nuevo_col_id)
                            st.rerun()

    with tab_dashboard:
        st.header("Métricas del Proyecto")
        if not tareas_df.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", len(tareas_df))
            hoy = datetime.datetime.now().strftime('%Y-%m-%d')
            col2.metric("Atrasadas", len(tareas_df[(tareas_df['fecha_limite'] < hoy) & (tareas_df['columna_id'] != 3)]))
            col3.metric("Terminadas", len(tareas_df[tareas_df['columna_id'] == 3]))
            st.bar_chart(tareas_df['columna_id'].map(dict(zip(columnas_df['id'], columnas_df['nombre']))).value_counts())

    with tab_equipo:
        st.header("Directorio")
        st.dataframe(pd.read_sql("SELECT nombre, email FROM Usuarios", db.get_conn()), use_container_width=True)
