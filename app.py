from flask import render_template, Flask, redirect, request, url_for
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
    return render_template('watt.html')

@app.route('/data')
def data_table():    
    try:
        
        # Render the data in your HTML template
        return render_template('table.html')

    except Exception as e:
        return str(e), 500

@app.route('/databyid')
def databyid():
    try:
        
        return render_template('watt.html', items=sorted_items)
    
    except Exception as e:
        print(f"Error: {e}")
        return "An error occurred while fetching data. Please try again later.", 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
