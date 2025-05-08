from flask import Flask,flash, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import bcrypt

app = Flask(__name__)
app.secret_key = 'AnaS_05@'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'online_bookstore'

mysql = MySQL(app)

# Sample book data
books = [
    (1, "Book Title 1", "Author 1", 10.99),
    (2, "Book Title 2", "Author 2", 12.99),
    (3, "Book Title 3", "Author 3", 15.99),
]

# Authentication 
# Register User
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                       (username, email, hashed_pw))
        mysql.connection.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# Login User
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            session['user_id'] = user[0]
            session['is_admin'] = user[4]  # Assuming `is_admin` is the 5th column in the `users` table
            return redirect(url_for('index'))
        else:
            return "Invalid login details"
    return render_template('login.html')

# Logout User
@app.route('/logout')
def logout():
    session.clear()  # Clear the session to log the user out
    return redirect(url_for('index'))  # Redirect to the homepage

# Displaying books
# Home Page: Display Books
@app.route('/')
def index():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    return render_template('index.html', books=books)

# Admin Dashboard: Manage Books
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return "Access denied", 403
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    return render_template('admin_dashboard.html', books=books)

#Adding a new book
@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        price = float(request.form['price'])
        stocks = int(request.form['stocks'])
        
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO books (title, author, price, stocks) VALUES (%s, %s, %s, %s)", 
                       (title, author, price, stocks))
        mysql.connection.commit()
        return redirect(url_for('index'))
    return render_template('add_book.html')

# remove book from database
@app.route('/remove_book/<int:book_id>', methods=['POST'])
def remove_book(book_id):
    if not session.get('is_admin'):
        return "Access denied", 403

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM books WHERE id = %s", (book_id,))
    mysql.connection.commit()
    flash('Book deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# Cart Management
@app.route('/cart')
def cart():
    if 'cart' not in session or not session['cart']:
        return render_template('cart.html', cart=[], total=0)

    cursor = mysql.connection.cursor()
    cart_books = []
    total = 0

    for item in session['cart']:
        cursor.execute("SELECT id, title, author, price FROM books WHERE id = %s", (item['book_id'],))
        book = cursor.fetchone()
        if book:
            cart_books.append({
                'book_id': book[0],
                'book_title': book[1],
                'author': book[2],
                'price': book[3],
                'quantity': item['quantity']
            })
            total += book[3] * item['quantity']

    return render_template('cart.html', cart=cart_books, total=total)

# Add to Cart 
@app.route('/add_to_cart/<int:book_id>', methods=['POST'])
def add_to_cart(book_id):
    quantity = int(request.form.get('quantity', 1))
    cursor = mysql.connection.cursor()
    
    # Fetch the current stock for the book
    cursor.execute("SELECT stocks FROM books WHERE id = %s", (book_id,))
    stock = cursor.fetchone()[0]
    
    # Check if there is enough stock
    if quantity > stock:
        return "Not enough stock available", 400
    
    # Update the session cart
    if 'cart' not in session:
        session['cart'] = []
    
    for item in session['cart']:
        if item['book_id'] == book_id:
            if item['quantity'] + quantity > stock:
                return "Not enough stock available", 400
            item['quantity'] += quantity
            break
    else:
        session['cart'].append({'book_id': book_id, 'quantity': quantity})
    
    # Decrement the stock in the database
    new_stock = stock - quantity
    cursor.execute("UPDATE books SET stocks = %s WHERE id = %s", (new_stock, book_id))
    mysql.connection.commit()
    
    flash('Book added to cart and stock updated successfully!', 'success')
    return redirect(url_for('index'))

# Remove from Cart
@app.route('/remove_from_cart/<int:book_id>', methods=['GET', 'POST'])
def remove_from_cart(book_id):
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['book_id'] != book_id]
    flash('Book removed from cart successfully!', 'success')
    return redirect(url_for('cart'))

@app.route('/update_stock/<int:book_id>', methods=['POST'])
def update_stock(book_id):
    if not session.get('is_admin'):
        return "Access denied", 403

    new_stock = int(request.form['new_stock'])
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE books SET stocks = %s WHERE id = %s", (new_stock, book_id))
    mysql.connection.commit()
    flash('Stock updated successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


# Checkout & Place Order
@app.route('/order', methods=['POST'])
def place_order():
    user_id = session['user_id']
    cart = session.get('cart', [])
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO orders(user_id) VALUES (%s)", (user_id,))
    order_id = cursor.lastrowid
    
    for item in cart:
        cursor.execute("INSERT INTO order_items(order_id, book_id, quantity) VALUES (%s, %s, %s)", 
                       (order_id, item['book_id'], item['quantity']))
    
    mysql.connection.commit()
    session['cart'] = []
    return redirect(url_for('thank_you'))


# Thank You Page
@app.route('/thank_you')
def thank_you():
    return "Thank you for your order!"


if __name__ == '__main__':
    app.run(debug=True)
