from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from database.init_db import db, create_app as create_db_app
from config import Config
from models.user import User
from models.customer import Customer
from models.audit_log import AuditLog
from models.goal import Goal
from models.reminder import Reminder
from models.deal import Deal
from utils.exports import customers_csv

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, resources={r"/api/*": {"origins": "*"}})

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.', 'danger')
            return render_template('register.html')

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Welcome back, %s!' % user.username, 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid credentials.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    customer_count = Customer.query.count()
    audit_count = AuditLog.query.count()

    chart_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    income_history = [7500, 8300, 9100, 9800, 10200, 11700, 12500, 13400, 14000, 15100, 16300, 17100]
    expenses_history = [4200, 4300, 4550, 4800, 4900, 5300, 5450, 5800, 6100, 6500, 6800, 7000]

    profit_history = [inc - exp for inc, exp in zip(income_history, expenses_history)]

    # Business funds data
    funds_by_class = [
        {'label': 'Alpha Growth Fund', 'value': 125000},
        {'label': 'Beta Dividend Stock', 'value': 89000},
        {'label': 'Gamma Tech Index', 'value': 72000},
        {'label': 'Delta Bonds', 'value': 54000}
    ]

    # DB-powered goals
    raw_goals = Goal.query.filter_by(user_id=current_user.id, is_active=True).order_by(Goal.due_date.asc().nullslast()).all()
    if not raw_goals:
        raw_goals = [
            Goal(user_id=current_user.id, title='Close 3 enterprise deals', progress=67),
            Goal(user_id=current_user.id, title='Increase renewal rate to 92%', progress=76),
            Goal(user_id=current_user.id, title='Launch new marketing campaign', progress=45),
        ]

    business_goals = []
    for g in raw_goals:
        business_goals.append({
            'id': getattr(g, 'id', 0) or 0,
            'goal': g.title,
            'progress': g.progress,
            'due_date': g.due_date if hasattr(g, 'due_date') else None
        })

    executive_actions = [
        'Review cashflow forecast',
        'Approve Q2 budget',
        'Send follow-up to top lead',
        'Schedule board meeting'
    ]

    # DB-powered reminders
    reminders = Reminder.query.filter_by(user_id=current_user.id, is_done=False).order_by(Reminder.due_date.asc()).all()

    # DB-powered deals pipeline
    deals = Deal.query.filter_by(user_id=current_user.id).order_by(Deal.expected_close_date.asc().nullslast()).all()
    funnel_stages = ['Lead', 'Qualified', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost']
    funnel_values = [sum(d.value for d in deals if d.stage == stage) for stage in funnel_stages]

    business_kpis = {
        'Total Revenue': '$' + f'{sum(income_history):,}',
        'Total Expenses': '$' + f'{sum(expenses_history):,}',
        'Net Profit': '$' + f'{sum(profit_history):,}',
        'Monthly Growth': '6.2%',
        'Customer Retention': '88%',
        'Active Projects': len(deals)
    }

    return render_template(
        'dashboard.html',
        customer_count=customer_count,
        audit_count=audit_count,
        chart_months=chart_months,
        income_history=income_history,
        expenses_history=expenses_history,
        profit_history=profit_history,
        funds_by_class=funds_by_class,
        business_kpis=business_kpis,
        business_goals=business_goals,
        executive_actions=executive_actions,
        reminders=reminders,
        deals=deals,
        funnel_stages=funnel_stages,
        funnel_values=funnel_values
    )

# API endpoints for Netlify frontend proxy
@app.route('/api/customers', methods=['GET', 'POST'])
@login_required
def api_customers():
    if request.method == 'GET':
        items = [
            {
                'id': c.id,
                'first_name': c.first_name,
                'last_name': c.last_name,
                'email': c.email,
                'phone': c.phone,
                'company': c.company,
                'created_at': c.created_at.isoformat()
            }
            for c in Customer.query.order_by(Customer.created_at.desc()).all()
        ]
        return jsonify(items)

    data = request.json or {}
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    if not first_name or not last_name or not email:
        return jsonify({'error': 'first_name/last_name/email required'}), 400

    if Customer.query.filter_by(email=email).first():
        return jsonify({'error': 'email exists'}), 409

    customer = Customer(first_name=first_name, last_name=last_name, email=email,
                        phone=data.get('phone'), company=data.get('company'))
    db.session.add(customer)
    db.session.commit()
    return jsonify({'id': customer.id}), 201

@app.route('/api/customers/<int:cid>', methods=['PUT', 'DELETE'])
@login_required
def api_customer_manage(cid):
    customer = Customer.query.get_or_404(cid)
    if request.method == 'DELETE':
        db.session.delete(customer)
        db.session.commit()
        return jsonify({'status': 'deleted'})
    data = request.json or {}
    customer.first_name = data.get('first_name', customer.first_name)
    customer.last_name = data.get('last_name', customer.last_name)
    customer.email = data.get('email', customer.email)
    customer.phone = data.get('phone', customer.phone)
    customer.company = data.get('company', customer.company)
    db.session.commit()
    return jsonify({'status': 'updated'})

@app.route('/api/goals', methods=['GET', 'POST'])
@login_required
def api_goals():
    if request.method == 'GET':
        items = [
            {'id': g.id, 'title': g.title, 'progress': g.progress, 'due_date': g.due_date.isoformat() if g.due_date else None, 'is_active': g.is_active}
            for g in Goal.query.filter_by(user_id=current_user.id, is_active=True).all()
        ]
        return jsonify(items)

    data = request.json or {}
    if not data.get('title'):
        return jsonify({'error': 'title required'}), 400
    goal = Goal(user_id=current_user.id, title=data['title'], progress=data.get('progress', 0), due_date=data.get('due_date'))
    db.session.add(goal)
    db.session.commit()
    return jsonify({'id': goal.id}), 201

@app.route('/api/reminders', methods=['GET', 'POST'])
@login_required
def api_reminders():
    if request.method == 'GET':
        items = [
            {'id': r.id, 'message': r.message, 'due_date': r.due_date.isoformat(), 'is_done': r.is_done}
            for r in Reminder.query.filter_by(user_id=current_user.id, is_done=False).all()
        ]
        return jsonify(items)

    data = request.json or {}
    if not data.get('message') or not data.get('due_date'):
        return jsonify({'error': 'message and due_date required'}), 400
    reminder = Reminder(user_id=current_user.id, message=data['message'], due_date=data['due_date'])
    db.session.add(reminder)
    db.session.commit()
    return jsonify({'id': reminder.id}), 201

@app.route('/api/deals', methods=['GET', 'POST'])
@login_required
def api_deals():
    if request.method == 'GET':
        items = [
            {'id': d.id, 'name': d.name, 'stage': d.stage, 'value': d.value, 'probability': d.probability, 'expected_close_date': d.expected_close_date.isoformat() if d.expected_close_date else None}
            for d in Deal.query.filter_by(user_id=current_user.id).all()
        ]
        return jsonify(items)

    data = request.json or {}
    if not data.get('name') or not data.get('value'):
        return jsonify({'error': 'name and value required'}), 400
    deal = Deal(user_id=current_user.id, name=data['name'], stage=data.get('stage', 'Lead'), value=data['value'], probability=data.get('probability', 0), expected_close_date=data.get('expected_close_date'))
    db.session.add(deal)
    db.session.commit()
    return jsonify({'id': deal.id}), 201

@app.route('/customers')
@login_required
def customers():
    data = Customer.query.order_by(Customer.created_at.desc()).all()
    return render_template('customers.html', customers=data)

@app.route('/goals/add', methods=['POST'])
@login_required
def add_goal():
    title = request.form.get('goal_title', '').strip()
    progress = int(request.form.get('goal_progress', 0))
    due_date = request.form.get('goal_due_date') or None

    if title:
        goal = Goal(user_id=current_user.id, title=title, progress=progress, due_date=due_date)
        db.session.add(goal)
        db.session.commit()
        flash('Goal saved.', 'success')
    else:
        flash('Goal title is required.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/goals/update/<int:goal_id>', methods=['POST'])
@login_required
def update_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    goal.progress = int(request.form.get('goal_progress', goal.progress))
    goal.is_active = request.form.get('goal_active') == 'on'
    db.session.commit()
    flash('Goal updated.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/goals/delete/<int:goal_id>', methods=['POST'])
@login_required
def delete_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    flash('Goal removed.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/reminders/add', methods=['POST'])
@login_required
def add_reminder():
    message = request.form.get('reminder_message', '').strip()
    due_date = request.form.get('reminder_due_date')

    if message and due_date:
        reminder = Reminder(user_id=current_user.id, message=message, due_date=due_date)
        db.session.add(reminder)
        db.session.commit()
        flash('Reminder created.', 'success')
    else:
        flash('Reminder details are required.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/reminders/complete/<int:reminder_id>', methods=['POST'])
@login_required
def complete_reminder(reminder_id):
    reminder = Reminder.query.filter_by(id=reminder_id, user_id=current_user.id).first_or_404()
    reminder.is_done = True
    db.session.commit()
    flash('Reminder completed.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/deals/add', methods=['POST'])
@login_required
def add_deal():
    name = request.form.get('deal_name', '').strip()
    stage = request.form.get('deal_stage', 'Lead')
    value = float(request.form.get('deal_value', 0) or 0)
    probability = int(request.form.get('deal_probability', 0) or 0)
    expected_close_date = request.form.get('deal_close_date') or None

    if name and value > 0:
        deal = Deal(user_id=current_user.id, name=name, stage=stage, value=value, probability=probability, expected_close_date=expected_close_date)
        db.session.add(deal)
        db.session.commit()
        flash('Deal added.', 'success')
    else:
        flash('Deal name and value are required.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/deals/update/<int:deal_id>', methods=['POST'])
@login_required
def update_deal(deal_id):
    deal = Deal.query.filter_by(id=deal_id, user_id=current_user.id).first_or_404()
    deal.stage = request.form.get('deal_stage', deal.stage)
    deal.probability = int(request.form.get('deal_probability', deal.probability) or deal.probability)
    db.session.commit()
    flash('Deal updated.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/deals/delete/<int:deal_id>', methods=['POST'])
@login_required
def delete_deal(deal_id):
    deal = Deal.query.filter_by(id=deal_id, user_id=current_user.id).first_or_404()
    db.session.delete(deal)
    db.session.commit()
    flash('Deal removed.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        email = request.form['email'].strip().lower()
        phone = request.form['phone'].strip()
        company = request.form['company'].strip()

        if not first_name or not last_name or not email:
            flash('First name, last name and email are required.', 'danger')
            return render_template('add_customer.html')

        if Customer.query.filter_by(email=email).first():
            flash('Customer email already exists.', 'danger')
            return render_template('add_customer.html')

        customer = Customer(first_name=first_name, last_name=last_name, email=email, phone=phone or None, company=company or None)
        db.session.add(customer)
        db.session.commit()

        audit = AuditLog(user_id=current_user.id, action='Created customer', target_type='Customer', target_id=customer.id)
        db.session.add(audit)
        db.session.commit()

        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers'))

    return render_template('add_customer.html')

@app.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    if request.method == 'POST':
        customer.first_name = request.form['first_name'].strip()
        customer.last_name = request.form['last_name'].strip()
        customer.email = request.form['email'].strip().lower()
        customer.phone = request.form['phone'].strip() or None
        customer.company = request.form['company'].strip() or None

        if not customer.first_name or not customer.last_name or not customer.email:
            flash('First name, last name and email are required.', 'danger')
            return render_template('edit_customer.html', customer=customer)

        db.session.commit()

        audit = AuditLog(user_id=current_user.id, action='Updated customer', target_type='Customer', target_id=customer.id)
        db.session.add(audit)
        db.session.commit()

        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customers'))

    return render_template('edit_customer.html', customer=customer)

@app.route('/customers/delete/<int:customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    db.session.delete(customer)
    audit = AuditLog(user_id=current_user.id, action='Deleted customer', target_type='Customer', target_id=customer.id)
    db.session.add(audit)
    db.session.commit()
    flash('Customer removed.', 'success')
    return redirect(url_for('customers'))

@app.route('/audit-log')
@login_required
def audit_log():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(200).all()
    return render_template('audit_log.html', logs=logs)

@app.route('/export/customers')
@login_required
def export_customers():
    all_customers = Customer.query.order_by(Customer.id).all()
    return customers_csv(all_customers)

@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
