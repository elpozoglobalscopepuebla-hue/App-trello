import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import sqlite3
from db import get_conn

# Configuración de correo (Usa variables de entorno en producción)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "tu_correo@gmail.com"
SENDER_PASSWORD = "tu_password_de_aplicacion"

def enviar_correo(destinatario, asunto, cuerpo):
    if not destinatario: return
    try:
        msg = MIMEText(cuerpo)
        msg['Subject'] = asunto
        msg['From'] = SENDER_EMAIL
        msg['To'] = destinatario

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"Correo enviado a {destinatario}")
    except Exception as e:
        print(f"Error enviando correo: {e}")

def revisar_vencimientos():
    """Se ejecuta periódicamente para revisar tareas a menos de 24h de vencer."""
    conn = get_conn()
    c = conn.cursor()
    
    limite_24h = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    
    query = """
        SELECT t.id, t.titulo, u.email, u.nombre 
        FROM Tareas t
        JOIN Usuarios u ON t.responsable_id = u.id
        WHERE t.fecha_limite <= ? AND t.recordatorio_enviado = 0
    """
    c.execute(query, (limite_24h,))
    tareas_por_vencer = c.fetchall()

    for tarea in tareas_por_vencer:
        tarea_id, titulo, email, nombre = tarea
        asunto = f"Recordatorio: Tarea '{titulo}' próxima a vencer"
        cuerpo = f"Hola {nombre},\n\nTe recordamos que la tarea '{titulo}' vence en menos de 24 horas.\n\nSaludos."
        enviar_correo(email, asunto, cuerpo)
        
        # Marcar como enviado para no spamear
        c.execute("UPDATE Tareas SET recordatorio_enviado = 1 WHERE id = ?", (tarea_id,))
    
    conn.commit()
    conn.close()

def iniciar_scheduler():
    scheduler = BackgroundScheduler()
    # Configurar para que revise cada hora (aquí cada 1 minuto para pruebas)
    scheduler.add_job(revisar_vencimientos, 'interval', minutes=60) 
    scheduler.start()
    return scheduler