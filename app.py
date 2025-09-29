from flask import Flask, render_template, redirect, url_for, session, make_response, request
from flask_cors import CORS
from dotenv import load_dotenv
import mysql.connector.pooling
from datetime import datetime, timedelta
import boto3
import os

# Load environment variables from .env file
load_dotenv()

# MySQL config
Host = os.getenv("Host")
user = os.getenv("User")
db_password = os.getenv("db_password")
db_name = os.getenv("db_name")

# AWS S3 config (optional)
aws_access = os.getenv("aws_access_key_id")
aws_secret = os.getenv("aws_secret")
region_name = os.getenv("region_name")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'neeraj'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
CORS(app)

# MySQL connection pool
dbconfig = {
    "host": Host,
    "user": user,
    "password": db_password,
    "database": db_name
}

mydb_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    **dbconfig
)

def get_db_connection():
    return mydb_pool.get_connection()

# AWS S3 client (optional)
s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access,
    aws_secret_access_key=aws_secret,
    region_name=region_name
)

# IST datetime setup
utc_now = datetime.utcnow()
india_time = utc_now + timedelta(hours=5, minutes=30)
timestamp = india_time.strftime("%Y-%m-%d %H:%M:%S")
start_of_day = india_time.replace(hour=0, minute=0, second=0, microsecond=0)
hour_end = india_time.replace(minute=0, second=0, microsecond=0)
hour_start = hour_end - timedelta(hours=1)
last_day = start_of_day - timedelta(days=1)

# ===================== ROUTES =========================
def user(u_email, u_password):
    user_data = None
    try:
        with get_db_connection() as connection:
            with connection.cursor(buffered=True) as cursor:
                query_user = "SELECT * FROM sa_users WHERE u_email = %s AND u_password = %s"
                cursor.execute(query_user, (u_email, u_password))
                user_data = cursor.fetchone()
    except Exception as e:
        print(f"Error fetching user data: {e}")

    return user_data if user_data else "Invalid credentials or account is inactive."


@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    if request.method == 'POST':
        try:
            u_email = request.form['username'].lower()
            u_password = request.form['password']
            session['u_email'] = u_email
            session['password'] = u_password

            user_data = user(u_email, u_password)
          
            if user_data:
               return redirect(url_for('dashboard'))
            else:
                    error = "Invalid Email or password"

        except Exception as e:
            return f"<h2 style='color:red;'>Error in / route: {e}</h2>", 500

    return render_template('index.html', error=error)
#####################################################################################################
@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor(buffered=True) as cursor:
          query = """SELECT distinct(Device_id)
                        FROM ssb_locations
                           """
          cursor.execute(query)
          alldataprint = cursor.fetchall()
        return render_template('dashboard.html', alldataprint=alldataprint)
    except Exception as e:
        return f"<h2 style='color:red;'>Error in /ssbikedata route: {e}</h2>", 500
    finally:
        if connection:
            connection.close()

#####################################################################################################
@app.route('/ssbikedata/<device_id>', methods=['GET'])
def ssbikedata(device_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor(buffered=True) as cursor:
          query = """SELECT Device_id, Ignition, UID, Latitude, Longitude, Satellites, received_at, speed_kmph
                FROM ssb_locations
                WHERE Device_id = %s
                ORDER BY received_at DESC
                LIMIT 1;
           """
          cursor.execute(query, (device_id,))
          alldataprint = cursor.fetchone()
        return render_template('data.html', alldataprint=alldataprint)
    except Exception as e:
        return f"<h2 style='color:red;'>Error in /ssbikedata route: {e}</h2>", 500
    finally:
        if connection:
            connection.close()

#####################################################################################################

@app.route('/tablesdata', methods=['GET', 'POST'])
def tablesdata():
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor(dictionary=True) as cursor: 
            query = "SELECT * FROM ssb_locations LIMIT 1000"
            cursor.execute(query)
            alldataprint = cursor.fetchall()
        return render_template('alldatatable.html', alldataprint=alldataprint)
    except Exception as e:
        return f"<h2 style='color:red;'>Error in /alldatatable route: {e}</h2>", 500
    finally:
        if connection:
            connection.close()


###########################################################################################
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    response = make_response(redirect(url_for('index')))
    response.set_cookie('sessionID', expires=0)

    # Cache control headers
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    return response

# ===================== RUN =========================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)