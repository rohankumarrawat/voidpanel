import sys
sys.path.insert(0, '/var/www/panel')
import mysql.connector

passw = open('/etc/dontdelete.txt').read().strip()
print('Password loaded:', bool(passw))

try:
    conn = mysql.connector.connect(host='localhost', user='root', password=passw)
    if conn.is_connected():
        cur = conn.cursor()
        cur.execute('SELECT User, Db FROM mysql.db;')
        rows = cur.fetchall()
        print('All rows:', rows)
        filter_string = 'namanit_'
        mappings = []
        for user, db in rows:
            if user.startswith(filter_string) or db.startswith(filter_string):
                mappings.append({'user': user, 'database': db})
        print('Filtered:', mappings)
except Exception as e:
    print('ERROR:', e)
