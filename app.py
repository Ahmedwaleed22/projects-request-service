from flask import Flask, render_template, request, session, redirect, url_for, jsonify, send_from_directory
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from flask_session import Session
from functools import wraps
from functions import fetch_one_with_columns, fetch_all_with_columns
from werkzeug.utils import secure_filename
import stripe
import random
import string
import jwt
import os


path = os.getcwd()
PROJECTS_FOLDER = os.path.join(path, 'projects')

if not os.path.isdir(PROJECTS_FOLDER):
  os.mkdir(PROJECTS_FOLDER)


app = Flask(__name__)
app.config['secret_key'] = 'BzRDgK2JAtaixivnguCz8aEzgX1oyrZn'
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'WorkRequestsProject'
app.config['MAIL_SERVER'] = 'smtp.hostinger.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'support@complete-thesis.com'
app.config['MAIL_PASSWORD'] = '87555622aB@'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['PROJECTS_FOLDER'] = PROJECTS_FOLDER

stripe_keys = {
  'secret_key': 'sk_test_51KL5fZSIeo8cbA9acaGiriXApreMJoliz1YnTX9SdweJMliwxVUeMDoU8zdb8nLFFVMmcUizp1S2BSlx1OVwhJ5j00i59tU6US',
  'publishable_key': 'pk_test_51KL5fZSIeo8cbA9aFNsoJYy35jp4ePQtnrJOSUwc34oMGcc0KL88oW1KB9jsdm0ZoShZwOh1zLba7yI6c6NxDIc200kIlLxI9q'
}


mysql = MySQL(app)
mail = Mail(app)
bcrypt = Bcrypt(app)
Session(app)
stripe.api_key = stripe_keys['secret_key']


def token_required(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    token = None
    if "Authorization" in request.headers:
      token = request.headers["Authorization"].split(" ")[1]
    if not token:
      return {
        "message": "Authentication Token is missing!",
        "data": None,
        "error": "Unauthorized"
      }, 401
    try:
      data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])

      cursor = mysql.connection.cursor()
      cursor.execute("SELECT * FROM users WHERE id = %s", (data['public_id'],))
      current_user = cursor.fetchone()
      cursor.close()

      user = {
        "id": current_user[0],
        "username": current_user[1],
      }

      if current_user is None:
        return {
          "message": "Invalid Authentication token!",
          "data": None,
          "error": "Unauthorized"
        }, 401
    except Exception as e:
      return {
        "message": "Something went wrong",
        "data": None,
        "error": str(e)
      }, 500

    return f(user, *args, **kwargs)

  return decorated


@app.route("/api/stripe/config")
def get_publishable_key():
  stripe_config = {"publicKey": stripe_keys["publishable_key"]}
  return jsonify(stripe_config)


@app.route('/create', methods=['GET'])
def create():
  if session.get('user_id'):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    cursor.close()
    return render_template('create.html', categories=categories)
  else:
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    email = request.form.get('email')
    password = request.form.get('password')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT ID, username, password FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    if bcrypt.check_password_hash(user[2], password):
      session['user_id'] = user[0]
      session['username'] = user[1]

      return redirect(url_for('dashboard'))

  else:
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
  if request.method == 'POST':
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    # Project Info
    project_title = request.form.get('project_name', default=None)
    category_id = request.form.get('project_category', default=None)
    project_id = request.form.get('project', default=None)

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = %s", (email,))
    count = cursor.fetchone()[0]

    if not count > 0:
      hashed_pass = bcrypt.generate_password_hash(password)
      cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed_pass))
      mysql.connection.commit()
      user_id = cursor.lastrowid
      cursor.close()

      if project_title is not None and category_id is not None and project_id is not None:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT name FROM work WHERE ID = %s", (project_id,))
        project = cursor.fetchone()[0]
        cursor.close()

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT name FROM categories WHERE ID = %s", (category_id,))
        category = cursor.fetchone()[0]
        cursor.close()

        msg = Message("New Project Requested", sender='support@complete-thesis.com', recipients=['me@ahmedwaleed.net'])
        msg.body = f"Someone requested a projected of type {project} from category {category}"
        mail.send(msg)

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO work_requests (project_title, services_id, user_id) VALUES (%s, %s, %s)", (project_title, project_id, user_id))
        mysql.connection.commit()
        cursor.close()

        return render_template('register.html', message="Account Created Successfully and Project Sent to Admins For Approval", status='SUCCESS')

    else:
      return render_template('register.html', message="Email Already Registered", status='FAILED')

    return render_template('register.html', message="Account Created Successfully", status='SUCCESS')

  else:
    return render_template('register.html')


@app.route('/send-work', methods=['POST'])
def send_work():
  if session.get('user_id'):
    project_title = request.json.get('project_title')
    category_id = request.json.get('category_id')
    project_id = request.json.get('project_id')
    user_id = session.get('user_id')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT name FROM work WHERE ID = %s", (project_id,))
    project = cursor.fetchone()[0]
    cursor.close()

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT name FROM categories WHERE ID = %s", (category_id,))
    category = cursor.fetchone()[0]
    cursor.close()

    msg = Message("New Project Requested", sender='support@complete-thesis.com', recipients=['me@ahmedwaleed.net'])
    msg.body = f"Someone requested a projected of type {project} from category {category}"
    mail.send(msg)

    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO work_requests (project_title, services_id, user_id) VALUES (%s, %s, %s)", (project_title, project_id, user_id))
    mysql.connection.commit()
    cursor.close()

    return "Waiting For Admin To Approve The Request"
  else:
    return "Not Logged In", 403


@app.route('/dashboard')
def dashboard():
  if session.get('user_id'):
    user_id = session.get('user_id')
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT work_requests.*, work.*, work_requests.ID as request_id FROM work_requests INNER JOIN work ON work_requests.services_id = work.ID WHERE work_requests.user_id = %s", (user_id,))
    projects = cursor.fetchall()
    results = fetch_all_with_columns(cursor.description, projects)
    cursor.close()

    return render_template('dashboard.html', projects=results)

  return redirect(url_for('login'))


@app.route('/dashboard/project/<id>', methods=['GET', 'POST'])
def dashboard_project(id):
  if session.get('user_id'):
    if request.method == 'POST':
      project_instruction = request.json.get('instructions')

      checkout_id = ''.join(random.choice(string.ascii_letters) for i in range(32))

      cursor = mysql.connection.cursor()
      cursor.execute("SELECT * FROM work_requests WHERE ID = %s", (id,))
      work_request = cursor.fetchone()
      results = fetch_one_with_columns(cursor.description, work_request)

      if results['user_id'] == session.get('user_id'):
        cursor.execute("SELECT * FROM work WHERE ID = %s", (str(results['services_id'])))
        work = cursor.fetchone()
        work_results = fetch_one_with_columns(cursor.description, work)

        cursor.execute("INSERT INTO payment (instructions, checkout_id, request_id) VALUES (%s, %s, %s)", (project_instruction, checkout_id, id))
        mysql.connection.commit()
        cursor.close()

        product = stripe.Product.create(
          name=work_results['name'],
        )

        # checkout using stripe
        price = stripe.Price.create(
          currency='inr',
          unit_amount=int(work_results['price']) * 100,
          product=product.id
        )

        stripe_session = stripe.checkout.Session.create(
          payment_method_types=['card'],
          mode='payment',
          line_items=[
            {
              'price': price.id,
              'quantity': 1,
            }
          ],
          payment_intent_data={
            'metadata': {
              'checkout_id': checkout_id
            }
          },
          success_url='http://localhost:8000/checkout/success/{CHECKOUT_SESSION_ID}',
          cancel_url=url_for('checkout_cancel', _external=True)
        )

        return jsonify({"sessionId": stripe_session["id"]})

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM work_requests WHERE ID = %s", (id,))
    work_request = cursor.fetchone()
    if work_request:
      results = fetch_one_with_columns(cursor.description, work_request)
    else:
      return redirect(url_for('dashboard'))

    if results['user_id'] == session.get('user_id'):
      return render_template('dashboard_project.html', project=results)
    else:
      return redirect(url_for('dashboard'))

  else:
    return redirect(url_for('login'))


@app.route('/checkout/success/<session_id>')
def checkout_success(session_id):
  try:
    session = stripe.checkout.Session.retrieve(session_id)
    payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
    checkout_id = payment_intent.metadata.get('checkout_id')

    if session.payment_status == 'paid':
      cursor = mysql.connection.cursor()
      cursor.execute("SELECT * FROM payment WHERE checkout_id = %s", (checkout_id,))
      payment_info = cursor.fetchone()

      cursor.execute("UPDATE work_requests SET instructions = %s, status = %s WHERE ID = %s", (payment_info[1], 1, payment_info[3]))
      mysql.connection.commit()
      return redirect(url_for('dashboard'))

    return render_template('error.html')
  except stripe.error.InvalidRequestError:
    return render_template('canceled.html')


@app.route('/checkout/canceled', methods=['GET'])
def checkout_cancel():
  return render_template('canceled.html')


@app.route('/download/project/<id>')
def download_project(id):
  cursor = mysql.connection.cursor()
  cursor.execute("SELECT * FROM project_files WHERE project_id = %s", (id,))
  filename = cursor.fetchone()[1]

  return send_from_directory(app.config['PROJECTS_FOLDER'], filename, as_attachment=True)


@app.route('/api/getprojects/<id>')
def get_projects(id):
  cursor = mysql.connection.cursor()
  cursor.execute("SELECT * FROM work WHERE category_id = %s", (id,))
  projects = cursor.fetchall()
  results = fetch_all_with_columns(cursor.description, projects)
  cursor.close()

  return results


# Admin Panel Routes

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
  if request.method == 'POST':
    email = request.form.get('email')
    password = request.form.get('password')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT ID, email, password FROM admins WHERE email = %s", (email,))
    user = cursor.fetchone()

    if bcrypt.check_password_hash(user[2], password):
      session['admin_id'] = user[0]
      session['admin_email'] = user[1]

      return redirect(url_for('admin'))

  return render_template('/admin/login.html')


@app.route('/admin')
def admin():
  if not session.get('admin_id'):
    return redirect(url_for('admin_login'))

  cursor = mysql.connection.cursor()
  cursor.execute("SELECT work_requests.*, work.name as service_name, categories.name as category_name, work.category_id FROM work_requests INNER JOIN work ON work_requests.services_id = work.ID INNER JOIN categories ON work.category_id = categories.ID WHERE status = 1 OR status = 2 OR status = 3")
  projects = cursor.fetchall()
  results = fetch_all_with_columns(cursor.description, projects)
  cursor.close()
  status_messages = ('PAYMENT REQUIRED', 'WAITING APPROVAL', 'APPROVED', 'WORK SENT', 'REJECTED')

  return render_template('/admin/projects.html', projects=results, status_messages=status_messages)


@app.route('/admin/projects/<id>/sendfiles', methods=['GET', 'POST'])
def send_files(id):
  if not session.get('admin_id'):
    return redirect(url_for('admin_login'))

  if request.method == 'POST':
    file = request.files['files']
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['PROJECTS_FOLDER'], filename))
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO project_files (files, project_id) VALUES (%s, %s)", (filename, id))
    cursor.execute("UPDATE work_requests SET status = %s WHERE ID = %s", (3, id))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('admin'))

  return render_template('/admin/sendfiles.html')


@app.route('/admin/api/projects/<id>/<status>')
def set_status(id, status):
  if not session.get('admin_id'):
    return redirect(url_for('admin_login'))

  status_code = 4

  if status == 'approve':
    status_code = 2

  cursor = mysql.connection.cursor()
  cursor.execute("UPDATE work_requests SET status = %s WHERE ID = %s", (status_code, id))
  mysql.connection.commit()
  cursor.close()

  return redirect(url_for('admin'))


if __name__ == '__main__':
  app.run(debug=True, port=8000, host='0.0.0.0')
