from flask import render_template, Flask, redirect, request, url_for, jsonify,session,make_response
from dotenv import load_dotenv
import mysql.connector.pooling
from mysql.connector import Error
from flask import session
from datetime import datetime,date,timedelta
import math
from flask_cors import CORS
import os
import boto3

load_dotenv()
########################################################################################################
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
@app.route('/', methods=['POST', 'GET'])
def index():
    connection = None
    error = ""

    if request.method == 'POST':
        try:
            u_email = request.form['username']
            u_password = request.form['password']

            session['u_email'] = u_email
            session['u_password'] = u_password

            user_data = user(u_email, u_password)
            user_type = user_data[5]

            if user_type == 1:
                return redirect(url_for('dash'))
            elif user_type == 2:
                return redirect(url_for('client_dash'))
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
# frontpage / homepage
@app.route('/client_dash')
def client_dash():
    connection = None
    try:
        u_email = session.get('u_email')
        connection = get_db_connection()  
        with connection.cursor(buffered=True) as cursor:
            alldata = """
            SELECT DISTINCT 
            dc.Device_id,
            t_generated.total_generated,
            t_consumed.total_consumed,
            CASE 
                WHEN TIMESTAMPDIFF(HOUR, dc.timestamp, NOW()) <= 1 THEN 'Active'
                ELSE 'Inactive'
            END AS status
        FROM dc_data dc
        JOIN (
            SELECT Device_id, MAX(timestamp) AS latest_timestamp
            FROM dc_data
            GROUP BY Device_id
        ) latest ON dc.Device_id = latest.Device_id AND dc.timestamp = latest.latest_timestamp

        LEFT JOIN ac_data ac ON dc.Device_id = ac.Device_id  -- Changed from JOIN to LEFT JOIN

        LEFT JOIN (
            SELECT device_id, SUM(avg_kwh) AS total_generated
            FROM dc_kwh
            GROUP BY device_id
        ) t_generated ON t_generated.device_id = dc.Device_id

        LEFT JOIN (
            SELECT device_id, SUM(avg_kwh) AS total_consumed
            FROM ac_kwh
            GROUP BY device_id
        ) t_consumed ON t_consumed.device_id = dc.Device_id

        JOIN sa_users u ON dc.company_id = u.company_id
        WHERE u.u_email =%s;

                                      """
            cursor.execute(alldata,(u_email,))
            alldataprint = cursor.fetchall()
            devicecount="""
                  
                    SELECT COUNT(DISTINCT dc.Device_id)
                    FROM dc_data dc
                    JOIN sa_users su ON dc.company_id = su.company_id
                    WHERE su.u_email = %s;
                """
            cursor.execute(devicecount,(u_email,))
            dcdevicecount=cursor.fetchone()[0]
            
               # unit generated
            Generated="""
                    SELECT sum(avg_kwh) from dc_kwh;

                    """
            cursor.execute(Generated)
            dcGenerated=cursor.fetchone()[0]

            # unit consumed
            acconsumed="""
                    SELECT sum(avg_kwh) from ac_kwh;

                    """
            cursor.execute(acconsumed)
            acconsumedunit=cursor.fetchone()[0]
        return render_template('/client/client_dash.html',alldataprint=alldataprint,dcGenerated=dcGenerated,
                                  acconsumedunit=acconsumedunit ,dcdevicecount=dcdevicecount,detail_user1='dd')
    
    except Exception as e:
        return str(e), 500

    finally:
        if connection:
            connection.close() 
##########################################################################################################

# frontpage / homepage
@app.route('/dash')
def dash():
    connection = None
    try:
        connection = get_db_connection()  
        with connection.cursor(buffered=True) as cursor:
          
               # unit generated
            Generated="""
                    SELECT sum(avg_kwh) from dc_kwh;

                    """
            cursor.execute(Generated)
            dcGenerated=cursor.fetchone()[0]

            # unit consumed
            acconsumed="""
                    SELECT sum(avg_kwh) from ac_kwh;

                    """
            cursor.execute(acconsumed)
            acconsumedunit=cursor.fetchone()[0]

            return render_template('maindashboard.html',dcGenerated=dcGenerated,
                                  acconsumedunit=acconsumedunit )
    
    except Exception as e:
        return str(e), 500

    finally:
        if connection:
            connection.close() 
##########################################################################################################
@app.route('/user_profile')
def user_profile():
    connection = None
    try:
        connection = get_db_connection()  
        with connection.cursor(buffered=True) as cursor:
      

            return render_template('client/profile.html',detail_user1='bb')
    
    except Exception as e:
        return str(e), 500

    finally:
        if connection:
            connection.close() 
# Function to insert Clientdetails data
@app.route('/clientinsert', methods=['POST'])
def clientinsert():
    connection = None
    try:
        data = request.form
        u_email = session.get('u_email')
        u_password = session.get('u_password')
        cd = user(u_email, u_password)
        company_id = cd[6] if cd else None

        if not company_id:
            return jsonify({'message': 'Please Login again'}), 400

        required_fields = ['fullName', 'email', 'mobileNo', 'address',
                           'district', 'pincode', 'State']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400

        if 'profile_image' not in request.files:
            return jsonify({'message': 'No file part'}), 400

        file = request.files['profile_image']
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400

        FOLDER_NAME = 'ImagesSolset'
        s3_key = f"{FOLDER_NAME}/{u_email}_{file.filename}"
        s3_client.upload_fileobj(
            file,
            BUCKET_NAME,
            s3_key,
            ExtraArgs={'ACL': 'public-read'}
        )
        s3_url = f"https://{BUCKET_NAME}.s3.{region_name}.amazonaws.com/{s3_key}"

        connection = get_db_connection()
        if connection is None:
            return jsonify({'message': 'Database connection error'}), 500

        with connection.cursor(buffered=True) as cursor:
            update_query = """
                UPDATE clientdetails SET profile_image = %s WHERE company_id = %s
            """
            cursor.execute(update_query, (s3_url, company_id))
            connection.commit()

            created_at = datetime.now()
            insert_query = """
                INSERT INTO clientdetails (company_id, full_Name, email, phone, address, district, State, pincode, created_at, profile_image)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                company_id,
                data['fullName'],
                data['email'],
                data['mobileNo'],
                data['address'],
                data['district'],
                data['State'],
                data['pincode'],
                created_at,
                s3_url
            )
            cursor.execute(insert_query, values)
            connection.commit()

        return jsonify({'message': 'Data inserted successfully'}), 200

    except mysql.connector.Error as e:
        print(f"Error with MySQL: {e}")
        return jsonify({'message': 'Error with MySQL: ' + str(e)}), 500

    finally:
        if connection:
            connection.close()
##########################################################################################################
#  inverter
@app.route('/alldevices')
def alldevices():
    connection = None
    try:
        connection = get_db_connection()  
        with connection.cursor(buffered=True) as cursor:
            alldata = """
            WITH LatestData AS (
    SELECT dc.Device_id, 
           dc.timestamp,
           ROW_NUMBER() OVER (PARTITION BY dc.Device_id ORDER BY dc.timestamp DESC) AS rn
    FROM dc_data dc
)
SELECT DISTINCT dc.Device_id,
       t_generated.total_generated,
       t_consumed.total_consumed,
       CASE 
           WHEN TIMESTAMPDIFF(HOUR, dc.timestamp, NOW()) <= 1 THEN 'Active'
           ELSE 'Inactive'
       END AS status
FROM LatestData dc
LEFT JOIN ac_data ac ON dc.Device_id = ac.Device_id
LEFT JOIN (
    SELECT device_id, SUM(avg_kwh) AS total_generated 
    FROM dc_kwh 
    GROUP BY device_id
) t_generated ON t_generated.device_id = dc.Device_id
LEFT JOIN (
    SELECT device_id, SUM(avg_kwh) AS total_consumed 
    FROM ac_kwh 
    GROUP BY device_id
) t_consumed ON t_consumed.device_id = dc.Device_id
WHERE dc.rn = 1;

            """
            cursor.execute(alldata)
            alldataprint = cursor.fetchall()
            devicecount="""
                    SELECT count(distinct(Device_id)) from dc_data;

                """
            cursor.execute(devicecount)
            dcdevicecount=cursor.fetchone()[0]
            
               # unit generated
            Generated="""
                    SELECT sum(avg_kwh) from dc_kwh;

                    """
            cursor.execute(Generated)
            dcGenerated=cursor.fetchone()[0]

            # unit consumed
            acconsumed="""
                    SELECT sum(avg_kwh) from ac_kwh;

                    """
            cursor.execute(acconsumed)
            acconsumedunit=cursor.fetchone()[0]

        return render_template('all_devices.html', alldataprint=alldataprint,
                               dcdevicecount=dcdevicecount,acconsumedunit=acconsumedunit
                               ,dcGenerated=dcGenerated)
    
    except Exception as e:
        return str(e), 500

    finally:
        if connection:
            connection.close() 
            
###############################################################################################################
@app.route('/create_new_user', methods=['POST'])
def create_new_user():
    connection = None
    cursor = None
    try:
        data = request.form
        required_fields = ['u_firstname', 'u_lastname',
                           'u_email', 'u_password','user_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        connection = get_db_connection()
        if connection is None:
            return jsonify({'message': 'Database connection error'}), 500
        cursor = connection.cursor(buffered=True)
        query_check_email = 'SELECT * FROM sa_users WHERE u_email = %s'
        email = data['u_email']
        cursor.execute(query_check_email, (email,))
        user_email = cursor.fetchone()
        if user_email:
            return jsonify({'message': 'User already exists'}), 200
        query_count_users = "SELECT max(u_id) FROM sa_users"
        cursor.execute(query_count_users)
        count_company_id = cursor.fetchone()
        count = count_company_id[0] if count_company_id[0] else 0
        company_id = int(count) + 1
        
        insert_query = """
            INSERT INTO sa_users
            (u_firstname, u_lastname, u_email,
             u_password, user_type, company_id,u_status,u_created_at,admin_id,cmd_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        u_firstname = data["u_firstname"]
        u_lastname = data["u_lastname"]
        u_email = data['u_email']
        u_password = data['u_password']
        user_type=data['user_type']
        u_status='Active'
        u_created_at = datetime.now()
        admin_id=1
        cmd_status=1
        values = (u_firstname, u_lastname, u_email,
                  u_password, user_type, company_id,u_status,u_created_at,admin_id,cmd_status)
        cursor.execute(insert_query, values)
        connection.commit()
        cursor.close()
        return jsonify({'message': 'User created successfully'}), 200

    except Exception as e:
        print(f"Error in adding user: {e}")
        return "An error occurred during processing. Please try again later.", 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
########################################################################################################
# bar graph for dc kwh
@app.route('/dckwh_graph')
def dckwh_graph():
    robot_id = request.args.get('robot_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not robot_id:
        return jsonify({'message': 'Missing robot_id parameter'}), 400

    if start_date and end_date:
    #     try:
    #         # start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    #         # end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    #     except ValueError:
    #         return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400

        query = """
            select start_hour as start_time,avg_kwh from dc_kwh where Device_id=%s and start_hour>=%s and end_hour<=%s order by start_hour asc;
        """
        query_params = (robot_id, start_date, end_date)
    else:
        seven_days_ago = (datetime.now() - timedelta(days=2)
                          ).strftime('%Y-%m-%d')
        query = """
                select start_hour as start_time,avg_kwh from dc_kwh where Device_id=%s and start_hour>=%s order by start_hour asc;

        """
        query_params = (robot_id, seven_days_ago)


    graph_data = []
    try:
        connection = get_db_connection()  
        with connection.cursor(buffered=True) as cursor:
            cursor.execute(query, query_params)
            dc_avg_kwh = cursor.fetchall()

        
            graph_data = [
                {
                    "date": start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    "dc_avg": dc_avg
                }
                for start_time,dc_avg in dc_avg_kwh
            ]

                
    except Error as db_err:
        print(f"Database error: {db_err}")
        return jsonify({'message': 'Database error occurred. Please try again later.'}), 500
    except Exception as e:
        print(f"Error fetching graph data: {e}")
        return jsonify({'message': 'Error fetching graph data. Please try again later.'}), 500
    finally:
        if connection.is_connected():
            connection.close()
    return jsonify(graph_data)
###################################################################################################################
#OTA 
@app.route('/ota/<device>')
def ota_page(device):
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'message': 'Database connection failed'}), 500
        with connection.cursor(buffered=True) as cursor:
            query = "SELECT mac_address FROM dc_data WHERE Device_id = %s order by timestamp desc limit 1"
            cursor.execute(query, (device,))
            mac_id = cursor.fetchone()[0]
            return render_template('ota.html',mac_id=mac_id) 
    except Exception as e:
        print(f"Error during ota process: {e}")
        return "An error occurred during login. Please try again later.", 500
    finally:
        if connection:
            connection.close()  
################################################################################################################
# Upload Bin file for OTA
@app.route('/upload/<mac_id>', methods=['POST'])
def upload(mac_id):
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'message': 'Database connection failed'}), 500

        with connection.cursor(buffered=True) as cursor:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'message': 'No selected file'}), 400

            if file:
                s3_key = f"{mac_id}"
                s3_client.upload_fileobj(
                    file,
                    BUCKET_NAME,
                    s3_key
                )
                s3_url = f"https://{BUCKET_NAME}.s3.{region_name}.amazonaws.com/{s3_key}"
                
        return jsonify({'message': 'File uploaded successfully'}), 200

    except Exception as e:
        print(f"Error during upload: {e}")
        return "An error occurred during login. Please try again later.", 500
    finally:
        if connection:
            connection.close()
#########################################################################################################

######################################################################################
# bar graph for ac kwh
@app.route('/ackwh_graph')
def ackwh_graph():
    robot_id = request.args.get('robot_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not robot_id:
        return jsonify({'message': 'Missing robot_id parameter'}), 400

    if start_date and end_date:
    #     try:
    #         # start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    #         # end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    #     except ValueError:
    #         return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400

        query = """
            select start_hour as start_time,avg_kwh from ac_kwh where Device_id=%s and start_hour>=%s and end_hour<=%s order by start_hour asc;
        """
        query_params = (robot_id, start_date, end_date)
    else:
        seven_days_ago = (datetime.now() - timedelta(days=2)
                          ).strftime('%Y-%m-%d')
        query = """
                select start_hour as start_time,avg_kwh from ac_kwh where Device_id=%s and start_hour>=%s order by start_hour asc;

        """
        query_params = (robot_id, seven_days_ago)


    graph_data = []
    try:
        connection = get_db_connection()  
        with connection.cursor(buffered=True) as cursor:
            cursor.execute(query, query_params)
            ac_avg_kwh = cursor.fetchall()

           
            graph_data = [
                {
                    "date": start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    "dc_avg": dc_avg
                }
                for start_time,dc_avg in ac_avg_kwh
            ]

        
                
    except Error as db_err:
        print(f"Database error: {db_err}")
        return jsonify({'message': 'Database error occurred. Please try again later.'}), 500
    except Exception as e:
        print(f"Error fetching graph data: {e}")
        return jsonify({'message': 'Error fetching graph data. Please try again later.'}), 500
    finally:
        if connection.is_connected():
            connection.close()
    return jsonify(graph_data)
########################################################################################################
# Summary page
@app.route('/summary/<device>')
def summary(device):
    try:
        with get_db_connection() as connection:
            with connection.cursor(buffered=True) as cursor:
                # Fetch DC data
                current_query = """
                SELECT TRUNCATE(Dc_Current, 5) AS Current, timestamp,Dc_Power, Temperature, 
                TRUNCATE(Dc_Voltage, 5) AS Voltage,Device_id,panel_voltage,panel_current,Panel_Power 
                FROM dc_data WHERE Device_id = %s ORDER BY timestamp DESC LIMIT 1"""
                cursor.execute(current_query, (device,))
                currentdata = cursor.fetchone()
                #DC KWH 1 hour
                dc_total_kwh_query = """
                SELECT 
                    * FROM dc_kwh where Device_id = %s
                ORDER BY start_hour DESC
                LIMIT 1
                """
                # dc_total_kwh_query = """
                # SELECT 
                # CAST(AVG(Dc_KWH) AS DECIMAL(10, 5)) AS avg_kWh,
                # DATE_FORMAT(CONVERT_TZ(NOW() - INTERVAL 1 HOUR, 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') AS start_time,
                # DATE_FORMAT(CONVERT_TZ(NOW(), 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') AS end_time
                # FROM dc_data 
                # WHERE Device_id = %s
                # AND timestamp >= DATE_FORMAT(CONVERT_TZ(NOW() - INTERVAL 1 HOUR, 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') 
                # AND timestamp < DATE_FORMAT(CONVERT_TZ(NOW(), 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00')
                # """
                cursor.execute(dc_total_kwh_query, (device,))
                dc_kwh = cursor.fetchone()

                today_date = date.today()
                
                #DC KWH 24-hours
                # dc_total_kwh_query = """
                # SELECT 
                # CAST(SUM(hourly.avg_kWh) AS DECIMAL(10, 5)) AS total_avg_kWh_24h
                # FROM (
                #     SELECT 
                #         DATE_FORMAT(timestamp, '%Y-%m-%D %H:00:00') AS hour,
                #         AVG(Dc_KWH) AS avg_kWh
                #     FROM dc_data WHERE Device_id = %s AND timestamp >= %s GROUP BY hour
                # ) AS hourly
                # """
                # cursor.execute(dc_total_kwh_query, (device,today_date))
                # dc_total_kwh = cursor.fetchone()
                # dc_total_kwh_value = dc_total_kwh[0] if dc_total_kwh and dc_total_kwh[0] is not None else 0

                #DC Units
                # dc_total_unit_query = """
                # SELECT CAST(SUM(hourly.avg_kWh) AS UNSIGNED) AS total_avg_kWh_24h
                # FROM (SELECT DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') AS hour,
                # AVG(Dc_KWH) AS avg_kWh FROM dc_data WHERE Device_id = %s GROUP BY hour
                # ) AS hourly """
                # dc_total_unit_query = """
                # SELECT CAST(SUM(avg_kWh) AS UNSIGNED) AS total_avg_kWh_24h
                # FROM dc_kwh where device_id= %s"""
                dc_total_unit_query = """
                SELECT SUM(avg_kWh) AS total_avg_kWh_24h
                FROM dc_kwh where device_id= %s"""
                cursor.execute(dc_total_unit_query, (device,))
                dc_total_unit = cursor.fetchone()

                # Fetch AC data
                Accurrent_query = """
                SELECT TRUNCATE(Current, 5) AS Current, timestamp,Power, Temperature, TRUNCATE(Voltage, 5) AS Voltage, 
                Device_id FROM ac_data 
                WHERE Device_id = %s ORDER BY timestamp DESC LIMIT 1"""
                cursor.execute(Accurrent_query, (device,))
                Accurrentdata = cursor.fetchone()
                try:
                    if Accurrentdata and currentdata and currentdata[2] != 0:
                        value = round(Accurrentdata[2] / currentdata[2], 4)
                    else:
                        value = "N/A"
                except ZeroDivisionError:
                    value = "N/A"     

                #AC KWH 1 hour
                ac_total_kwh_query = """
                SELECT 
                    * FROM ac_kwh where Device_id = %s
                ORDER BY start_hour DESC
                LIMIT 1
                """
                cursor.execute(ac_total_kwh_query, (device,))
                ac_total_kwh = cursor.fetchone()

                today_date = date.today()
                
                #AC KWH 24-hours
                # total_kwh_query = """
                # SELECT CAST(SUM(hourly.avg_kWh) AS DECIMAL(10, 5)) AS total_avg_kWh_24h
                # FROM (SELECT DATE_FORMAT(timestamp, '%Y-%m-%D %H:00:00') AS hour,
                # AVG(kWh_Consumed) AS avg_kWh FROM ac_data WHERE Device_id = %s AND timestamp >= %s GROUP BY hour
                # ) AS hourly
                # """
                # cursor.execute(total_kwh_query, (device,today_date))
                # total_kwh = cursor.fetchone()

                # total_kwh_value = total_kwh[0] if total_kwh and total_kwh[0] is not None else 0
                
                # AC Units Calculation
                # total_unit_query = """
                # SELECT CAST(SUM(hourly.avg_kWh) AS UNSIGNED) AS total_avg_kWh_24h
                # FROM (SELECT DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') AS hour,
                # AVG(kWh_Consumed) AS avg_kWh FROM ac_data WHERE Device_id = %s 
                # GROUP BY hour) AS hourly """
                # total_unit_query = """
                # SELECT CAST(SUM(avg_kWh) AS UNSIGNED) AS total_avg_kWh_24h
                # FROM ac_kwh where Device_id = %s """
                total_unit_query = """
                SELECT SUM(avg_kWh) AS total_avg_kWh_24h
                FROM ac_kwh where Device_id = %s """
                cursor.execute(total_unit_query, (device,))
                total_unit = cursor.fetchone()

                inst_date="""
                select * from dc_data where Device_id = %s order by timestamp  asc
              """
                cursor.execute(inst_date,(device,))
                man_date=cursor.fetchone()
   # Fetch DC data
                alldata = "SELECT * FROM dc_data WHERE Device_id = %s ORDER BY timestamp DESC LIMIT 700"
                cursor.execute(alldata,(device,))
                alldataprint = cursor.fetchall()
                # Fetch AC data
                Acdata = "SELECT * FROM ac_data WHERE Device_id = %s order by timestamp desc LIMIT 700"
                cursor.execute(Acdata,(device,))
                allAcdataprint = cursor.fetchall()
                # Fetch DC KWH data
                dc_kwh_data = "select * from dc_kwh WHERE Device_id = %s order by start_hour desc LIMIT 700"
                cursor.execute(dc_kwh_data,(device,))
                dc_kwh_dataprint = cursor.fetchall()
                # Fetch AC KWH data
                ac_kwh_data = "SELECT * FROM ac_kwh WHERE Device_id = %s order by start_hour desc LIMIT 700"
                cursor.execute(ac_kwh_data,(device,))
                ac_kwh_dataprint = cursor.fetchall()

                # Determine Device Type and Battery Voltage Range
                device2 = int(device)
                if 1000 <= device2 < 2000: #12V LEAD Battery
                    battery_percentage = ((currentdata[4]-10.5)/(13.8-10.5))*100
                elif 2000 <= device2 < 3000: #24V LEAD Battery
                    battery_percentage = ((currentdata[4]-21)/(27.6-21))*100
                elif 3000 <= device2 < 4000: #12V Lithium Battery
                    battery_percentage = ((currentdata[4]-10.5)/(14.6-10.5))*100
                elif 4000 <= device2 < 5000: #24V Lithium Battery
                    battery_percentage = math.trunc(((currentdata[4]-19.8)/(26-19.8))*100)
                elif 5000 <= device2 < 6000:  # 48V Lead Battery
                    battery_percentage = math.trunc(((currentdata[4] - 42) / (58 - 42)) * 100)
                else:  # 48V Lithium Battery
                    battery_percentage = math.trunc(((currentdata[4] - 40) / (54.6 - 40)) * 100)
                battery_percentage = max(0, min(100, battery_percentage))


                
                return render_template(
                    'summary.html',
                    battery_chargefull=int(battery_percentage),
                    Dccurrent=currentdata,
                    Accurrent=Accurrentdata,
                    dc_kwh=dc_kwh,
                    dc_total_unit=dc_total_unit,
                    ac_total_kwh=ac_total_kwh,
                    total_unit=total_unit,today_date=today_date,man_date=man_date,value=value,
                    alldataprint=alldataprint,allAcdataprint=allAcdataprint,dc_kwh_dataprint=dc_kwh_dataprint,
                    ac_kwh_dataprint=ac_kwh_dataprint,deviceid=device
                )    
    except Exception as e:
                 return str(e), 500
########################################################################################################
# Summary page
@app.route('/client_summary/<device>')
def client_summary(device):
    try:
        with get_db_connection() as connection:
            with connection.cursor(buffered=True) as cursor:
                # Fetch DC data
                current_query = """
                SELECT TRUNCATE(Dc_Current, 5) AS Current, timestamp,Dc_Power, Temperature, 
                TRUNCATE(Dc_Voltage, 5) AS Voltage,Device_id,panel_voltage,panel_current,Panel_Power 
                FROM dc_data WHERE Device_id = %s ORDER BY timestamp DESC LIMIT 1"""
                cursor.execute(current_query, (device,))
                currentdata = cursor.fetchone()
                #DC KWH 1 hour
                dc_total_kwh_query = """
                SELECT 
                    * FROM dc_kwh where Device_id = %s
                ORDER BY start_hour DESC
                LIMIT 1
                """
                # dc_total_kwh_query = """
                # SELECT 
                # CAST(AVG(Dc_KWH) AS DECIMAL(10, 5)) AS avg_kWh,
                # DATE_FORMAT(CONVERT_TZ(NOW() - INTERVAL 1 HOUR, 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') AS start_time,
                # DATE_FORMAT(CONVERT_TZ(NOW(), 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') AS end_time
                # FROM dc_data 
                # WHERE Device_id = %s
                # AND timestamp >= DATE_FORMAT(CONVERT_TZ(NOW() - INTERVAL 1 HOUR, 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00') 
                # AND timestamp < DATE_FORMAT(CONVERT_TZ(NOW(), 'UTC', 'Asia/Kolkata'), '%Y-%m-%d %H:00:00')
                # """
                cursor.execute(dc_total_kwh_query, (device,))
                dc_kwh = cursor.fetchone()

                today_date = date.today()
                
                #DC KWH 24-hours
                # dc_total_kwh_query = """
                # SELECT 
                # CAST(SUM(hourly.avg_kWh) AS DECIMAL(10, 5)) AS total_avg_kWh_24h
                # FROM (
                #     SELECT 
                #         DATE_FORMAT(timestamp, '%Y-%m-%D %H:00:00') AS hour,
                #         AVG(Dc_KWH) AS avg_kWh
                #     FROM dc_data WHERE Device_id = %s AND timestamp >= %s GROUP BY hour
                # ) AS hourly
                # """
                # cursor.execute(dc_total_kwh_query, (device,today_date))
                # dc_total_kwh = cursor.fetchone()
                # dc_total_kwh_value = dc_total_kwh[0] if dc_total_kwh and dc_total_kwh[0] is not None else 0

                #DC Units
                # dc_total_unit_query = """
                # SELECT CAST(SUM(hourly.avg_kWh) AS UNSIGNED) AS total_avg_kWh_24h
                # FROM (SELECT DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') AS hour,
                # AVG(Dc_KWH) AS avg_kWh FROM dc_data WHERE Device_id = %s GROUP BY hour
                # ) AS hourly """
                # dc_total_unit_query = """
                # SELECT CAST(SUM(avg_kWh) AS UNSIGNED) AS total_avg_kWh_24h
                # FROM dc_kwh where device_id= %s"""
                dc_total_unit_query = """
                SELECT SUM(avg_kWh) AS total_avg_kWh_24h
                FROM dc_kwh where device_id= %s"""
                cursor.execute(dc_total_unit_query, (device,))
                dc_total_unit = cursor.fetchone()

                # Fetch AC data
                Accurrent_query = """
                SELECT TRUNCATE(Current, 5) AS Current, timestamp,Power, Temperature, TRUNCATE(Voltage, 5) AS Voltage, 
                Device_id FROM ac_data 
                WHERE Device_id = %s ORDER BY timestamp DESC LIMIT 1"""
                cursor.execute(Accurrent_query, (device,))
                Accurrentdata = cursor.fetchone()
                try:
                    if Accurrentdata and currentdata and currentdata[2] != 0:
                        value = round(Accurrentdata[2] / currentdata[2], 4)
                    else:
                        value = "N/A"
                except ZeroDivisionError:
                    value = "N/A"     

                #AC KWH 1 hour
                ac_total_kwh_query = """
                SELECT 
                    * FROM ac_kwh where Device_id = %s
                ORDER BY start_hour DESC
                LIMIT 1
                """
                cursor.execute(ac_total_kwh_query, (device,))
                ac_total_kwh = cursor.fetchone()

                today_date = date.today()
                
                #AC KWH 24-hours
                # total_kwh_query = """
                # SELECT CAST(SUM(hourly.avg_kWh) AS DECIMAL(10, 5)) AS total_avg_kWh_24h
                # FROM (SELECT DATE_FORMAT(timestamp, '%Y-%m-%D %H:00:00') AS hour,
                # AVG(kWh_Consumed) AS avg_kWh FROM ac_data WHERE Device_id = %s AND timestamp >= %s GROUP BY hour
                # ) AS hourly
                # """
                # cursor.execute(total_kwh_query, (device,today_date))
                # total_kwh = cursor.fetchone()

                # total_kwh_value = total_kwh[0] if total_kwh and total_kwh[0] is not None else 0
                
                # AC Units Calculation
                # total_unit_query = """
                # SELECT CAST(SUM(hourly.avg_kWh) AS UNSIGNED) AS total_avg_kWh_24h
                # FROM (SELECT DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') AS hour,
                # AVG(kWh_Consumed) AS avg_kWh FROM ac_data WHERE Device_id = %s 
                # GROUP BY hour) AS hourly """
                # total_unit_query = """
                # SELECT CAST(SUM(avg_kWh) AS UNSIGNED) AS total_avg_kWh_24h
                # FROM ac_kwh where Device_id = %s """
                total_unit_query = """
                SELECT SUM(avg_kWh) AS total_avg_kWh_24h
                FROM ac_kwh where Device_id = %s """
                cursor.execute(total_unit_query, (device,))
                total_unit = cursor.fetchone()

                inst_date="""
                select * from dc_data where Device_id = %s order by timestamp  asc
              """
                cursor.execute(inst_date,(device,))
                man_date=cursor.fetchone()
   # Fetch DC data
                alldata = "SELECT * FROM dc_data WHERE Device_id = %s ORDER BY timestamp DESC LIMIT 700"
                cursor.execute(alldata,(device,))
                alldataprint = cursor.fetchall()
                # Fetch AC data
                Acdata = "SELECT * FROM ac_data WHERE Device_id = %s order by timestamp desc LIMIT 700"
                cursor.execute(Acdata,(device,))
                allAcdataprint = cursor.fetchall()
                # Fetch DC KWH data
                dc_kwh_data = "select * from dc_kwh WHERE Device_id = %s order by start_hour desc LIMIT 700"
                cursor.execute(dc_kwh_data,(device,))
                dc_kwh_dataprint = cursor.fetchall()
                # Fetch AC KWH data
                ac_kwh_data = "SELECT * FROM ac_kwh WHERE Device_id = %s order by start_hour desc LIMIT 700"
                cursor.execute(ac_kwh_data,(device,))
                ac_kwh_dataprint = cursor.fetchall()

                # Determine Device Type and Battery Voltage Range
                device2 = int(device)
                if 1000 <= device2 < 2000: #12V LEAD Battery
                    battery_percentage = ((currentdata[4]-10.5)/(13.8-10.5))*100
                elif 2000 <= device2 < 3000: #24V LEAD Battery
                    battery_percentage = ((currentdata[4]-21)/(27.6-21))*100
                elif 3000 <= device2 < 4000: #12V Lithium Battery
                    battery_percentage = ((currentdata[4]-10.5)/(14.6-10.5))*100
                elif 4000 <= device2 < 5000: #24V Lithium Battery
                    battery_percentage = math.trunc(((currentdata[4]-19.8)/(26-19.8))*100)
                elif 5000 <= device2 < 6000:  # 48V Lead Battery
                    battery_percentage = math.trunc(((currentdata[4] - 42) / (58 - 42)) * 100)
                else:  # 48V Lithium Battery
                    battery_percentage = math.trunc(((currentdata[4] - 40) / (54.6 - 40)) * 100)
                battery_percentage = max(0, min(100, battery_percentage))


                
                return render_template(
                    'client/client_summary.html',
                    battery_chargefull=int(battery_percentage),
                    Dccurrent=currentdata,
                    Accurrent=Accurrentdata,
                    dc_kwh=dc_kwh,
                    dc_total_unit=dc_total_unit,
                    ac_total_kwh=ac_total_kwh,
                    total_unit=total_unit,today_date=today_date,man_date=man_date,value=value,
                    alldataprint=alldataprint,allAcdataprint=allAcdataprint,dc_kwh_dataprint=dc_kwh_dataprint,
                    ac_kwh_dataprint=ac_kwh_dataprint
                )    
    except Exception as e:
                 return str(e), 500
########################################################################################################
# create new user and admin
@app.route('/user_form', methods=['GET'])
def user_form():
    try:
        return render_template('create_users.html')
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred while fetching graph data."}), 500

########################################################################################################

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

                # Fetch DC KWH data
                dc_kwh_data = "select * from dc_kwh order by start_hour desc LIMIT 700"
                cursor.execute(dc_kwh_data)
                dc_kwh_dataprint = cursor.fetchall()
                # Fetch AC KWH data
                ac_kwh_data = "SELECT * FROM ac_kwh order by start_hour desc LIMIT 700"
                cursor.execute(ac_kwh_data)
                ac_kwh_dataprint = cursor.fetchall()

        return render_template('table.html', alldataprint=alldataprint, Acalldataprint=allAcdataprint
                               ,dc_kwh_dataprint=dc_kwh_dataprint,ac_kwh_dataprint=ac_kwh_dataprint)

    except Exception as e:
        return "An error occurred while retrieving the data. Please try again later.", 500
########################################################################################################
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
########################################################################################################
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
