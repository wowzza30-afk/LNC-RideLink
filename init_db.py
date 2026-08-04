import sqlite3

DATABASE = "ridelink.db"


def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    conn.execute("""
        PRAGMA foreign_keys = ON
    """)

    return conn


def init_database():

    conn = get_db()

    cursor = conn.cursor()

    # =========================
    # USERS (PARENTS)
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        email TEXT UNIQUE NOT NULL,

        password TEXT NOT NULL,

        phone TEXT,

        neighborhood TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )
    """)

    # =========================
    # CHILDREN
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS children(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        parent_id INTEGER NOT NULL,

        name TEXT NOT NULL,

        grade_level TEXT,

        campus TEXT,

        activities TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


        FOREIGN KEY(parent_id)

        REFERENCES users(id)

        ON DELETE CASCADE

    )
    """)

    # =========================
    # CARPOOLS
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS active_pools (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        driver_id INTEGER NOT NULL,

        child_id INTEGER NOT NULL,

        campus TEXT NOT NULL,

        ride_type TEXT NOT NULL,

        neighborhood TEXT NOT NULL,

        start_point TEXT NOT NULL,

        destination TEXT NOT NULL,

        departure_time TEXT NOT NULL,

        seats_total INTEGER NOT NULL,

        seats_filled INTEGER DEFAULT 1,

        status TEXT DEFAULT 'Open',

        monday INTEGER DEFAULT 0,
        tuesday INTEGER DEFAULT 0,
        wednesday INTEGER DEFAULT 0,
        thursday INTEGER DEFAULT 0,
        friday INTEGER DEFAULT 0,
        saturday INTEGER DEFAULT 0,
        sunday INTEGER DEFAULT 0,

        start_date TEXT NOT NULL,
        end_date TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(driver_id)
            REFERENCES users(id)
            ON DELETE CASCADE,

        FOREIGN KEY(child_id)
            REFERENCES children(id)
            ON DELETE CASCADE
    )
    """)

    # =========================
    # RIDE REQUESTS
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ride_requests(

        id INTEGER PRIMARY KEY AUTOINCREMENT,


        pool_id INTEGER NOT NULL,


        child_id INTEGER NOT NULL,


        parent_id INTEGER NOT NULL,


        status TEXT DEFAULT 'Pending',


        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,



        FOREIGN KEY(pool_id)

        REFERENCES active_pools(id)

        ON DELETE CASCADE,



        FOREIGN KEY(child_id)

        REFERENCES children(id)

        ON DELETE CASCADE,



        FOREIGN KEY(parent_id)

        REFERENCES users(id)

        ON DELETE CASCADE

    )
    """)

    # =========================
    # APPROVED MEMBERS
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ride_members(

        id INTEGER PRIMARY KEY AUTOINCREMENT,


        pool_id INTEGER NOT NULL,


        child_id INTEGER NOT NULL,


        parent_id INTEGER NOT NULL,


        status TEXT DEFAULT 'Approved',



        FOREIGN KEY(pool_id)

        REFERENCES active_pools(id)

        ON DELETE CASCADE,



        FOREIGN KEY(child_id)

        REFERENCES children(id)

        ON DELETE CASCADE,



        FOREIGN KEY(parent_id)

        REFERENCES users(id)

        ON DELETE CASCADE

    )
    """)

    # =========================
    # NOTIFICATIONS
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications(

        id INTEGER PRIMARY KEY AUTOINCREMENT,


        user_id INTEGER NOT NULL,


        message TEXT NOT NULL,


        seen INTEGER DEFAULT 0,


        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,



        FOREIGN KEY(user_id)

        REFERENCES users(id)

        ON DELETE CASCADE

    )
    """)

    # =========================
    # RIDE CHAT
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ride_messages(

        id INTEGER PRIMARY KEY AUTOINCREMENT,


        pool_id INTEGER NOT NULL,


        user_id INTEGER NOT NULL,


        message TEXT NOT NULL,


        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,



        FOREIGN KEY(pool_id)

        REFERENCES active_pools(id)

        ON DELETE CASCADE,



        FOREIGN KEY(user_id)

        REFERENCES users(id)

        ON DELETE CASCADE

    )
    """)

    conn.commit()

    conn.close()

    print("RideLink database initialized!")


if __name__ == "__main__":
    init_database()
