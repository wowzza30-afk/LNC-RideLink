import sqlite3


DATABASE = "ridelink.db"


def init_database():

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    # =========================
    # USERS
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        email TEXT UNIQUE NOT NULL,

        password TEXT NOT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    );
    """)

    # =========================
    # ACTIVE RIDES
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS active_pools (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        organizer TEXT NOT NULL,

        vehicle TEXT,

        role TEXT NOT NULL,

        start_point TEXT NOT NULL,

        end_point TEXT NOT NULL,

        ride_date TEXT,

        ride_time TEXT,

        seats_filled INTEGER DEFAULT 0,

        seats_total INTEGER DEFAULT 4,

        status TEXT DEFAULT 'Open',

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    );
    """)

    # =========================
    # AVAILABLE GROUPS
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS carpool_groups (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        organization TEXT,

        destination TEXT,

        departure_time TEXT,

        schedule TEXT,

        origin TEXT,

        match_percentage INTEGER DEFAULT 0,

        status TEXT DEFAULT 'Open',

        seats_filled INTEGER DEFAULT 0,

        seats_total INTEGER DEFAULT 4,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    );
    """)

    # =========================
    # GROUP MEMBERS
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS group_members (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER NOT NULL,

        group_id INTEGER NOT NULL,

        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


        FOREIGN KEY(user_id)
        REFERENCES users(id),


        FOREIGN KEY(group_id)
        REFERENCES carpool_groups(id)

    );
    """)

    connection.commit()

    connection.close()


    print(
        "RideLink database initialized successfully!"
    )

if __name__ == "__main__":

    init_database()