from flask import render_template, Flask, redirect, request, url_for, jsonify,session,make_response
from dotenv import load_dotenv
import mysql.connector.pooling
from mysql.connector import Error
from datetime import datetime,date
import os
load_dotenv()

# load the values
Host = os.getenv("Host")
user = os.getenv("User")
db_password = os.getenv("db_password")
db_name = os.getenv("db_name")

app = Flask(__name__)

# Database connection pool for AWS database
dbconfig = {
    "host": Host,
    "user": user,
    "password": db_password,
    "database": db_name
}

# connection Pool
mydb_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="mypool",
                                                        pool_size=5,
                                                        **dbconfig)
# secret key for session
app.secret_key='neeraj'

# database connection
def get_db_connection():
    return mydb_pool.get_connection()

# to truncate the values 
def truncate(value, decimal_places):
    if isinstance(value, float):
        factor = 10 ** decimal_places
        return int(value * factor) / factor
    return value

def truncate_values(data, decimal_places):
    if isinstance(data, (tuple, list)):
        return tuple(truncate(val, decimal_places) for val in data if isinstance(val, (int, float)))
    elif isinstance(data, (int, float)):
        return truncate(data, decimal_places)
    return data 

# login / index page
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        try:
            u_email = request.form['username']
            u_password = request.form['password']
            if u_email == 'test' and u_password == 'test':
                return redirect(url_for('dash'))
            else:
                error = "Invalid Email or password"
                return render_template('index.html', error=error)
        except Exception as e:
            print(f"Error during login process: {e}")
            return "An error occurred during login. Please try again later.", 500
    return render_template('index.html', error="")

# frontpage / homepage
@app.route('/dashboard')
def dash():
    connection = None
    try:
        connection = get_db_connection()  
        with connection.cursor(buffered=True) as cursor:
            alldata = """
            SELECT dc.Device_id, dc.Dc_KWH, ac.kWh_Consumed, (dc.Dc_KWH - ac.kWh_Consumed) AS Remaining_KWH
            FROM dc_data dc
            LEFT JOIN ac_data ac ON dc.Device_id = ac.Device_id
            WHERE dc.timestamp = (SELECT MAX(timestamp) FROM dc_data WHERE Device_id = dc.Device_id)
            AND ac.timestamp = (SELECT MAX(timestamp) FROM ac_data WHERE Device_id = ac.Device_id)
            ORDER BY dc.Device_id"""
            cursor.execute(alldata)
            alldataprint = cursor.fetchall()
            
            # truncated_data = []
            # for row in alldataprint:
            #     truncated_row = (
            #         row[0],  
            #         truncate(row[1], 5), 
            #         truncate(row[2], 5),  
            #         truncate(row[3], 5)   
            #     )
            #     truncated_data.append(truncated_row)
        return render_template('maindashboard.html', alldataprint=alldataprint)
    
    except Exception as e:
        return str(e), 500

    finally:
        if connection:
            connection.close() 

# Summary page
@app.route('/summary/<device>')
def summary(device):
    try:
        with get_db_connection() as connection:
            with connection.cursor(buffered=True) as cursor:
                # Fetch DC data
                current_query = """
                SELECT TRUNCATE(Dc_Current, 5) AS Current, timestamp,Dc_Power, Temperature, TRUNCATE(Dc_Voltage, 5) AS Voltage, TRUNCATE((Dc_Voltage * Dc_Current),5) AS cal_power,Device_id,TRUNCATE(TRUNCATE(Dc_Power,5)-TRUNCATE((Dc_Voltage * Dc_Current),5),5) as error FROM dc_data WHERE Device_id = %s ORDER BY timestamp DESC LIMIT 1"""
                cursor.execute(current_query, (device,))
                currentdata = cursor.fetchone()
                
                #DC KWH 1 hour
                dc_total_kwh_query = """
                SELECT 
                CAST(AVG(Dc_KWH) AS DECIMAL(10, 5)) AS avg_kWh,
                DATE_FORMAT(CONVERT_TZ(NOW() - INTERVAL 1 HOUR, 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') AS start_time,
                DATE_FORMAT(CONVERT_TZ(NOW(), 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') AS end_time
                FROM dc_data 
                WHERE Device_id = %s
                AND timestamp >= DATE_FORMAT(CONVERT_TZ(NOW() - INTERVAL 1 HOUR, 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') 
                AND timestamp < DATE_FORMAT(CONVERT_TZ(NOW(), 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00')
                """
                cursor.execute(dc_total_kwh_query, (device,))
                dc_kwh = cursor.fetchone()

                today_date = date.today()
                
                #DC KWH 24-hours
                dc_total_kwh_query = """
                SELECT 
                CAST(SUM(hourly.avg_kWh) AS DECIMAL(10, 5)) AS total_avg_kWh_24h
                FROM (
                    SELECT 
                        DATE_FORMAT(timestamp, '%Y-%m-%D %H:00:00') AS hour,
                        AVG(Dc_KWH) AS avg_kWh
                    FROM dc_data WHERE Device_id = %s AND timestamp >= %s GROUP BY hour
                ) AS hourly
                """
                cursor.execute(dc_total_kwh_query, (device,today_date))
                dc_total_kwh = cursor.fetchone()

                dc_total_kwh_value = dc_total_kwh[0] if dc_total_kwh and dc_total_kwh[0] is not None else 0

                #DC Units
                dc_total_unit_query = """
               SELECT 
                    CAST(SUM(hourly.avg_kWh) AS UNSIGNED) AS total_avg_kWh_24h
                FROM (
                    SELECT 
                        DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') AS hour,
                        AVG(Dc_KWH) AS avg_kWh
                    FROM dc_data 
                    WHERE Device_id = %s 
                    GROUP BY hour
                ) AS hourly """
                cursor.execute(dc_total_unit_query, (device,))
                dc_total_unit = cursor.fetchone()

                # Fetch AC data
                Accurrent_query = """
                SELECT TRUNCATE(Current, 5) AS Current, timestamp,Power, Temperature, TRUNCATE(Voltage, 5) AS Voltage, TRUNCATE((Voltage * Current),5) AS cal_power,Device_id,TRUNCATE(TRUNCATE(Power,5)-TRUNCATE((Voltage * Current),5),5) as error FROM ac_data WHERE Device_id = %s ORDER BY timestamp DESC LIMIT 1"""
                cursor.execute(Accurrent_query, (device,))
                Accurrentdata = cursor.fetchone()
                
                #AC KWH 1 hour
                ac_total_kwh_query = """
                SELECT 
                CAST(AVG(kWh_Consumed) AS DECIMAL(10, 5)) AS avg_kWh,
                DATE_FORMAT(CONVERT_TZ(NOW() - INTERVAL 1 HOUR, 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') AS start_time,
                DATE_FORMAT(CONVERT_TZ(NOW(), 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') AS end_time
                FROM ac_data 
                WHERE Device_id = %s
                AND timestamp >= DATE_FORMAT(CONVERT_TZ(NOW() - INTERVAL 1 HOUR, 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') 
                AND timestamp < DATE_FORMAT(CONVERT_TZ(NOW(), 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00')
                """
                cursor.execute(ac_total_kwh_query, (device,))
                ac_total_kwh = cursor.fetchone()

                today_date = date.today()
                
                #AC KWH 24-hours
                total_kwh_query = """
                SELECT 
                CAST(SUM(hourly.avg_kWh) AS DECIMAL(10, 5)) AS total_avg_kWh_24h
                FROM (
                    SELECT 
                        DATE_FORMAT(timestamp, '%Y-%m-%D %H:00:00') AS hour,
                        AVG(kWh_Consumed) AS avg_kWh
                    FROM ac_data WHERE Device_id = %s AND timestamp >= %s GROUP BY hour
                ) AS hourly
                """
                cursor.execute(total_kwh_query, (device,today_date))
                total_kwh = cursor.fetchone()

                total_kwh_value = total_kwh[0] if total_kwh and total_kwh[0] is not None else 0

                #AC Units
                total_unit_query = """
               SELECT 
                    CAST(SUM(hourly.avg_kWh) AS UNSIGNED) AS total_avg_kWh_24h
                FROM (
                    SELECT 
                        DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') AS hour,
                        AVG(kWh_Consumed) AS avg_kWh
                    FROM ac_data 
                    WHERE Device_id = %s 
                    GROUP BY hour
                ) AS hourly """
                cursor.execute(total_unit_query, (device,))
                total_unit = cursor.fetchone()
               
                device2 = int(device)
                if 1000 <= device2 < 2000:
                    device_type = "12V Lead"
                elif 2000 <= device2 < 3000:
                    device_type = "24V Lead"
                elif 3000 <= device2 < 4000:
                    device_type = "12V Lithium"
                else:
                    device_type = "24V Lithium"

        return render_template('summary.html', Dccurrent=currentdata, Accurrent=Accurrentdata,dc_kwh=dc_kwh,dc_total_kwh_value=dc_total_kwh_value,dc_total_unit=dc_total_unit, total_kwh_value=total_kwh_value,ac_total_kwh=ac_total_kwh,total_unit=total_unit)

    except Exception as e:
        return str(e), 500

# Table data
@app.route('/data')
def data_table():    
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # Fetch DC data
                alldata = "SELECT * FROM dc_data"
                cursor.execute(alldata)
                alldataprint = cursor.fetchall()
                
                # Fetch AC data
                Acdata = "SELECT * FROM ac_data"
                cursor.execute(Acdata)
                allAcdataprint = cursor.fetchall()

        return render_template('table.html', alldataprint=alldataprint, Acalldataprint=allAcdataprint)

    except Exception as e:
        return "An error occurred while retrieving the data. Please try again later.", 500

#DC DATA GRAPH
@app.route('/livegraphdc/<string:id>')
def livegraphdc(id):
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                query = """
                    SELECT timestamp, Dc_Current, Dc_Voltage 
                    FROM dc_data 
                    WHERE Device_id = %s
                """
                cursor.execute(query, (id,))
                livedc_graph_data = cursor.fetchall()
                
                # Format the timestamp for each record
                for item in livedc_graph_data:
                    item['timestamp'] = item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify(livedc_graph_data)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while fetching graph data."}), 500

#AC DATA GRAPH
@app.route('/livegraphac/<string:id>')
def livegraphac(id):
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                query = """
                    SELECT timestamp,Current,Voltage FROM ac_data WHERE Device_id = %s
                """
                cursor.execute(query, (id,))
                liveac_graph_data = cursor.fetchall()
               
                for item in liveac_graph_data:
                    item['timestamp'] = item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(liveac_graph_data)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while fetching graph data."}), 500
    
# Logout Page
@app.route('/logout')
def logout():
    session.clear()
    response = make_response(redirect(url_for('index')))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
