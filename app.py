from flask import render_template, Flask, redirect, request, url_for, jsonify,session,make_response,send_file
import pandas as pd
from dotenv import load_dotenv
import mysql.connector.pooling
from mysql.connector import Error
from flask import session
from datetime import datetime,date,timedelta
from io import BytesIO
import math
from flask_cors import CORS
import os
import boto3

load_dotenv()
##########################################################################################################
# load the values
Host = os.getenv("Host")
user = os.getenv("User")
db_password = os.getenv("db_password")
db_name = os.getenv("db_name") 

aws_acess = os.getenv("aws_access_key_id")
aws_secret = os.getenv("aws_secret")
region_name = os.getenv("region_name")
bucket_name = os.getenv("BUCKET_NAME")

# Bucket details
BUCKET_NAME = bucket_name
region_name = region_name
########################################################################################################
app = Flask(__name__)
########################################################################################################
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
########################################################################################################
# Database connection pool for AWS database
dbconfig = {
    "host": Host,
    "user": user,
    "password": db_password,
    "database": db_name
}
########################################################################################################
# connection Pool
mydb_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="mypool",
                                                        pool_size=5,
                                                        **dbconfig)
########################################################################################################
# secret key for session
app.secret_key='neeraj'
########################################################################################################
# database connection
def get_db_connection():
    return mydb_pool.get_connection()
CORS(app)

s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_acess,
    aws_secret_access_key=aws_secret,
    region_name=region_name
)
utc_now = datetime.utcnow()
india_time = utc_now + timedelta(hours=5, minutes=30)
timestamp = india_time.strftime("%Y-%m-%d %H:%M:%S") 
start_of_day = india_time.replace(hour=0, minute=0, second=0, microsecond=0)
hour_end = india_time.replace(minute=0, second=0, microsecond=0)
hour_start = hour_end - timedelta(hours=1)
last_day = start_of_day - timedelta(days=1)

########################################################################################################
def user(u_email,u_password):
    connection =None
    user_data =None
    try:
        connection =get_db_connection()
        with connection.cursor(buffered=True) as cursor:
            query_user = "SELECT * FROM sa_users WHERE u_email = %s AND u_password = %s "
            cursor.execute(query_user, (u_email, u_password))

            user_data = cursor.fetchone()
            if user_data:
                return user_data
            else:
                return "Invalid credentials or account is inactive."
    except Exception as e:
        print(f"Error fetching user data: {e}")
        user_data = None
    finally:
        if connection:
            connection.close()

    return user_data
########################################################################################################
# login / index page
# @app.route('/', methods=['POST', 'GET'])
# def index():
    connection = None
    error = ""

    if request.method == 'POST':
        try:
            u_email = request.form['username']
            u_password = request.form['password']
            print(u_email,u_password,"DHD")
            session['u_email'] = u_email
            session['u_password'] = u_password

            user_data = user(u_email, u_password)
            user_type = user_data[5]

            if u_email and u_password =='test':
                return redirect(url_for('data_table'))
           
            else:
                error = "Invalid Email or password"
        except Exception as e:
            print(f"Error during login process: {e}")
            return "An error occurred during login. Please try again later.", 500
        finally:
            if connection:
                connection.close()
    
    return render_template('index.html', error=error)
########################################################################################################
#############################################################################################################
# data table 
@app.route('/', methods=['POST', 'GET'])
def index():
   
    return render_template('tablesdata.html')
########################################################################################################
@app.route('/data_table')
def data_table():    
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                alldata = "SELECT * FROM dc_data ORDER BY timestamp DESC LIMIT 700"
                cursor.execute(alldata)
                alldataprint = cursor.fetchall()

        return render_template('tabledata.html', alldataprint="alldataprint")

    except Exception as e:
        print(f"Error in /data_table: {e}")
        return "An error occurred while retrieving the data. Please try again later.", 500

########################################################################################################

# Function for logout and clear it sessions
@app.route('/logout', methods=['POST'])
def logout():
    
    session.clear() 
    response = make_response(redirect(url_for('index')))  # Redirect to index
    response.set_cookie('sessionID', expires=0)

    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    return response

# Optionally, you may want to allow GET to log out as well for general safety.
@app.route('/logout', methods=['GET'])
def logout_get_redirect():
    return redirect(url_for('index'))
########################################################################################################
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
########################################################################################################
