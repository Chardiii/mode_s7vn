from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from flask_bcrypt import Bcrypt
from flask_session import Session
from datetime import timedelta

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Secret key + session settings
app.secret_key = "mode_s7vn_secret"
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)  # Auto-logout after 30 mins
Session(app)

# Database connection
db = mysql.connector.connect(
    host="localhost",      # XAMPP MySQL default
    user="root",           # default XAMPP user
    password="",           # usually blank in XAMPP
    database="modes7vn"    # make sure this DB exists in SQLyog
)
cursor = db.cursor(dictionary=True)

# ---------------- Home ----------------
@app.route('/')
def home():
    return "Welcome to Mode S7vn E-commerce!"

# ---------------- Buyer Signup ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Confirm password match
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('signup'))

        # Check if email already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for('login'))

        # Hash password and insert new user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor.execute("INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                       (username, email, hashed_password, "buyer"))
        db.commit()

        # Auto-login after signup
        session['user_id'] = cursor.lastrowid
        session['username'] = username
        session['role'] = "buyer"
        flash("Account created successfully! Welcome to Mode S7vn.", "success")
        return redirect(url_for('buyer_dashboard'))

    return render_template('signup.html')

# ---------------- Buyer Login ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE email = %s AND role = 'buyer'", (email,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user['password'], password):
            session.permanent = True  # enable session lifetime
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash("Login successful!", "success")
            return redirect(url_for('buyer_dashboard'))
        else:
            flash("Invalid credentials. Try again.", "danger")

    return render_template('login.html')

# ---------------- Buyer Dashboard ----------------
@app.route('/buyer/dashboard')
def buyer_dashboard():
    if 'user_id' not in session or session['role'] != 'buyer':
        return redirect(url_for('login'))
    return f"Welcome Buyer, {session['username']}!"

# ---------------- Logout ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/products')
def products():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    items = cursor.fetchall()
    cursor.close()
    return render_template('products.html', products=items)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    return render_template('product_detail.html', product=product)
# -------------------- CART SYSTEM --------------------

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'buyer_id' not in session:
        flash("Please login first to add items to your cart.", "danger")
        return redirect(url_for('login'))

    buyer_id = session['buyer_id']
    quantity = int(request.form.get("quantity", 1))

    cursor = db.cursor()
    # Check if product already exists in cart
    cursor.execute("SELECT * FROM cart WHERE buyer_id=%s AND product_id=%s", (buyer_id, product_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("UPDATE cart SET quantity = quantity + %s WHERE buyer_id=%s AND product_id=%s",
                       (quantity, buyer_id, product_id))
    else:
        cursor.execute("INSERT INTO cart (buyer_id, product_id, quantity) VALUES (%s, %s, %s)",
                       (buyer_id, product_id, quantity))

    db.commit()
    cursor.close()
    flash("Product added to cart!", "success")
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    if 'buyer_id' not in session:
        flash("Please login first to view your cart.", "danger")
        return redirect(url_for('login'))

    buyer_id = session['buyer_id']
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.cart_id, p.name, p.price, c.quantity, (p.price * c.quantity) as total
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.buyer_id = %s
    """, (buyer_id,))
    cart_items = cursor.fetchall()
    cursor.close()

    total_amount = sum(item['total'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)

@app.route('/remove_from_cart/<int:cart_id>')
def remove_from_cart(cart_id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM cart WHERE cart_id=%s", (cart_id,))
    db.commit()
    cursor.close()
    flash("Item removed from cart!", "info")
    return redirect(url_for('cart'))

@app.route('/update_cart/<int:cart_id>', methods=['POST'])
def update_cart(cart_id):
    new_quantity = int(request.form.get("quantity", 1))

    cursor = db.cursor()
    if new_quantity > 0:
        cursor.execute("UPDATE cart SET quantity=%s WHERE cart_id=%s", (new_quantity, cart_id))
        flash("Cart updated!", "success")
    else:
        cursor.execute("DELETE FROM cart WHERE cart_id=%s", (cart_id,))
        flash("Item removed from cart!", "info")

    db.commit()
    cursor.close()
    return redirect(url_for('cart'))


if __name__ == '__main__':
    app.run(debug=True)
