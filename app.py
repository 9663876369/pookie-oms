from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os, io
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50))
    address = db.Column(db.String(500))
    pincode = db.Column(db.String(20))
    item = db.Column(db.String(200))
    quantity = db.Column(db.Integer, default=1)
    total_amount = db.Column(db.Float, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')  # pending or completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def pending_amount(self):
        return round((self.total_amount or 0) - (self.paid_amount or 0), 2)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

with app.app_context():
    db.create_all()

    # create default admin if none exists
    if not Admin.query.first():
        default_user = Admin(username=os.environ.get('ADMIN_USER','admin'),
                             password_hash=generate_password_hash(os.environ.get('ADMIN_PASS','password')))
        db.session.add(default_user)
        db.session.commit()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_logged_in'] = True
            session['admin_user'] = username
            return redirect(url_for('index'))
        flash('Invalid credentials','danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return redirect(url_for('orders'))

@app.route('/orders')
@login_required
def orders():
    q = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=q)

@app.route('/orders/add', methods=['GET','POST'])
@login_required
def add_order():
    if request.method == 'POST':
        data = request.form
        order = Order(
            customer_name=data.get('customer_name'),
            phone=data.get('phone'),
            address=data.get('address'),
            pincode=data.get('pincode'),
            item=data.get('item'),
            quantity=int(data.get('quantity') or 1),
            total_amount=float(data.get('total_amount') or 0),
            paid_amount=float(data.get('paid_amount') or 0),
            status='pending'
        )
        db.session.add(order)
        db.session.commit()
        flash('Order added','success')
        return redirect(url_for('orders'))
    return render_template('add_order.html')

@app.route('/orders/<int:order_id>/edit', methods=['GET','POST'])
@login_required
def edit_order(order_id):
    order = Order.query.get_or_404(order_id)
    if request.method == 'POST':
        data = request.form
        order.customer_name = data.get('customer_name')
        order.phone = data.get('phone')
        order.address = data.get('address')
        order.pincode = data.get('pincode')
        order.item = data.get('item')
        order.quantity = int(data.get('quantity') or 1)
        order.total_amount = float(data.get('total_amount') or 0)
        order.paid_amount = float(data.get('paid_amount') or 0)
        order.status = data.get('status')
        db.session.commit()
        flash('Order updated','success')
        return redirect(url_for('orders'))
    return render_template('edit_order.html', order=order)

@app.route('/orders/<int:order_id>/delete', methods=['POST'])
@login_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash('Order deleted','success')
    return redirect(url_for('orders'))

@app.route('/orders/<int:order_id>/mark/<string:state>')
@login_required
def mark_order(order_id, state):
    order = Order.query.get_or_404(order_id)
    if state in ('pending','completed'):
        order.status = state
        db.session.commit()
    return redirect(url_for('orders'))

@app.route('/orders/<int:order_id>/invoice')
@login_required
def invoice(order_id):
    order = Order.query.get_or_404(order_id)
    business_name = os.environ.get('BUSINESS_NAME','Pookie Sells')
    return render_template('invoice.html', order=order, business_name=business_name)

@app.route('/reports', methods=['GET'])
@login_required
def reports():
    # filters
    month = request.args.get('month')  # format YYYY-MM
    date = request.args.get('date')    # format YYYY-MM-DD

    query = Order.query
    if month:
        start = datetime.strptime(month+"-01", "%Y-%m-%d")
        # next month
        if start.month == 12:
            end = datetime(start.year+1,1,1)
        else:
            end = datetime(start.year, start.month+1,1)
        query = query.filter(Order.created_at >= start, Order.created_at < end)
    if date:
        start = datetime.strptime(date, "%Y-%m-%d")
        end = start.replace(hour=23, minute=59, second=59)
        query = query.filter(Order.created_at >= start, Order.created_at <= end)

    orders = query.order_by(Order.created_at.asc()).all()

    # aggregate totals
    total_sales = sum(o.total_amount for o in orders)
    total_paid = sum(o.paid_amount for o in orders)
    total_pending = sum(o.pending_amount for o in orders)
    per_day = db.session.query(func.date(Order.created_at), func.count(Order.id),
                               func.sum(Order.total_amount), func.sum(Order.paid_amount))                        .group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at)).all()
    return render_template('reports.html', orders=orders, total_sales=total_sales,
                           total_paid=total_paid, total_pending=total_pending, per_day=per_day)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

