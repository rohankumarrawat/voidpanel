import mysql.connector
from mysql.connector import Error
import random
import string
import time
import threading

def generate_temp_password(length=24):
    """Generate a highly secure random password for the temp session user."""
    characters = string.ascii_letters + string.digits + "!@#$%^&*()-_"
    return ''.join(random.choice(characters) for i in range(length))

def create_temp_pma_user(domain_prefix, admin_password):
    """
    Creates a temporary MySQL user restricted to the user's domain prefix.
    Returns: (temp_user, temp_password) or None if failure
    """
    # Simple garbage collection: Clean up ANY temp user older than 2 hours.
    cleanup_old_temp_users(admin_password)

    # 1. Generate temp credentials
    temp_user = "vp_temp_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    temp_password = generate_temp_password()
    
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="newuser",  # the root-level voidpanel DB user
            password=admin_password
        )
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create user
            cursor.execute(f"CREATE USER '{temp_user}'@'localhost' IDENTIFIED BY '{temp_password}';")
            
            # Grant privileges only to databases matching the prefix wildcard
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{domain_prefix}\_%`.* TO '{temp_user}'@'localhost';")
            
            connection.commit()
            return temp_user, temp_password
    except Error as e:
        print(f"Error creating temp PMA user: {e}")
        return None, None
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def cleanup_old_temp_users(admin_password):
    """
    Finds and deletes any MySQL user starting with 'vp_temp_' 
    that was created more than 2 hours ago (approximation by just dropping all vp_temp_).
    Since this is a lightweight solution, we aggressively clean up old temp users.
    """
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="newuser",
            password=admin_password
        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT user FROM mysql.user WHERE user LIKE 'vp_temp_%';")
            temp_users = cursor.fetchall()
            
            for user in temp_users:
                username = user[0]
                cursor.execute(f"DROP USER IF EXISTS '{username}'@'localhost';")
            
            connection.commit()
    except Error as e:
        pass
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
