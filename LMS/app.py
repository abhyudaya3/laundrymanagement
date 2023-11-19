# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from flask_mysqldb import MySQL
from pymongo import MongoClient
from flask_pymongo import PyMongo
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
from passlib.hash import sha256_crypt
import uuid
from uuid import UUID


app = Flask(__name__)
app.secret_key = '\xfd{H\xe5<\x95\xf9\xe3\x96.5\xd1\x01O<!\xd5\xa2\xa0\x9fR"\xa1\xa8'

# MongoDB connection
#mongodb+srv://abhyudaya:<password>@abhyudayamongo.lijpsor.mongodb.net/?retryWrites=true&w=majority
#client = MongoClient("mongodb://localhost:27017")  # Replace with your MongoDB URI
client = MongoClient("mongodb://localhost:27017")
db = client["contact_app"]  # Replace with your database name
collection = db["contacts"]
# Define the MongoDB collection for prices
prices_collection = db.prices




# Check if prices are already in the database, if not, add them
if prices_collection.count_documents({}) == 0:
    prices_collection.insert_one({
        'shirt': 5,
        'jeans': 8,
        'pant': 7,
        'blanket': 10,
        'tshirt': 4
    })

# Fetch prices from the MongoDB collection
prices = prices_collection.find_one()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        contact = {
            'name': request.form['name'],
            'email': request.form['email'],
            'message': request.form['message']
        }
        collection.insert_one(contact)
        return redirect(url_for('index'))
    return render_template('contact.html')

@app.route('/displaycontacts')
def display_contacts():
    # Retrieve contact data from MongoDB
    contact_collection = db.contacts
    contacts = contact_collection.find()
    return render_template('displaycontact.html', contacts=contacts)

@app.route('/update/<string:contact_id>', methods=['GET', 'POST'])
def update_contact(contact_id):
    contact_collection = db.contacts
    contact = contact_collection.find_one({'_id': ObjectId(contact_id)})
    
    if request.method == 'POST':
        new_name = request.form.get('name')
        new_email = request.form.get('email')
        new_message = request.form.get('message')
        
        # Update the contact entry in the database
        contact_collection.update_one(
            {'_id': ObjectId(contact_id)},
            {'$set': {'name': new_name, 'email': new_email, 'message': new_message}}
        )
        
        return redirect('/displaycontacts')
    
    return render_template('updatecontact.html', contact=contact)

@app.route('/deletecontact/<contact_id>', methods=['POST'])
def delete_contact(contact_id):
    # Convert contact_id to ObjectId
    contact_id = ObjectId(contact_id)
    print(contact_id, '-<')
    # Remove the contact from MongoDB
    contact_collection = db.contacts
    contact_collection.delete_one({'_id': contact_id})

    return redirect(url_for('display_contacts'))

@app.route('/prices')
def price_list():
    prices = prices_collection.find_one()
    return render_template('price_list.html', prices=prices)



@app.route('/order_form')
def laundry():
    return render_template('laundry.html', prices=prices)

@app.route('/submit_order', methods=['POST'])
def submit_order():
    if request.method == 'POST':
        name = request.form['name']
        roll_no = request.form['roll_no']
        mobile = request.form['mobile']
        email = request.form['email']
        shirt_quantity = int(request.form['shirt_quantity'])
        jeans_quantity = int(request.form['jeans_quantity'])
        pant_quantity = int(request.form['pant_quantity'])
        blanket_quantity = int(request.form['blanket_quantity'])
        tshirt_quantity = int(request.form['tshirt_quantity'])

        # Calculate total prices
        total_price = (
            shirt_quantity * prices['shirt'] +
            jeans_quantity * prices['jeans'] +
            pant_quantity * prices['pant'] +
            blanket_quantity * prices['blanket'] +
            tshirt_quantity * prices['tshirt']
        )

        # Generate a reference ID
        reference_id = str(uuid.uuid4())[:8].upper() # Use the first 8 characters of the UUID

        # Store the order in the MongoDB collection for requests
        requests_collection = db.request_lms
        requests_collection.insert_one({
            'reference_id': reference_id,
            'name': name,
            'roll_no': roll_no,
            'mobile': mobile,
            'email': email,
            'shirt_quantity': shirt_quantity,
            'jeans_quantity': jeans_quantity,
            'pant_quantity': pant_quantity,
            'blanket_quantity': blanket_quantity,
            'tshirt_quantity': tshirt_quantity,
            'total_price': total_price
        })

        flash(f'Order placed successfully! Your reference ID is {reference_id}. Total Price: Rs {total_price}', 'success')
        return redirect(url_for('confirmation', reference_id=reference_id, total_price=total_price))

@app.route('/confirmation/<reference_id>/<total_price>')
def confirmation(reference_id, total_price):
    return render_template('confirmation.html', reference_id=reference_id, total_price=total_price)



# Define the MongoDB collection for user registration
register_collection = db.register

@app.route('/sign_form')
def signup():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup_post():
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        hostel = request.form.get('hostel', '')
        roll = request.form.get('roll', '')
        email = request.form['email']
        gender = request.form['gender']
        username = request.form['username']
        password = sha256_crypt.encrypt(request.form['password'])
        user_type = request.form['user_type']

        # Check if the username is already taken
        if register_collection.find_one({'username': username}):
            flash('Username is already taken. Please choose another.', 'danger')
            return redirect(url_for('signup'))

        # Insert the user data into the MongoDB collection
        register_collection.insert_one({
            'name': name,
            'mobile': mobile,
            'hostel': hostel,
            'roll': roll,
            'email': email,
            'gender': gender,
            'username': username,
            'password': password,
            'user_type': user_type
        })

        flash('Signup successful! You can now login.', 'success')
        return redirect(url_for('signup'))
    

@app.route('/log')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        # Check if the username exists in the MongoDB collection
        user_data = register_collection.find_one({'username': username})

        if user_data:
            # Verify the password using passlib
            if sha256_crypt.verify(password_candidate, user_data['password']):
                # Set session variables
                session['user_id'] = str(user_data['_id'])
                session['username'] = user_data['username']
                session['user_type'] = user_data['user_type']

                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))

        flash('Invalid username or password. Please try again.', 'danger')
        return redirect(url_for('login'))

register_collection = db.register
requests_collection = db.request_lms

# Inserting a new document with ObjectId
new_order = {
    '_id': ObjectId(),  # Use ObjectId() to generate a new ObjectId
    # Other fields...
}



requests_collection.insert_one(new_order)

if 'status' not in requests_collection.find_one({}):
    # Add the 'status' field to existing documents with the default value
    requests_collection.update_many({}, {'$set': {'status': 'Order Request Sent'}})

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_type = session['user_type']
        if user_type == 'admin':
            # Fetch all order requests for admin users
            orders_collection = db.request_lms
            orders = list(orders_collection.find())  # Convert cursor to list
            return render_template('dashboard_admin.html', username=session['username'], user_type=user_type, orders=orders)
        else:
            return render_template('dashboard.html', username=session['username'], user_type=user_type)
    else:
        flash('You are not logged in. Please log in first.', 'danger')
        return redirect(url_for('login'))

@app.route('/update_order/<string:reference_id>', methods=['GET', 'POST'])
def update_order(reference_id):
    orders_collection = db.request_lms
    order = orders_collection.find_one({'reference_id': reference_id})

    if request.method == 'POST':
        new_status = request.form['status']

        # Update the status in the database
        orders_collection.update_one({'reference_id': reference_id}, {'$set': {'status': new_status}})
        flash('Order status updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('update_order.html', order=order)

@app.route('/delete_order/<string:reference_id>')
def delete_order(reference_id):
    orders_collection = db.request_lms
    orders_collection.delete_one({'reference_id': reference_id})
    flash('Order deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/check_status', methods=['GET', 'POST'])
def check_status():
    if request.method == 'POST':
        reference_id = request.form['reference_id']
        order = requests_collection.find_one({'reference_id': reference_id})

        if order:
            status = order['status']
            return render_template('check_status.html', status=status)
        else:
            flash('Invalid reference ID. Please try again.', 'danger')

    return render_template('check_status.html', status=None)





if __name__ == '__main__':
    app.run(debug=True)
