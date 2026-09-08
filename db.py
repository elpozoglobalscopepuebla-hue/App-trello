import os
import psycopg2
import pandas as pd

def get_conn():
    # En Streamlit Cloud guardaremos esto de forma segura en los "Secrets"
    # Aquí puedes poner tus credenciales directas para pruebas locales
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "tu_host_de_supabase"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "tu_password"),
        port=os.getenv("DB_PORT", "5432")
    )

def verificar_login(email, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, nombre FROM Usuarios WHERE email = %s AND password = %s", (email, password))
    usuario = c.fetchone()
    conn.close()
    return usuario

def get_columnas(tablero_id):
    return pd.read_sql(f"SELECT * FROM Columnas WHERE tablero_id = {tablero_id}", get_conn())

def get_tareas(tablero_id):
    query = """
        SELECT t.*, u.nombre as responsable_nombre, u.email as responsable_email 
        FROM Tareas t 
        LEFT JOIN Usuarios u ON t.responsable_id = u.id 
        WHERE t.tablero_id = %s
    """
    return pd.read_sql(query, get_conn(), params=(tablero_id,))

def add_tarea(tablero_id, columna_id, titulo, desc, fecha, prioridad, resp_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO Tareas (tablero_id, columna_id, titulo, descripcion, fecha_limite, prioridad, responsable_id)
                 VALUES (%s, %s, %s, %s, %s, %s, %s)""", (tablero_id, columna_id, titulo, desc, fecha, prioridad, resp_id))
    conn.commit()
    conn.close()

def mover_tarea(tarea_id, nueva_col_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE Tareas SET columna_id = %s WHERE id = %s", (nueva_col_id, tarea_id))
    conn.commit()
    conn.close()