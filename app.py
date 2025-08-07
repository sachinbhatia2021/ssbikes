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

@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                query = "SELECT * FROM ssb_locations;" 
                cursor.execute(query)
                alldataprint = cursor.fetchall()

            return render_template('tablesdata.html',alldataprint=alldataprint)

    except Exception as e:
        return f"<h2 style='color:red;'>Error in / route: {e}</h2>", 500


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
