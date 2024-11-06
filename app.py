from flask import render_template, Flask, redirect, request, url_for, jsonify,session,make_response
from dotenv import load_dotenv
import mysql.connector.pooling
from mysql.connector import Error
from datetime import datetime,date
import math
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
            SELECT distinct(dc.Device_id)
            FROM dc_data dc
            JOIN ac_data ac ON dc.Device_id = ac.Device_id
            ORDER BY dc.Device_id"""
            cursor.execute(alldata)
            alldataprint = cursor.fetchall()
            
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
                SELECT TRUNCATE(Dc_Current, 5) AS Current, timestamp,Dc_Power, Temperature, 
                TRUNCATE(Dc_Voltage, 5) AS Voltage, TRUNCATE((Dc_Voltage * Dc_Current),5) AS cal_power,Device_id,
                TRUNCATE(TRUNCATE(Dc_Power,5)-TRUNCATE((Dc_Voltage * Dc_Current),5),5) as error,panel_voltage,panel_current 
                FROM dc_data WHERE Device_id = %s ORDER BY timestamp DESC LIMIT 1"""
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
                SELECT CAST(SUM(hourly.avg_kWh) AS UNSIGNED) AS total_avg_kWh_24h
                FROM (SELECT DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') AS hour,
                AVG(Dc_KWH) AS avg_kWh FROM dc_data WHERE Device_id = %s GROUP BY hour
                ) AS hourly """
                cursor.execute(dc_total_unit_query, (device,))
                dc_total_unit = cursor.fetchone()

                # Fetch AC data
                Accurrent_query = """
                SELECT TRUNCATE(Current, 5) AS Current, timestamp,Power, Temperature, TRUNCATE(Voltage, 5) AS Voltage, 
                TRUNCATE((Voltage * Current),5) AS cal_power,Device_id,
                TRUNCATE(TRUNCATE(Power,5)-TRUNCATE((Voltage * Current),5),5) as error FROM ac_data 
                WHERE Device_id = %s ORDER BY timestamp DESC LIMIT 1"""
                cursor.execute(Accurrent_query, (device,))
                Accurrentdata = cursor.fetchone()
                
                #AC KWH 1 hour
                ac_total_kwh_query = """
                SELECT 
                CAST(AVG(kWh_Consumed) AS DECIMAL(10, 5)) AS avg_kWh,
                DATE_FORMAT(CONVERT_TZ(NOW() - INTERVAL 1 HOUR, 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') AS start_time,
                DATE_FORMAT(CONVERT_TZ(NOW(), 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') AS end_time
                FROM ac_data WHERE Device_id = %s
                AND timestamp >= DATE_FORMAT(CONVERT_TZ(NOW() - INTERVAL 1 HOUR, 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') 
                AND timestamp < DATE_FORMAT(CONVERT_TZ(NOW(), 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00')
                """
                cursor.execute(ac_total_kwh_query, (device,))
                ac_total_kwh = cursor.fetchone()

                today_date = date.today()
                
                #AC KWH 24-hours
                total_kwh_query = """
                SELECT CAST(SUM(hourly.avg_kWh) AS DECIMAL(10, 5)) AS total_avg_kWh_24h
                FROM (SELECT DATE_FORMAT(timestamp, '%Y-%m-%D %H:00:00') AS hour,
                AVG(kWh_Consumed) AS avg_kWh FROM ac_data WHERE Device_id = %s AND timestamp >= %s GROUP BY hour
                ) AS hourly
                """
                cursor.execute(total_kwh_query, (device,today_date))
                total_kwh = cursor.fetchone()

                total_kwh_value = total_kwh[0] if total_kwh and total_kwh[0] is not None else 0
                
                # AC Units Calculation
                total_unit_query = """
                SELECT CAST(SUM(hourly.avg_kWh) AS UNSIGNED) AS total_avg_kWh_24h
                FROM (SELECT DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') AS hour,
                AVG(kWh_Consumed) AS avg_kWh FROM ac_data WHERE Device_id = %s 
                GROUP BY hour) AS hourly """
                cursor.execute(total_unit_query, (device,))
                total_unit = cursor.fetchone()

                # Determine Device Type and Battery Voltage Range
                device2 = int(device)
                if 2000 <= device2 < 3000: #12V LEAD
                    battery_percentage = ((currentdata[4]-10.5)/(12.7-10.5))*100
                elif 1000 <= device2 < 2000: #24V LEAD
                    battery_percentage = ((currentdata[4]-22)/(27-22))*100
                elif 3000 <= device2 < 4000: #12V Lithium
                    battery_percentage = ((currentdata[4]-10.5)/(14.6-10.5))*100
                else: #24V Lithium
                    battery_percentage = math.trunc(((currentdata[4]-19.8)/(26-19.8))*100)
                battery_percentage = max(0, min(100, battery_percentage))
               
                return render_template(
                    'summary.html',
                    battery_chargefull=int(battery_percentage),
                    Dccurrent=currentdata,
                    Accurrent=Accurrentdata,
                    dc_kwh=dc_kwh,
                    dc_total_kwh_value=dc_total_kwh_value,
                    dc_total_unit=dc_total_unit,
                    total_kwh_value=total_kwh_value,
                    ac_total_kwh=ac_total_kwh,
                    total_unit=total_unit,today_date=today_date
                )    
    except Exception as e:
                 return str(e), 500

# Table data
@app.route('/data')
def data_table():    
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # Fetch DC data
                alldata = "SELECT * FROM dc_data order by timestamp desc LIMIT 700"
                cursor.execute(alldata)
                alldataprint = cursor.fetchall()
                
                # Fetch AC data
                Acdata = "SELECT * FROM ac_data order by timestamp desc LIMIT 700"
                cursor.execute(Acdata)
                allAcdataprint = cursor.fetchall()

        return render_template('table.html', alldataprint=alldataprint, Acalldataprint=allAcdataprint)

    except Exception as e:
        return "An error occurred while retrieving the data. Please try again later.", 500

#DC DATA GRAPH
@app.route('/livegraphdc/<string:id>')
def livegraphdc(id):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                query = """
                    SELECT timestamp, Dc_Current, Dc_Voltage 
                    FROM dc_data WHERE Device_id = %s 
                """
                params = [id]

                if start_date and end_date:
                    query += " AND timestamp BETWEEN %s AND %s"
                    params.append(start_date)
                    params.append(end_date)
                else:
                    query += " AND timestamp >= NOW() - INTERVAL 4 HOUR" 

                cursor.execute(query, params)
                livedc_graph_data = cursor.fetchall()

                for item in livedc_graph_data:
                    item['timestamp'] = item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify(livedc_graph_data)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while fetching graph data."}), 500

#AC DATA GRAPH
@app.route('/livegraphac/<string:id>')
def livegraphac(id):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                query = """
                SELECT timestamp, Current, Voltage 
                FROM ac_data WHERE Device_id = %s 
                """
                params = [id]

                if start_date and end_date:
                    query += " AND timestamp BETWEEN %s AND %s"
                    params.append(start_date)
                    params.append(end_date)
                else:
                    query += " AND timestamp >= NOW() - INTERVAL 4 HOUR"  

                cursor.execute(query, params)
                liveac_graph_data = cursor.fetchall()
                
                for item in liveac_graph_data:
                    item['timestamp'] = item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(liveac_graph_data)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while fetching graph data."}), 500
    
# model E
@app.route('/modeledata')
def modeledata():    
    try:
        with get_db_connection() as connection:
            with connection.cursor(buffered=True) as cursor:
                # Fetch DC data
                alldata = "SELECT * FROM model_e"
                cursor.execute(alldata)
                alldataprint = cursor.fetchall()
               
        return render_template('modele.html', alldataprint=alldataprint)

    except Exception as e:
        return "An error occurred while retrieving the data. Please try again later.", 500
    
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
