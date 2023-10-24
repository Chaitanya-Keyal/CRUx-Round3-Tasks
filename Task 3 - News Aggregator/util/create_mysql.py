import mysql.connector as msc

password = input("MySQL Password: ")
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
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """
)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS saved_articles (
        user_id INT NOT NULL,
        article_link VARCHAR(255) NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """
)
print("Created Database and Tables")
