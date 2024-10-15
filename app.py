from flask import render_template, Flask, redirect, request, url_for
import boto3
import os
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from dotenv import load_dotenv
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Key

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Initialize the DynamoDB client using environment variables
dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id=os.getenv('aws_access_key_id'),
    aws_secret_access_key=os.getenv('aws_secret'),
    region_name=os.getenv('region_name')
)

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
    table_name = 'Wattmeter' 
    table = dynamodb.Table(table_name)

    try:
        # Fetch data from DynamoDB
        response = table.scan()
        items = response['Items']

        # Sort items by timestamp in descending order
        sorted_items = sorted(items, key=lambda x: x.get('timestamp', 0), reverse=True)

        # Render the data in your HTML template
        return render_template('table.html', items=sorted_items)
    
    except (NoCredentialsError, PartialCredentialsError) as e:
        print(f"Credentials error: {e}")
        return "Could not access DynamoDB. Please check your AWS credentials.", 500
    except Exception as e:
        print(f"Error fetching data from DynamoDB: {e}")
        return "An error occurred while fetching data. Please try again later.", 500
# 

@app.route('/databyid')
def databyid():
    print()
    table_name = 'Wattmeter' 
    table = dynamodb.Table(table_name)

    try:
        # Fetch data from DynamoDB where Device_id = id
        response = table.scan(
            FilterExpression=Key('Device_id').eq('1')  # Adjusted to your specific device_id
        )
        items = response['Items']

        # Sort items by timestamp in descending order
        sorted_items = sorted(items, key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Render the data in your HTML template
        return render_template('watt.html', items=sorted_items)
    
    except (NoCredentialsError, PartialCredentialsError) as e:
        print(f"Credentials error: {e}")
        return "Could not access DynamoDB. Please check your AWS credentials.", 500
    except Exception as e:
        print(f"Error fetching data from DynamoDB: {e}")
        return "An error occurred while fetching data. Please try again later.", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
