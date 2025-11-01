from flask import Flask , render_template , request, redirect , url_for , session, flash 
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3
import os
import barcode
from barcode.writer import ImageWriter 
from flask_login import login_required, current_user
# from flask_login import LoginManager
# from barcode.writer import ImageWriter
# from io import BytesIO
# import base64

# from yourapp import db, User  # adjust import as needed



@event.listens_for(Engine, "connect")
def enforce_foreign_keys(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()



app = Flask(__name__)
app.secret_key = "supersecretkey"  # 🔐 Replace this with a long, random secret in production!
app.config['SQLALCHEMY_DATABASE_URI']= "sqlite:///venues.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


from flask_login import LoginManager
from flask_login import UserMixin

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # The login route name





app.app_context().push()    
class Venue(db.Model):
    sno = db.Column(db.Integer, primary_key=True) 
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer , nullable = False)
    date_created=db.Column(db.DateTime, default = datetime.utcnow)
    # one venue can have many shows linked to it 
    shows = db.relationship('Show', back_populates='venue', cascade="all, delete", passive_deletes=True)

    def __repr__(self):  
       return f"<Venue {self.name} - {self.date_created}>"
    
app.app_context().push()  
class Show(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    # This connects each show to a venue
    venue = db.relationship('Venue', back_populates='shows')
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.sno', ondelete='CASCADE'), nullable=False)
    remaining_seats = db.Column(db.Integer, nullable=False, default=100)  # or based on venue.capacity



app.app_context().push()  
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



app.app_context().push() 
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seat_number = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    show_id = db.Column(db.Integer, db.ForeignKey('show.id'), nullable=False)

    snacks = db.Column(db.String(200))  # New column to store snack names


    user = db.relationship('User', backref='bookings')
    show = db.relationship('Show', backref='bookings')


# @app.route("/register", methods=["GET", "POST"])
# def register():
#     if request.method == "POST":
#         username = request.form["username"]
#         phone = request.form["phone"]
#         password = request.form["password"]

#         # Check if username already exists
#         existing_user = User.query.filter_by(username=username).first()
#         existing_phone = User.query.filter_by(phone=phone).first()

#         if existing_user or existing_phone:
#          return "Username or Phone already registered."



#         new_user = User(username=username, phone=phone, password=password)
#         db.session.add(new_user)
#         db.session.commit()

#         return redirect(url_for("login"))

#     return render_template("register.html")

import random
from flask import session

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        phone = request.form["phone"]
        password = request.form["password"]

        # Check if username or phone already exists
        existing_user = User.query.filter_by(username=username).first()
        existing_phone = User.query.filter_by(phone=phone).first()

        if existing_user or existing_phone:
            return "Username or Phone already registered."

        # Generate OTP and store user details in session
        otp = str(random.randint(100000, 999999))
        session["otp"] = otp
        session["pending_user"] = {
            "username": username,
            "phone": phone,
            "password": password
        }

        print(f"DEBUG OTP: {otp}")  # Show this in terminal for testing (or display on next page)

        return redirect(url_for("verify_otp"))

    return render_template("register.html")



@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        entered_otp = request.form["otp"]
        actual_otp = session.get("otp")
        user_data = session.get("pending_user")

        if entered_otp == actual_otp and user_data:
            new_user = User(
                username=user_data["username"],
                phone=user_data["phone"],
                password=user_data["password"]
            )
            db.session.add(new_user)
            db.session.commit()

            session.pop("otp", None)
            session.pop("pending_user", None)

            return redirect(url_for("login"))
        else:
            return "Invalid OTP. Please try again."

    otp_to_show = session.get("otp")  # Show OTP for now instead of sending
    return render_template("verify_otp.html", otp=otp_to_show)




import random

@app.route('/book/<int:show_id>', methods=['GET', 'POST'])
def book(show_id):
    if 'username' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))

    show = Show.query.get_or_404(show_id)
    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        try:
            seat_number = int(request.form['seat_number'])
        except ValueError:
            return "Invalid seat number format."

        if seat_number < 1 or seat_number > show.venue.capacity:
            return f"Seat number must be between 1 and {show.venue.capacity}."

        if show.remaining_seats <= 0:
            return "Sorry, no seats available."

        # Check for duplicate seat booking
        existing_booking = Booking.query.filter_by(show_id=show.id, seat_number=seat_number).first()
        if existing_booking:
            return f"Seat {seat_number} is already booked for this show. Please choose another seat."

        # 🥤 Get selected snacks & beverages
        selected_snacks = request.form.getlist("snacks")
        snack_string = ", ".join(selected_snacks) if selected_snacks else None

        # 🎟️ Proceed with booking
        booking = Booking(
            seat_number=seat_number,
            user_id=user.id,
            show_id=show.id,
            snacks=snack_string  # Store snacks in the booking
        )

        db.session.add(booking)
        show.remaining_seats -= 1
        db.session.commit()

        # 🧾 Generate barcode
        data = f"{user.phone}-{seat_number}-{show.id}"
        barcode_path = generate_ticket_barcode(data, booking.id)

        # ✨ Add random collectible tagline
        taglines = [
            
            "Tonight's forecast: 100% chance of drama.",
            "Popcorn, chill, and thrill 🍿",
            "You made a great choice!",
            "Collect moments, not just tickets.",
            "Every seat holds a story."
        ]
        selected_tagline = random.choice(taglines)

        return render_template(
            'ticket.html',
            user=user,
            show=show,
            seat_number=seat_number,
            barcode=barcode_path,
            snacks=snack_string,
            tagline=selected_tagline,
            booking_id=booking.id
        )

    return render_template('book_form.html', show=show)



@app.route('/history')
def booking_history():
    if 'username' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    bookings = Booking.query.filter_by(user_id=user.id).all()

    return render_template('history.html', bookings=bookings)


# @app.route('/admin/reset_bookings/<int:show_id>')
# def reset_bookings(show_id):
#     if 'username' not in session or session.get('role') != 'admin':
#         return redirect(url_for('login'))

#     show = Show.query.get_or_404(show_id)
#     venue_capacity = show.venue.capacity

#     # Delete all bookings for this show
#     Booking.query.filter_by(show_id=show.id).delete()

#     # Reset remaining seats to full capacity
#     show.remaining_seats = venue_capacity

#     db.session.commit()

#     return f"All bookings for '{show.name}' have been cleared and seats reset to {venue_capacity}."


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["userName"]
        password = request.form["userPassword"]
        role = request.form["role"]

        if role == "admin":
            if username == "sparky" and password == "rusty":
                session["username"] = username
                session["role"] = "admin"
                return redirect(url_for("admins_page"))
            else:
                return "Invalid Admin Credentials"

        elif role == "user":
            # Lookup the user in the database
            user = User.query.filter_by(username=username, password=password).first()
            if user:
              session["username"] = username
              session["role"] = "user"
              return redirect(url_for("user_dashboard"))
            else:
              return "Invalid User Credentials"
            
    return render_template("login_page.html")


@app.route("/user_dashboard")
def user_dashboard():
    return render_template("user_dashboard.html")


@app.route('/user_venues')
def user_venues():
    venues = Venue.query.all()
    return render_template('user_venues.html', venues=venues)



@app.route("/delete/<int:sno>")
def deleting(sno):
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    venue = Venue.query.filter_by(sno=sno).first()
    db.session.delete(venue)
    db.session.commit()
    return redirect('/admins_page')

@app.route('/delete_show/<int:show_id>')
def delete_show(show_id):
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    show_to_delete = Show.query.get_or_404(show_id)
    db.session.delete(show_to_delete)
    db.session.commit()
    return redirect('/admins_page')

@app.route('/edit_show/<int:show_id>', methods=['POST'])
def edit_show(show_id):
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    show = Show.query.get_or_404(show_id)
    show.name = request.form['name']
    show.price = request.form['price']
    date_str = request.form['date']
    show.date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
    db.session.commit()
    return redirect('/admins_page')


@app.route("/admins_page", methods=['GET', 'POST'])
def admins_page():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        company = request.form['company']
        capacity = int(request.form['capacity'])
        new_venue = Venue(name=name, location=location, company=company, capacity = capacity )
        db.session.add(new_venue)
        db.session.commit()
        return redirect(url_for('admins_page'))

    venues = Venue.query.all()
    return render_template("admin_dash.html", venues=venues)

@app.route("/admin_update/<int:sno>", methods = ['GET', 'POST'])
def updating(sno):
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        company = request.form['company']
        capacity = request.form['capacity']
        venue = Venue.query.filter_by(sno=sno).first()
        venue.name = name
        venue.location = location 
        venue.company = company
        venue.capacity = capacity                 
        db.session.add(venue)
        db.session.commit()
        return redirect('/admins_page')

    venue = Venue.query.filter_by(sno=sno).first()
    return render_template("admin_update.html", venue = venue)

@app.route('/add_show', methods=['POST'])
def add_show():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    name = request.form['name']
    date_str = request.form['date']
    price = request.form['price']
    venue_id = request.form['venue_id']
    # Convert string to datetime object
    date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M")
    new_show = Show(name=name, date=date, price=price, venue_id=venue_id)
    db.session.add(new_show)
    db.session.commit()

    return redirect('/admins_page') 




@app.route('/booking_history_admin')
# @login_required
def booking_history_admin():
    # You might want to add an admin check here
    # For example:
    # if not current_user.is_admin:
    #     abort(403)

    all_bookings = Booking.query.order_by(Booking.id.desc()).all()
    return render_template('full_history.html', bookings=all_bookings)



@app.route("/shows")
def shows():  
    venues = Venue.query.all()
    return render_template("shows.html", venues=venues)


@app.route("/admin/shows")
def admin_shows():
    venues = Venue.query.all()
    return render_template("admin_shows.html", venues=venues)


# @app.route('/reset_bookings/<int:show_id>')
# def reset_bookings(show_id):
#     show = Show.query.get_or_404(show_id)
#     Booking.query.filter_by(show_id=show_id).delete()
#     db.session.commit()
#     flash(f"All bookings reset for show '{show.name}'.", "success")
#     return redirect(url_for('admin_shows'))



@app.route('/admin_dashboard')
def admin_dashboard():
    venue_list = Venue.query.all()
    return render_template('venues.html', venues=venue_list, is_admin=True)


@app.route('/view_venues')
def view_venues():
    venue_list = Venue.query.all()
    return render_template('venues.html', venues=venue_list, is_admin=False)



@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("role", None)
    return redirect(url_for("login"))



def generate_ticket_barcode(data, booking_id):

    barcode_format = barcode.get_barcode_class('code128')
    code = barcode_format(data, writer=ImageWriter())
    path = os.path.join('static', 'barcodes')
    os.makedirs(path, exist_ok=True)
    filename = os.path.join(path, f'booking_{booking_id}')
    full_path = code.save(filename)
    return full_path.replace('\\', '/')



if __name__ == "__main__":
    app.run(debug = True, port = 5000)

