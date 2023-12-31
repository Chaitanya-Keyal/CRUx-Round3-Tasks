import json

import mysql.connector as msc

f = open("credentials.json", "r")
password = json.load(f)["password"]
f.close()

db = msc.connect(
    host="localhost",
    username="root",
    password=password,
    autocommit=True,
)

cursor = db.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS NewsAggregator")
cursor.execute("USE NewsAggregator")
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        password VARCHAR(255) NOT NULL,
        created_at DATETIME NOT NULL
    )
    """
)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS fav_topics (
        user_id INT NOT NULL,
        topic VARCHAR(255) NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """
)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS saved_articles (
        user_id INT NOT NULL,
        title VARCHAR(255) NOT NULL,
        link VARCHAR(255) NOT NULL,
        image VARCHAR(255) NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """
)
print("Created Database and Tables")
