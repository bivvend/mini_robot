import sqlite3

db_path = "data/memory.db"

with sqlite3.connect(db_path) as db:
    db.execute("ALTER TABLE robot_interests RENAME TO robot_interests_old")

    db.execute("""
        CREATE TABLE robot_interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robot_name TEXT NOT NULL COLLATE NOCASE,
            topic TEXT NOT NULL COLLATE NOCASE,
            enthusiasm REAL NOT NULL DEFAULT 0.5,
            curiosity REAL NOT NULL DEFAULT 0.5,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(robot_name, topic)
        )
    """)

    db.execute("""
        INSERT INTO robot_interests
        (id, robot_name, topic, enthusiasm, curiosity,
         description, created_at, updated_at)
        SELECT id, 'Mini', topic, enthusiasm, curiosity,
               description, created_at, updated_at
        FROM robot_interests_old
    """)

    db.execute("DROP TABLE robot_interests_old")