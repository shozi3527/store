from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from functools import wraps

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///iphone_store.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ======================== DATABASE MODELS ========================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True, cascade='all, delete-orphan')
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class iPhone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(50), nullable=False)  # iPhone XR, iPhone 11, etc.
    storage = db.Column(db.String(20), nullable=False)  # 64GB, 128GB, 256GB, 512GB
    color = db.Column(db.String(50), nullable=False)  # Space Gray, Gold, etc.
    condition = db.Column(db.String(20), nullable=False)  # New, Refurbished
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cart_items = db.relationship('CartItem', backref='iphone', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='iphone', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'model': self.model,
            'storage': self.storage,
            'color': self.color,
            'condition': self.condition,
            'price': self.price,
            'stock': self.stock,
            'description': self.description,
            'image_url': self.image_url
        }


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    iphone_id = db.Column(db.Integer, db.ForeignKey('i_phone.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Pending')  # Pending, Processing, Shipped, Delivered, Cancelled
    delivery_status = db.Column(db.String(100), default='Not Yet Dispatched')  # Not Yet Dispatched, Dispatched, In Transit, Out for Delivery, Delivered
    tracking_number = db.Column(db.String(100))
    delivery_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    order_items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def generate_order_number(self):
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        self.order_number = f"ORD-{timestamp}-{self.user_id}"


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    iphone_id = db.Column(db.Integer, db.ForeignKey('i_phone.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)


# ======================== LOGIN MANAGER ========================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_id'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# ======================== ROUTES - PUBLIC ========================

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    model_filter = request.args.get('model')
    condition_filter = request.args.get('condition')
    
    query = iPhone.query
    
    if model_filter:
        query = query.filter_by(model=model_filter)
    if condition_filter:
        query = query.filter_by(condition=condition_filter)
    
    iphones = query.paginate(page=page, per_page=12)
    models = db.session.query(iPhone.model).distinct().all()
    
    return render_template('index.html', iphones=iphones, models=models)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    iphone = iPhone.query.get_or_404(product_id)
    return render_template('product_detail.html', iphone=iphone)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([username, email, password, confirm_password]):
            return render_template('register.html', error='All fields are required')

        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')

        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already registered')

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# ======================== ROUTES - USER ACCOUNT ========================

@app.route('/dashboard')
@login_required
def dashboard():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('dashboard.html', orders=orders, user=current_user)


@app.route('/account')
@login_required
def account():
    return render_template('account.html', user=current_user)


@app.route('/account/update', methods=['POST'])
@login_required
def update_account():
    current_user.full_name = request.form.get('full_name')
    current_user.phone = request.form.get('phone')
    current_user.address = request.form.get('address')
    current_user.city = request.form.get('city')
    current_user.postal_code = request.form.get('postal_code')
    current_user.country = request.form.get('country')
    
    db.session.commit()
    return redirect(url_for('account'))


# ======================== ROUTES - CART ========================

@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.iphone.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)


@app.route('/api/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json()
    iphone_id = data.get('iphone_id')
    quantity = data.get('quantity', 1)

    iphone = iPhone.query.get_or_404(iphone_id)

    if iphone.stock < quantity:
        return jsonify({'error': 'Insufficient stock'}), 400

    cart_item = CartItem.query.filter_by(user_id=current_user.id, iphone_id=iphone_id).first()

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, iphone_id=iphone_id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()
    return jsonify({'message': 'Added to cart'}), 200


@app.route('/api/cart/remove/<int:item_id>', methods=['DELETE'])
@login_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    
    if cart_item.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(cart_item)
    db.session.commit()
    return jsonify({'message': 'Removed from cart'}), 200


@app.route('/api/cart/update/<int:item_id>', methods=['PUT'])
@login_required
def update_cart_item(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    
    if cart_item.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    quantity = data.get('quantity', 1)

    if quantity <= 0:
        db.session.delete(cart_item)
    else:
        cart_item.quantity = quantity

    db.session.commit()
    return jsonify({'message': 'Cart updated'}), 200


# ======================== ROUTES - CHECKOUT ========================

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        return redirect(url_for('cart'))

    if request.method == 'POST':
        total_amount = sum(item.iphone.price * item.quantity for item in cart_items)

        order = Order(user_id=current_user.id, total_amount=total_amount)
        order.generate_order_number()

        for item in cart_items:
            order_item = OrderItem(
                iphone_id=item.iphone_id,
                quantity=item.quantity,
                unit_price=item.iphone.price,
                subtotal=item.iphone.price * item.quantity
            )
            order.order_items.append(order_item)
            
            # Reduce stock
            item.iphone.stock -= item.quantity

        db.session.add(order)
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        return redirect(url_for('order_confirmation', order_id=order.id))

    total = sum(item.iphone.price * item.quantity for item in cart_items)
    return render_template('checkout.html', cart_items=cart_items, total=total, user=current_user)


@app.route('/order/confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    
    if order.user_id != current_user.id:
        return redirect(url_for('index'))

    return render_template('order_confirmation.html', order=order)


@app.route('/order/track/<int:order_id>')
@login_required
def track_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    if order.user_id != current_user.id:
        return redirect(url_for('index'))

    return render_template('track_order.html', order=order)


# ======================== ROUTES - ADMIN ========================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        admin = Admin.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid credentials')

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@admin_login_required
def admin_dashboard():
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    pending_orders = Order.query.filter_by(status='Pending').count()
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    return render_template('admin_dashboard.html', 
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         pending_orders=pending_orders,
                         recent_orders=recent_orders)


@app.route('/admin/orders')
@admin_login_required
def admin_orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status')

    query = Order.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=20)

    return render_template('admin_orders.html', orders=orders)


@app.route('/admin/order/<int:order_id>/update-status', methods=['POST'])
@admin_login_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    
    new_status = request.form.get('status')
    new_delivery_status = request.form.get('delivery_status')
    tracking_number = request.form.get('tracking_number')

    if new_status:
        order.status = new_status

    if new_delivery_status:
        order.delivery_status = new_delivery_status

    if tracking_number:
        order.tracking_number = tracking_number

    order.updated_at = datetime.utcnow()
    db.session.commit()

    return redirect(url_for('admin_orders'))


@app.route('/admin/products')
@admin_login_required
def admin_products():
    page = request.args.get('page', 1, type=int)
    products = iPhone.query.paginate(page=page, per_page=20)
    return render_template('admin_products.html', products=products)


@app.route('/admin/product/add', methods=['GET', 'POST'])
@admin_login_required
def add_product():
    if request.method == 'POST':
        iphone = iPhone(
            model=request.form.get('model'),
            storage=request.form.get('storage'),
            color=request.form.get('color'),
            condition=request.form.get('condition'),
            price=float(request.form.get('price')),
            stock=int(request.form.get('stock')),
            description=request.form.get('description'),
            image_url=request.form.get('image_url')
        )
        db.session.add(iphone)
        db.session.commit()
        return redirect(url_for('admin_products'))

    return render_template('admin_add_product.html')


@app.route('/admin/product/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_login_required
def edit_product(product_id):
    product = iPhone.query.get_or_404(product_id)

    if request.method == 'POST':
        product.model = request.form.get('model')
        product.storage = request.form.get('storage')
        product.color = request.form.get('color')
        product.condition = request.form.get('condition')
        product.price = float(request.form.get('price'))
        product.stock = int(request.form.get('stock'))
        product.description = request.form.get('description')
        product.image_url = request.form.get('image_url')
        
        db.session.commit()
        return redirect(url_for('admin_products'))

    return render_template('admin_edit_product.html', product=product)


@app.route('/admin/product/<int:product_id>/delete', methods=['POST'])
@admin_login_required
def delete_product(product_id):
    product = iPhone.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_products'))


# ======================== ERROR HANDLERS ========================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500


# ======================== DATABASE INITIALIZATION ========================

def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default admin if not exists
        if Admin.query.filter_by(username='admin').first() is None:
            admin = Admin(username='admin', email='admin@iphonestore.com')
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: username=admin, password=admin123")
        
        # Add sample products if database is empty
        if iPhone.query.first() is None:
            sample_products = [
                iPhone(model='iPhone XR', storage='64GB', color='Space Gray', condition='New', price=299.99, stock=10, description='iPhone XR - Brand New', image_url='https://via.placeholder.com/300?text=iPhone+XR'),
                iPhone(model='iPhone XR', storage='128GB', color='Black', condition='Refurbished', price=249.99, stock=5, description='iPhone XR - Refurbished', image_url='https://via.placeholder.com/300?text=iPhone+XR'),
                iPhone(model='iPhone 11', storage='64GB', color='White', condition='New', price=399.99, stock=15, description='iPhone 11 - Brand New', image_url='https://via.placeholder.com/300?text=iPhone+11'),
                iPhone(model='iPhone 12', storage='128GB', color='Blue', condition='New', price=599.99, stock=8, description='iPhone 12 - Brand New', image_url='https://via.placeholder.com/300?text=iPhone+12'),
                iPhone(model='iPhone 13', storage='256GB', color='Sierra Blue', condition='New', price=799.99, stock=12, description='iPhone 13 - Brand New', image_url='https://via.placeholder.com/300?text=iPhone+13'),
                iPhone(model='iPhone 14', storage='512GB', color='Gold', condition='New', price=999.99, stock=6, description='iPhone 14 - Brand New', image_url='https://via.placeholder.com/300?text=iPhone+14'),
                iPhone(model='iPhone 15', storage='128GB', color='Black', condition='New', price=799.99, stock=20, description='iPhone 15 - Brand New', image_url='https://via.placeholder.com/300?text=iPhone+15'),
                iPhone(model='iPhone 16', storage='256GB', color='Titanium Gray', condition='New', price=899.99, stock=14, description='iPhone 16 - Brand New', image_url='https://via.placeholder.com/300?text=iPhone+16'),
                iPhone(model='iPhone 17', storage='512GB', color='Titanium Blue', condition='New', price=1099.99, stock=7, description='iPhone 17 - Brand New', image_url='https://via.placeholder.com/300?text=iPhone+17'),
            ]
            for product in sample_products:
                db.session.add(product)
            db.session.commit()
            print("Sample products added to database")


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
