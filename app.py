from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os


# =====================================================
# FLASK CONFIGURATION
# =====================================================

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

# Use environment variable in production
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key-change-this"
)


# =====================================================
# DATABASE CONNECTION
# =====================================================

DATABASE = "ridelink.db"


def get_db_connection():
    """
    Creates SQLite database connection.
    Row factory allows accessing columns by name:
    user["email"] instead of user[1]
    """

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    return conn



# =====================================================
# HOME PAGE
# =====================================================

@app.route("/")
def home():
    return render_template("index.html")



# =====================================================
# AUTHENTICATION PAGE
# =====================================================

@app.route("/login")
def login_page():
    """
    Displays login/register page.
    """

    return render_template("login.html")



# =====================================================
# REGISTER USER
# =====================================================

@app.route("/register", methods=["POST"])
def handle_register():

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")


    if not name or not email or not password:
        flash("Please fill out all registration fields.")
        return redirect(url_for("login_page"))



    # Hash password before storing
    hashed_password = generate_password_hash(password)



    conn = get_db_connection()


    try:

        conn.execute(
            """
            INSERT INTO users
            (name, email, password)

            VALUES (?, ?, ?)
            """,

            (
                name,
                email,
                hashed_password
            )
        )


        conn.commit()



        # Get newly created user

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,

            (email,)
        ).fetchone()



        session["user_id"] = user["id"]
        session["user_name"] = user["name"]


        flash("Account created successfully!")

        return redirect(
            url_for("dashboard")
        )



    except sqlite3.IntegrityError:

        flash(
            "An account with this email already exists."
        )

        return redirect(
            url_for("login_page")
        )



    finally:

        conn.close()





# =====================================================
# LOGIN USER
# =====================================================

@app.route("/login", methods=["POST"])
def handle_login():

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")



    conn = get_db_connection()



    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,

        (email,)
    ).fetchone()



    conn.close()



    if user and check_password_hash(
        user["password"],
        password
    ):


        session["user_id"] = user["id"]
        session["user_name"] = user["name"]


        flash(
            "Welcome back!"
        )


        return redirect(
            url_for("dashboard")
        )



    else:

        flash(
            "Invalid email or password."
        )


        return redirect(
            url_for("login_page")
        )




# =====================================================
# LOGOUT
# =====================================================

@app.route("/logout")
def handle_logout():

    session.clear()


    flash(
        "You have been logged out."
    )


    return redirect(
        url_for("home")
    )

# =====================================================
# DASHBOARD
# =====================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        flash(
            "Please log in to access your dashboard."
        )
        return redirect(
            url_for("login_page")
        )


    conn = get_db_connection()


    # Get active pools
    pools = conn.execute(
        """
        SELECT *
        FROM active_pools
        ORDER BY id DESC
        """
    ).fetchall()



    # Calculate real statistics

    active_pool_count = len(pools)


    total_seats = sum(
        pool["seats_total"]
        for pool in pools
    )


    occupied_seats = sum(
        pool["seats_filled"]
        for pool in pools
    )


    available_seats = (
        total_seats - occupied_seats
    )



    # Estimate environmental impact
    # Each shared ride saves approximately fuel emissions

    co2_saved = occupied_seats * 12

    gas_saved = occupied_seats * 4.25



    metrics = {

        "active_pools": active_pool_count,

        "total_riders": occupied_seats,

        "available_seats": available_seats,

        "co2_saved": co2_saved,

        "gas_saved": round(
            gas_saved,
            2
        )
    }



    conn.close()



    return render_template(
        "dashboard.html",
        metrics=metrics,
        pools=pools
    )




# =====================================================
# MATCHING ALGORITHM
# =====================================================

def calculate_match(user_preferences, group):

    """
    Calculates compatibility score.

    Factors:

    Organization 40%
    Destination 30%
    Departure time 20%
    Availability 10%

    """

    score = 0



    # Organization match

    if (
        user_preferences.get("organization")
        and
        user_preferences["organization"].lower()
        in group["organization"].lower()
    ):

        score += 40



    # Destination match

    if (
        user_preferences.get("destination")
        and
        user_preferences["destination"].lower()
        in group["destination"].lower()
    ):

        score += 30




    # Time match

    if (
        user_preferences.get("departure_time")
        ==
        group["departure_time"]
    ):

        score += 20




    # Open seats

    if (
        group["seats_filled"]
        <
        group["seats_total"]
    ):

        score += 10

    return score


# =====================================================
# FIND GROUP PAGE
# =====================================================

@app.route("/find-group")
def find_group():

    if "user_id" not in session:

        flash(
            "Please log in to browse groups."
        )

        return redirect(
            url_for("login_page")
        )



    organization = request.args.get(
        "org_search",
        ""
    ).strip()



    shift_time = request.args.get(
        "shift_time",
        "Any Shift Time"
    )



    conn = get_db_connection()



    query = """
        SELECT *
        FROM carpool_groups
        WHERE 1=1
    """


    params = []



    if organization:

        query += """
        AND (
            organization LIKE ?
            OR name LIKE ?
        )
        """

        params.extend(
            [
                f"%{organization}%",
                f"%{organization}%"
            ]
        )



    if (
        shift_time !=
        "Any Shift Time"
    ):

        if "Morning" in shift_time:

            query += """
            AND departure_time
            LIKE '07%'
            """

        elif "Afternoon" in shift_time:

            query += """
            AND departure_time
            LIKE '12%'
            """

        elif "Evening" in shift_time:

            query += """
            AND departure_time
            LIKE '04%'
            """


    groups = conn.execute(
        query,
        params
    ).fetchall()


    conn.close()


    return render_template(
        "find-group.html",
        groups=groups
    )


# =====================================================
# CREATE A CARPOOL
# =====================================================

@app.route("/publish", methods=["POST"])
def publish_route():

    if "user_id" not in session:

        return redirect(
            url_for("login_page")
        )



    role = request.form.get(
        "role"
    )


    start_point = request.form.get(
        "start_point"
    )


    destination = request.form.get(
        "end_point"
    )


    ride_date = request.form.get(
        "ride_date"
    )


    ride_time = request.form.get(
        "ride_time"
    )


    seats = request.form.get(
        "seats",
        type=int
    )

    # Format date

    try:

        ride_date = datetime.strptime(
            ride_date,
            "%Y-%m-%d"
        ).strftime(
            "%b %d, %Y"
        )

    except:

        pass

    # Format time

    try:

        ride_time = datetime.strptime(
            ride_time,
            "%H:%M"
        ).strftime(
            "%I:%M %p"
        )

    except:

        pass

    conn = get_db_connection()

    conn.execute(
        """
        INSERT INTO active_pools

        (
        organizer,
        vehicle,
        role,
        start_point,
        end_point,
        ride_date,
        ride_time,
        seats_filled,
        seats_total,
        status
        )


        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """,

        (

        session["user_name"],

        request.form.get(
            "vehicle",
            "Unknown Vehicle"
        ),

        role,

        start_point,

        destination,

        ride_date,

        ride_time,


        1 if role == "passenger" else 0,


        seats,


        "Open"

        )

    )

    conn.commit()

    conn.close()

    flash(
        "Your carpool has been published!"
    )


    return redirect(
        url_for("dashboard")
    )


# =====================================================
# REQUEST TO JOIN GROUP
# =====================================================

@app.route(
    "/join-group/<int:group_id>",
    methods=["POST"]
)
def join_group(group_id):


    if "user_id" not in session:

        return redirect(
            url_for("login_page")
        )

    conn = get_db_connection()

    group = conn.execute(
        """
        SELECT *
        FROM carpool_groups
        WHERE id = ?
        """,

        (group_id,)
    ).fetchone()

    if not group:

        flash(
            "Group does not exist."
        )

        conn.close()

        return redirect(
            url_for("find_group")
        )

    if (
        group["seats_filled"]
        >=
        group["seats_total"]
    ):

        flash(
            "This group is already full."
        )

        conn.close()

        return redirect(
            url_for("find_group")
        )

    conn.execute(
        """
        UPDATE carpool_groups

        SET seats_filled =
        seats_filled + 1

        WHERE id = ?

        """,

        (group_id,)
    )

    conn.commit()

    conn.close()


    flash(
        "You successfully joined this carpool!"
    )

    return redirect(
        url_for("dashboard")
    )


# =====================================================
# CANCEL CARPOOL
# =====================================================

@app.route(
    "/cancel-pool/<int:pool_id>",
    methods=["POST"]
)
def cancel_pool(pool_id):

    if "user_id" not in session:

        return redirect(
            url_for("login_page")
        )



    conn = get_db_connection()



    pool = conn.execute(
        """
        SELECT *
        FROM active_pools
        WHERE id = ?
        """,

        (pool_id,)
    ).fetchone()



    if not pool:

        flash(
            "Carpool not found."
        )

        conn.close()

        return redirect(
            url_for("dashboard")
        )



    # Only owner can delete ride

    if (
        pool["organizer"]
        !=
        session["user_name"]
    ):

        flash(
            "You cannot cancel another user's ride."
        )

        conn.close()

        return redirect(
            url_for("dashboard")
        )



    conn.execute(
        """
        DELETE FROM active_pools
        WHERE id = ?
        """,

        (pool_id,)
    )


    conn.commit()

    conn.close()



    flash(
        "Carpool successfully cancelled."
    )



    return redirect(
        url_for("dashboard")
    )





# =====================================================
# LEAVE GROUP
# =====================================================

@app.route(
    "/leave-group/<int:group_id>",
    methods=["POST"]
)
def leave_group(group_id):


    if "user_id" not in session:

        return redirect(
            url_for("login_page")
        )



    conn = get_db_connection()



    group = conn.execute(
        """
        SELECT *
        FROM carpool_groups
        WHERE id = ?
        """,

        (group_id,)
    ).fetchone()



    if not group:

        flash(
            "Group not found."
        )

        conn.close()

        return redirect(
            url_for("dashboard")
        )



    if group["seats_filled"] > 0:


        conn.execute(
            """
            UPDATE carpool_groups

            SET seats_filled =
            seats_filled - 1

            WHERE id = ?

            """,

            (group_id,)
        )


        conn.commit()


        flash(
            "You left the carpool group."
        )


    else:

        flash(
            "You are not currently in this group."
        )



    conn.close()



    return redirect(
        url_for("dashboard")
    )





# =====================================================
# UPDATE GROUP STATUS
# =====================================================

def update_group_status():

    """
    Automatically changes groups:

    Open
    ↓
    Full

    when seats run out.
    """


    conn = get_db_connection()



    conn.execute(
        """
        UPDATE carpool_groups

        SET status = 'Full'

        WHERE seats_filled >= seats_total

        """
    )



    conn.execute(
        """
        UPDATE carpool_groups

        SET status = 'Open'

        WHERE seats_filled < seats_total

        """
    )


    conn.commit()

    conn.close()





# =====================================================
# DATABASE INITIALIZATION CHECK
# =====================================================

@app.before_request
def before_request():

    """
    Runs before every request.

    Keeps group statuses updated.
    """

    update_group_status()





# =====================================================
# ERROR HANDLERS
# =====================================================

@app.errorhandler(404)
def page_not_found(error):

    return (
        render_template(
            "404.html"
        ),
        404
    )



@app.errorhandler(500)
def internal_error(error):

    flash(
        "Something went wrong. Please try again."
    )

    return redirect(
        url_for("home")
    )





# =====================================================
# START APPLICATION
# =====================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )