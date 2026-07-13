import mysql.connector
from mysql.connector import Error
import random
import string
import time
import os
import re

def generate_temp_password(length=24):
    """Generate a highly secure random password for the temp session user."""
    characters = string.ascii_letters + string.digits + "!@#$%^&*()-_"
    return ''.join(random.choice(characters) for i in range(length))

import subprocess

def get_mysql_admin_credentials(fallback_password=""):
    """Dynamically determine the active MySQL admin username and password via sudo."""
    # First priority: check /root/.my.cnf
    try:
        r = subprocess.run(['sudo', '-n', 'cat', '/root/.my.cnf'], capture_output=True, text=True)
        if r.returncode == 0:
            content = r.stdout
            m_user = re.search(r'user\s*=\s*(.*)', content)
            m_pass = re.search(r'password\s*=\s*(.*)', content)
            user = m_user.group(1).strip() if m_user else "root"
            password = m_pass.group(1).strip() if m_pass else ""
            if password:
                return user, password
    except Exception:
        pass
            
    # Second priority: standard voidpanel path
    try:
        r2 = subprocess.run(['sudo', '-n', 'cat', '/etc/dontdelete.txt'], capture_output=True, text=True)
        if r2.returncode == 0:
            return "newuser", r2.stdout.strip()
    except Exception:
        pass
        
    return "newuser", fallback_password

def log_dbg(msg):
    with open('/tmp/sso_debug.log', 'a') as f:
        f.write(msg + '\n')

def create_temp_pma_user(domain_prefix, admin_password):
    """
    Creates a temporary MySQL user restricted to the user's domain prefix.
    Returns: (temp_user, temp_password) or None if failure
    """
    try:
        cleanup_old_temp_users(admin_password)
        log_dbg("Cleaned old temp users")

        db_user, db_pass = get_mysql_admin_credentials(admin_password)
        log_dbg(f"Credentials fetched: {db_user}, pass len: {len(db_pass)}")

        # 1. Generate temp credentials
        temp_user = "vp_temp_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        temp_password = generate_temp_password()
        
        connection = mysql.connector.connect(
            host="localhost",
            user=db_user,
            password=db_pass
        )
        if connection.is_connected():
            cursor = connection.cursor()
            
            try:
                log_dbg(f"Creating user {temp_user}")
                cursor.execute(f"CREATE USER '{temp_user}'@'localhost' IDENTIFIED BY '{temp_password}';")
                log_dbg("Granting privileges")
                cursor.execute(f"GRANT ALL PRIVILEGES ON `{domain_prefix}\_%`.* TO '{temp_user}'@'localhost';")
                connection.commit()
                log_dbg("Success!")
                return temp_user, temp_password
            except Exception as inner_e:
                log_dbg(f"Execution Error: {inner_e}")
                return None, None
        else:
            log_dbg("Connection failed but no exception?")
            return None, None
    except Exception as e:
        log_dbg(f"Outer Error creating temp PMA user: {e}")
        print(f"Error creating temp PMA user: {e}")
        return None, None
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def cleanup_old_temp_users(admin_password):
    """
    Finds and deletes any MySQL user starting with 'vp_temp_' 
    """
    db_user, db_pass = get_mysql_admin_credentials(admin_password)
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user=db_user,
            password=db_pass
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
