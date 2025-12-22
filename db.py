import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="hopper.proxy.rlwy.net",
        port=40776,
        user="appuser",
        password="AppUser@123",
        database="railway"
    )
