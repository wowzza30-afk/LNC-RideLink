from flask import Flask, render_template, request, redirect, url_for, session, flash

from werkzeug.security import generate_password_hash, check_password_hash

import sqlite3
import os
from datetime import datetime

app = Flask(__name__, template_folder="templates", static_folder="static")

app.secret_key = os.environ.get("SECRET_KEY", "development-secret-key")

DATABASE = "ridelink.db"

# =========================
# DATABASE
# =========================


def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    conn.execute("""
        PRAGMA foreign_keys = ON
    """)

    return conn


def logged_in():

    if "user_id" not in session:
        return False

    conn = get_db()

    user = conn.execute(
        "SELECT id FROM users WHERE id=?", (session["user_id"],)
    ).fetchone()

    conn.close()

    if not user:
        session.clear()
        return False

    return True


# =========================
# HOME
# =========================


@app.route("/")
def home():

    print("HOME ROUTE HIT")
    print("SESSION:", session)
    print("LOGGED IN:", logged_in())

    if logged_in():
        print("REDIRECTING TO DASHBOARD")
        return redirect(url_for("dashboard"))

    print("SHOWING LANDING PAGE")
    return render_template("index.html")


# =========================
# LOGIN PAGE
# =========================


@app.route("/login")
def login_page():

    return render_template("login.html")


# =========================
# REGISTER PARENT
# =========================


@app.route("/register", methods=["GET", "POST"])
def register():

    name = request.form.get("name", "").strip()

    email = request.form.get("email", "").lower().strip()

    password = request.form.get("password", "")

    phone = request.form.get("phone", "")

    neighborhood = request.form.get("neighborhood", "")

    if not name or not email or not password:
        flash("Please complete all required fields.")

        return redirect(url_for("login_page"))

    conn = get_db()

    try:
        conn.execute(
            """
            INSERT INTO users(
                name,
                email,
                password,
                phone,
                neighborhood
            )

            VALUES(?,?,?,?,?)

        """,
            (name, email, generate_password_hash(password), phone, neighborhood),
        )

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()

        flash("Email already exists.")

        return redirect(url_for("login_page"))

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE email=?

    """,
        (email,),
    ).fetchone()

    conn.close()

    session["user_id"] = user["id"]

    session["user_name"] = user["name"]

    flash("Account created!")

    return redirect(url_for("dashboard"))


# =========================
# LOGIN
# =========================


@app.route("/login", methods=["POST"])
def login():

    email = request.form.get("email", "").lower().strip()

    password = request.form.get("password", "")

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE email=?

    """,
        (email,),
    ).fetchone()

    conn.close()

    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]

        session["user_name"] = user["name"]

        return redirect(url_for("dashboard"))

    flash("Invalid login.")

    return redirect(url_for("login_page"))


# =========================
# DASHBOARD
# =========================


@app.route("/dashboard")
def dashboard():

    print("SESSION:", session)
    print("LOGGED IN:", logged_in())

    if not logged_in():
        return redirect(url_for("login_page"))

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id=?

    """,
        (session["user_id"],),
    ).fetchone()

    children = conn.execute(
        """
        SELECT *
        FROM children

        WHERE parent_id=?

        ORDER BY id DESC

    """,
        (session["user_id"],),
    ).fetchall()

    rides = conn.execute(
        """
        SELECT

            active_pools.*,

            children.name AS child_name


        FROM active_pools


        JOIN children

        ON active_pools.child_id = children.id


        WHERE active_pools.driver_id=?


        ORDER BY id DESC


    """,
        (session["user_id"],),
    ).fetchall()

    ride_passengers = {}

    for ride in rides:
        passengers = conn.execute(
            """
            SELECT

                children.name

            FROM ride_members

            JOIN children
                ON ride_members.child_id = children.id

            WHERE ride_members.pool_id=?

            ORDER BY children.name
            """,
            (ride["id"],),
        ).fetchall()

        ride_passengers[ride["id"]] = passengers

    notifications = conn.execute(
        """
        SELECT *

        FROM notifications

        WHERE user_id=?

        ORDER BY id DESC

        LIMIT 5


    """,
        (session["user_id"],),
    ).fetchall()

    requests = conn.execute(
        """
        SELECT

            ride_requests.*,

            children.name AS child_name


        FROM ride_requests


        JOIN children

        ON ride_requests.child_id = children.id


        JOIN active_pools

        ON ride_requests.pool_id = active_pools.id


        WHERE active_pools.driver_id=?

        AND ride_requests.status='Pending'


    """,
        (session["user_id"],),
    ).fetchall()

    requests = conn.execute(
        """
        SELECT
            ride_requests.*,
            children.name AS child_name
        FROM ride_requests
        JOIN children
            ON ride_requests.child_id = children.id
        JOIN active_pools
            ON ride_requests.pool_id = active_pools.id
        WHERE active_pools.driver_id = ?
        AND ride_requests.status = 'Pending'
        """,
        (session["user_id"],),
    ).fetchall()

    joined_rides = conn.execute(
        """
        SELECT

            active_pools.*,

            users.name AS driver_name,

            children.name AS child_name


        FROM ride_members


        JOIN active_pools

        ON ride_members.pool_id = active_pools.id


        JOIN users

        ON active_pools.driver_id = users.id


        JOIN children

        ON active_pools.child_id = children.id


        WHERE ride_members.parent_id=?


        AND ride_members.status='Approved'


        ORDER BY active_pools.id DESC

        """,
        (session["user_id"],),
    ).fetchall()

    joined_passengers = {}

    for ride in joined_rides:
        passengers = conn.execute(
            """
            SELECT

                children.name,

                users.name AS parent_name

            FROM ride_members

            JOIN children
                ON ride_members.child_id = children.id

            JOIN users
                ON ride_members.parent_id = users.id

            WHERE ride_members.pool_id=?

            ORDER BY children.name
        """,
            (ride["id"],),
        ).fetchall()

        joined_passengers[ride["id"]] = passengers

    conn.close()

# =========================
# IMPACT METRICS
# =========================

    total_rides = len(rides)

    students_connected = 0

    for ride in rides:

        passengers = ride["seats_filled"] - 1

        if passengers > 0:
            students_connected += passengers

    money_saved = students_connected * 3
    co2_saved = students_connected * 12
    cars_removed = students_connected

    return render_template(
        "dashboard.html",
        user=user,
        children=children,
        rides=rides,
        ride_passengers=ride_passengers,
        joined_passengers=joined_passengers,
        requests=requests,
        notifications=notifications,
        total_rides=total_rides,
        students=students_connected,
        co2_saved=co2_saved,
        money_saved=money_saved,
        joined_rides=joined_rides,
        cars_removed=cars_removed,
    )


# =========================
# ADD CHILD
# =========================


@app.route("/add-child")
def add_child_page():

    if not logged_in():
        return redirect(url_for("login_page"))

    return render_template("add-child.html")


@app.route("/add-child", methods=["POST"])
def add_child():

    if not logged_in():
        return redirect(url_for("login_page"))

    name = request.form.get("name", "")

    grade = request.form.get("grade_level", "")

    campus = request.form.get("campus", "")

    activities = request.form.get("activities", "")

    if not name:
        flash("Child name required.")

        return redirect(url_for("add_child_page"))

    conn = get_db()

    conn.execute(
        """
        INSERT INTO children(

            parent_id,

            name,

            grade_level,

            campus,

            activities

        )

        VALUES(?,?,?,?,?)

    """,
        (session["user_id"], name, grade, campus, activities),
    )

    conn.commit()

    conn.close()

    flash("Child added!")

    return redirect(url_for("dashboard"))


# =========================
# EDIT CHILD
# =========================


@app.route("/edit-child/<int:child_id>")
def edit_child_page(child_id):

    if not logged_in():
        return redirect(url_for("login_page"))

    conn = get_db()

    child = conn.execute(
        """
        SELECT *
        FROM children
        WHERE id=? AND parent_id=?
    """,
        (child_id, session["user_id"]),
    ).fetchone()

    conn.close()

    if not child:
        flash("Child not found.")
        return redirect(url_for("dashboard"))

    return render_template("edit-child.html", child=child)


@app.route("/edit-child/<int:child_id>", methods=["POST"])
def edit_child(child_id):

    if not logged_in():
        return redirect(url_for("login_page"))

    conn = get_db()

    conn.execute(
        """
        UPDATE children
        SET
            name=?,
            grade_level=?,
            campus=?,
            activities=?
        WHERE id=? AND parent_id=?
    """,
        (
            request.form["name"],
            request.form["grade_level"],
            request.form["campus"],
            request.form["activities"],
            child_id,
            session["user_id"],
        ),
    )

    conn.commit()
    conn.close()

    flash("Child updated!")

    return redirect(url_for("dashboard"))


# =========================
# DELETE CHILD
# =========================


@app.route("/delete-child/<int:child_id>", methods=["POST"])
def delete_child(child_id):

    if not logged_in():
        return redirect(url_for("login_page"))

    conn = get_db()

    conn.execute(
        """
        DELETE FROM children
        WHERE id=? AND parent_id=?
    """,
        (child_id, session["user_id"]),
    )

    conn.commit()
    conn.close()

    flash("Child deleted.")

    return redirect(url_for("dashboard"))


# =========================
# CREATE RIDE PAGE
# =========================


@app.route("/create-ride")
def create_ride_page():

    if not logged_in():
        return redirect(url_for("login_page"))

    conn = get_db()

    children = conn.execute(
        """
        SELECT *

        FROM children

        WHERE parent_id=?


    """,
        (session["user_id"],),
    ).fetchall()

    conn.close()

    return render_template("create-ride.html", children=children)


# =========================
# CREATE RIDE
# =========================


@app.route("/create-ride", methods=["POST"])
def create_ride():

    if not logged_in():
        return redirect(url_for("login_page"))

    child_id = request.form["child_id"]

    neighborhood = request.form["neighborhood"]

    campus = request.form["campus"]

    ride_type = request.form["ride_type"]

    if ride_type == "Morning Drop-off":
        start_point = neighborhood
        destination = campus

    elif ride_type == "Afternoon Dismissal":
        start_point = campus
        destination = neighborhood

    departure_time = request.form["departure_time"]

    seats = int(request.form["seats"])

    # Weekly schedule
    monday = 1 if request.form.get("monday") else 0
    tuesday = 1 if request.form.get("tuesday") else 0
    wednesday = 1 if request.form.get("wednesday") else 0
    thursday = 1 if request.form.get("thursday") else 0
    friday = 1 if request.form.get("friday") else 0
    saturday = 1 if request.form.get("saturday") else 0
    sunday = 1 if request.form.get("sunday") else 0

    start_date = request.form["start_date"]
    end_date = request.form.get("end_date")

    conn = get_db()

    # Verify the child belongs to the logged-in parent
    child = conn.execute(
        """
        SELECT *
        FROM children
        WHERE id=? AND parent_id=?
        """,
        (child_id, session["user_id"]),
    ).fetchone()

    if not child:
        conn.close()
        flash("Invalid child selected.")
        return redirect(url_for("create_ride_page"))

    if not any([monday, tuesday, wednesday, thursday, friday, saturday, sunday]):
        flash("Please select at least one day of the week.")
        conn.close()
        return redirect(url_for("create_ride_page"))

    conn.execute(
        """
        INSERT INTO active_pools(

            driver_id,
            child_id,
            campus,
            ride_type,
            neighborhood,
            start_point,
            destination,
            departure_time,
            seats_total,
            seats_filled,
            status,

            monday,
            tuesday,
            wednesday,
            thursday,
            friday,
            saturday,
            sunday,

            start_date,
            end_date

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            session["user_id"],
            child_id,
            campus,
            ride_type,
            neighborhood,
            start_point,
            destination,
            departure_time,
            seats,
            1,
            "Open",
            monday,
            tuesday,
            wednesday,
            thursday,
            friday,
            saturday,
            sunday,
            start_date,
            end_date,
        ),
    )

    conn.commit()
    conn.close()

    flash("Recurring carpool created!")

    return redirect(url_for("dashboard"))


# =========================
# TIME FILTER
# =========================


@app.template_filter("time12")
def time12(value):
    return datetime.strptime(value, "%H:%M").strftime("%I:%M %p").lstrip("0")


# =========================
# FIND RIDES
# =========================


@app.route("/find-rides")
def find_rides():

    if not logged_in():
        return redirect(url_for("login_page"))

    campus = request.args.get("campus", "")

    neighborhood = request.args.get("neighborhood", "")

    ride_type = request.args.get("ride_type", "")

    conn = get_db()

    query = """

    SELECT

        active_pools.*,

        users.name AS driver_name,

        children.name AS child_name


    FROM active_pools


    JOIN users

    ON active_pools.driver_id = users.id


    JOIN children

    ON active_pools.child_id = children.id


    WHERE status='Open'

    AND active_pools.driver_id != ?


    """

    params = [session["user_id"]]

    if campus:
        query += """
        AND active_pools.campus=?
        """

        params.append(campus)

    if neighborhood:
        query += """
        AND active_pools.neighborhood=?
        """

        params.append(neighborhood)

    if ride_type:
        query += """
        AND active_pools.ride_type=?
        """

        params.append(ride_type)

    query += """
        ORDER BY active_pools.id DESC
    """

    rides = conn.execute(query, params).fetchall()

    children = conn.execute(
        """
        SELECT *

        FROM children

        WHERE parent_id=?

    """,
        (session["user_id"],),
    ).fetchall()

    conn.close()

    return render_template("find-rides.html", rides=rides, children=children)


# =========================
# EDIT RIDE
# =========================


@app.route("/edit-ride/<int:ride_id>")
def edit_ride_page(ride_id):

    if not logged_in():
        return redirect(url_for("login_page"))

    conn = get_db()

    ride = conn.execute(
        """
        SELECT *
        FROM active_pools
        WHERE id=? AND driver_id=?
    """,
        (ride_id, session["user_id"]),
    ).fetchone()

    conn.close()

    if not ride:
        flash("Ride not found.")
        return redirect(url_for("dashboard"))

    return render_template("edit-ride.html", ride=ride)


@app.route("/edit-ride/<int:ride_id>", methods=["POST"])
def edit_ride(ride_id):

    if not logged_in():
        return redirect(url_for("login_page"))

    conn = get_db()

    conn.execute(
        """
        UPDATE active_pools
        SET

            campus=?,
            neighborhood=?,
            departure_time=?,
            seats_total=?

        WHERE id=?
        AND driver_id=?

    """,
        (
            request.form["campus"],
            request.form["neighborhood"],
            request.form["departure_time"],
            request.form["seats"],
            ride_id,
            session["user_id"],
        ),
    )

    conn.commit()
    conn.close()

    flash("Ride updated!")

    return redirect(url_for("dashboard"))


# =========================
# DELETE RIDE
# =========================


@app.route("/delete-ride/<int:ride_id>", methods=["POST"])
def delete_ride(ride_id):

    if not logged_in():
        return redirect(url_for("login_page"))

    conn = get_db()

    conn.execute(
        """
        DELETE FROM active_pools
        WHERE id=?
        AND driver_id=?
    """,
        (ride_id, session["user_id"]),
    )

    conn.commit()
    conn.close()

    flash("Ride deleted.")

    return redirect(url_for("dashboard"))


# =========================
# REQUEST RIDE
# =========================


@app.route("/request-ride/<int:pool_id>", methods=["POST"])
def request_ride(pool_id):

    if not logged_in():
        return redirect(url_for("login_page"))

    child_id = request.form.get("child_id")

    conn = get_db()

    child = conn.execute(
        """
        SELECT *

        FROM children

        WHERE id=?

        AND parent_id=?

    """,
        (child_id, session["user_id"]),
    ).fetchone()

    if not child:
        conn.close()

        flash("Invalid child.")

        return redirect(url_for("find_rides"))

    existing = conn.execute(
        """
        SELECT *

        FROM ride_requests

        WHERE pool_id=?

        AND child_id=?

        AND status='Pending'

    """,
        (pool_id, child_id),
    ).fetchone()

    if existing:
        conn.close()

        flash("Request already sent.")

        return redirect(url_for("find_rides"))

    conn.execute(
        """
        INSERT INTO ride_requests(

            pool_id,

            child_id,

            parent_id,

            status

        )

        VALUES(?,?,?,?)

    """,
        (pool_id, child_id, session["user_id"], "Pending"),
    )

    driver = conn.execute(
        """
        SELECT driver_id

        FROM active_pools

        WHERE id=?

    """,
        (pool_id,),
    ).fetchone()

    conn.execute(
        """
        INSERT INTO notifications(

            user_id,

            message

        )

        VALUES(?,?)

    """,
        (driver["driver_id"], "New ride request received."),
    )

    conn.commit()

    conn.close()

    flash("Ride request sent.")

    return redirect(url_for("find_rides"))


# =========================
# APPROVE REQUEST
# =========================


@app.route("/approve-request/<int:request_id>", methods=["POST"])
def approve_request(request_id):

    if not logged_in():
        return redirect(url_for("login_page"))

    conn = get_db()

    req = conn.execute(
        """
        SELECT *

        FROM ride_requests

        WHERE id=?

    """,
        (request_id,),
    ).fetchone()

    if not req:
        conn.close()

        return redirect(url_for("dashboard"))

    conn.execute(
        """
        UPDATE ride_requests

        SET status='Approved'

        WHERE id=?

    """,
        (request_id,),
    )

    conn.execute(
        """
        INSERT INTO ride_members(

            pool_id,

            child_id,

            parent_id,

            status

        )

        VALUES(?,?,?,?)

    """,
        (req["pool_id"], req["child_id"], req["parent_id"], "Approved"),
    )

    conn.execute(
        """
        UPDATE active_pools

        SET seats_filled =
        seats_filled + 1

        WHERE id=?

    """,
        (req["pool_id"],),
    )

    conn.execute(
        """
        INSERT INTO notifications(

            user_id,

            message

        )

        VALUES(?,?)

    """,
        (req["parent_id"], "Your ride request was approved."),
    )

    conn.commit()

    conn.close()

    flash("Request approved.")

    return redirect(url_for("dashboard"))


# =========================
# REJECT REQUEST
# =========================


@app.route("/reject-request/<int:request_id>", methods=["POST"])
def reject_request(request_id):

    if not logged_in():
        return redirect(url_for("login_page"))

    conn = get_db()

    req = conn.execute(
        """
        SELECT parent_id

        FROM ride_requests

        WHERE id=?

    """,
        (request_id,),
    ).fetchone()

    conn.execute(
        """
        UPDATE ride_requests

        SET status='Rejected'

        WHERE id=?

    """,
        (request_id,),
    )

    conn.execute(
        """
        INSERT INTO notifications(

            user_id,

            message

        )

        VALUES(?,?)

    """,
        (req["parent_id"], "Your ride request was rejected."),
    )

    conn.commit()

    conn.close()

    flash("Request rejected.")

    return redirect(url_for("dashboard"))


# =========================
# RIDE CHAT
# =========================


@app.route("/ride-chat/<int:pool_id>")
def ride_chat(pool_id):

    if not logged_in():
        return redirect(url_for("login_page"))

    conn = get_db()

    ride = conn.execute(
        """
        SELECT

        active_pools.*,

        users.name AS driver_name,

        children.name AS child_name


        FROM active_pools


        JOIN users

        ON active_pools.driver_id = users.id


        JOIN children

        ON active_pools.child_id = children.id


        WHERE active_pools.id=?


    """,
        (pool_id,),
    ).fetchone()

    if not ride:
        conn.close()

        flash("Ride not found.")

        return redirect(url_for("dashboard"))

    messages = conn.execute(
        """
        SELECT

        ride_messages.*,

        users.name


        FROM ride_messages


        JOIN users

        ON ride_messages.user_id = users.id


        WHERE pool_id=?


        ORDER BY id ASC


    """,
        (pool_id,),
    ).fetchall()

    conn.close()

    return render_template(
        "ride-chat.html", ride=ride, messages=messages, pool_id=pool_id
    )


@app.route("/ride-chat/<int:pool_id>/send", methods=["POST"])
def send_message(pool_id):

    if not logged_in():
        return redirect(url_for("login_page"))

    message = request.form.get("message", "").strip()

    if message:
        conn = get_db()

        conn.execute(
            """
            INSERT INTO ride_messages(

                pool_id,

                user_id,

                message

            )

            VALUES(?,?,?)

        """,
            (pool_id, session["user_id"], message),
        )

        conn.commit()

        conn.close()

    return redirect(url_for("ride_chat", pool_id=pool_id))


# =========================
# LOGOUT
# =========================


@app.route("/logout")
def logout():

    session.clear()

    print("AFTER LOGOUT:", session)

    flash("Logged out.")

    return redirect(url_for("home"))


# =========================
# ERROR HANDLING
# =========================


@app.errorhandler(404)
def page_not_found(error):

    return redirect(url_for("home"))


@app.errorhandler(500)
def server_error(error):

    flash("Something went wrong.")

    if logged_in():
        return redirect(url_for("dashboard"))

    return redirect(url_for("home"))


# =========================
# PROFILE
# =========================


@app.route("/profile")
def profile():

    if not logged_in():
        return redirect(url_for("login_page"))

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id=?

    """,
        (session["user_id"],),
    ).fetchone()

    return render_template("profile.html", user=user)


# =========================
# START SERVER
# =========================


if __name__ == "__main__":
    app.run(debug=True)
