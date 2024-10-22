from flask import render_template, Flask, redirect, request, url_for ,jsonify
from dotenv import load_dotenv
import mysql.connector.pooling
from mysql.connector import Error
import os

# Load environment variables from .env file
load_dotenv()

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
                                                        pool_size=8,
                                                        **dbconfig)

def get_db_connection():
    return mydb_pool.get_connection()


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

@app.route('/dashboard')
def dash():
    try:
        with get_db_connection() as connection:
            with connection.cursor(buffered=True) as cursor:
                alldata = """
                SELECT dc.Device_id, dc.Dc_KWH, ac.kWh_Consumed, (dc.Dc_KWH - ac.kWh_Consumed) AS Remaining_KWH
                FROM dc_data dc
                JOIN ac_data ac ON dc.Device_id = ac.Device_id
                WHERE dc.timestamp = (SELECT MAX(timestamp) FROM dc_data WHERE Device_id = dc.Device_id)
                AND ac.timestamp = (SELECT MAX(timestamp) FROM ac_data WHERE Device_id = ac.Device_id)
                ORDER BY dc.Device_id"""
                cursor.execute(alldata)
                alldataprint = cursor.fetchall()
                
        return render_template('maindashboard.html', alldataprint=alldataprint)
    
    except Exception as e:
        return str(e), 500

@app.route('/databyid')
def databyid():
    try:
        
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                alldata = """
                select * from dc_data"""
                cursor.execute(alldata)
                alldataprint = cursor.fetchall()
              
        return render_template('.html',items=alldataprint)
    
    except Exception as e:
        print(f"Error: {e}")
        return "An error occurred while fetching data. Please try again later.", 500

@app.route('/summary/<device>')
def summary(device):
    try:
        with get_db_connection() as connection:
            with connection.cursor(buffered=True) as cursor:
                alldata = """
                select dc.Device_id, max(dc.Dc_KWH),max(ac.kWh_Consumed),( max(dc.Dc_KWH)-max(ac.kWh_Consumed)) from dc_data dc
            join ac_data ac on dc.Device_id=ac.Device_id
                  WHERE dc.Device_id = %s """
                cursor.execute(alldata,(device,))
                alldataprint = cursor.fetchone()

                current = """
                SELECT Dc_Current,timestamp,Dc_KWH,Dc_Power,Temperature FROM dc_data WHERE Device_id = %s order by timestamp desc LIMIT 1"""
                cursor.execute(current, (device,))  
                currentdata = cursor.fetchone()
                Accurrent = """
                SELECT Current,timestamp,kWh_Consumed,Power,Temperature FROM ac_data WHERE Device_id = %s order by timestamp desc LIMIT 1"""
                cursor.execute(Accurrent, (device,))  
                Accurrentdata = cursor.fetchone()

        return render_template('dashboard.html', Dccurrent=currentdata, Accurrent=Accurrentdata,alldataprint=alldataprint)
    
    except Exception as e:
        return str(e), 500
 

@app.route('/data')
def data_table():    
    try:
        
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                alldata = """
                select * from dc_data"""
                cursor.execute(alldata)
                alldataprint = cursor.fetchall()
                
                Acdata = """
                select * from ac_data"""
                cursor.execute(Acdata)
                allAcdataprint = cursor.fetchall()
              
        return render_template('table.html',alldataprint=alldataprint,Acalldataprint=allAcdataprint)

    except Exception as e:
        return str(e), 500

# @app.route('/databyid')
# def databyid():
#     try:
        
#         with get_db_connection() as connection:
#             with connection.cursor(dictionary=True) as cursor:
#                 # query for Robot table
#                 alldata = """
#                 select * from dc_data"""
#                 cursor.execute(alldata)
#                 alldataprint = cursor.fetchall()
              
#         # Render the data in your HTML template
#         return render_template('watt.html',items=alldataprint)
    
#     except Exception as e:
#         print(f"Error: {e}")
#         return "An error occurred while fetching data. Please try again later.", 500


@app.route('/graphdata')
def graphdata():
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # Query to fetch only timestamp and Dc_Voltage for the graph
                query = """
                    SELECT timestamp, Dc_Current FROM dc_data
                """
                cursor.execute(query)
                graph_data = cursor.fetchall()
                # Convert data to the right format (if necessary)
                for item in graph_data:
                    item['timestamp'] = item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')  # Format the timestamp
        return jsonify(graph_data)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while fetching graph data."}), 500

@app.route('/graphdatatemperature')
def graphdatatemperature():
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # Query to fetch only timestamp and Dc_Voltage for the graph
                query = """
                    SELECT timestamp, Temperature FROM dc_data
                """
                cursor.execute(query)
                graph_data = cursor.fetchall()
                # Convert data to the right format (if necessary)
                for item in graph_data:
                    item['timestamp'] = item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')  # Format the timestamp
        return jsonify(graph_data)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while fetching graph data."}), 500
# graph 3
@app.route('/graph3')
def graph3():
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # Query to fetch only timestamp and Dc_Voltage for the graph
                query = """
                    SELECT timestamp, Temperature FROM dc_data
                """
                cursor.execute(query)
                graph_data = cursor.fetchall()
                # Convert data to the right format (if necessary)
                for item in graph_data:
                    item['timestamp'] = item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')  # Format the timestamp
        return jsonify(graph_data)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while fetching graph data."}), 500

@app.route('/graph4')
def graph4():
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # Query to fetch only timestamp and Dc_Voltage for the graph
                query = """
                    SELECT timestamp, Temperature FROM dc_data
                """
                cursor.execute(query)
                graph_data = cursor.fetchall()
                # Convert data to the right format (if necessary)
                for item in graph_data:
                    item['timestamp'] = item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')  # Format the timestamp
        return jsonify(graph_data)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while fetching graph data."}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
