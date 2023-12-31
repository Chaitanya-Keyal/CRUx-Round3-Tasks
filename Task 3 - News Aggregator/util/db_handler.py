import base64
import datetime
import json
import os

import bcrypt
import mysql.connector as msc

f = open("credentials.json", "r")
PASSWORD = json.load(f)["password"]
f.close()

HOST = "localhost"
USERNAME = "root"


PFP_PATH = "pfp"


class Database:
    def __init__(self):
        self.db = msc.connect(
            host=HOST,
            username=USERNAME,
            password=PASSWORD,
            database="NewsAggregator",
            autocommit=True,
        )

    def execute(self, query, multi=False):
        """
        Executes the query and returns the response

        Args:
            query (str): Query to be executed
            multi (bool, optional): If the query is multi-statement. Defaults to False.

        Returns:
            list: Response from the database
        """
        while True:
            try:
                cursor = self.db.cursor()
                response = []
                if multi:
                    for result in cursor.execute(query, multi=True):
                        if result.with_rows:
                            print(result.fetchall())
                else:
                    cursor.execute(query)
                    response = cursor.fetchall()
                cursor.close()
                return response

            except msc.OperationalError:
                self.db = msc.connect(
                    host=HOST,
                    username=USERNAME,
                    password=PASSWORD,
                    database="NewsAggregator",
                    autocommit=True,
                )
            except Exception as e:
                print(f'{e} avoided, Query was "{query}"')
                return None

    def data_change(self, query, multi=True):
        """
        Executes the query and commits the changes for data manipulation queries

        Args:
            query (str): Query to be executed
            multi (bool, optional): If the query is multi-statement. Defaults to True.
        Returns:
            None
        """
        try:
            self.execute(query, multi=multi)
            self.db.commit()
        except:
            self.db.rollback()


db = Database()


def register(username, password, pfp):
    """
    Registers the user

    Args:
        username (str): Username
        password (str): Password
        pfp (str): Base64 encoded image
    Returns:
        str: Success or Error message
    """
    password = password.encode("utf-8")
    count = db.execute(f"SELECT * FROM users WHERE username = '{username}'")
    if len(count):
        return "Username already exists"
    password = str(bcrypt.hashpw(password, bcrypt.gensalt()))[2:-1]
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.data_change(
        f'INSERT INTO users (username, password, created_at) VALUES ("{username}", "{password}", "{created_at}")'
    )
    save_img(pfp, username)
    return "Success"


def do_login(username, password, remember_me=False, remember_login=False):
    """
    Checks the login credentials

    Args:
        username (str): Username
        password (str): Password
        remember_me (bool, optional): If the user has checked remember me. Defaults to False.

    Returns:
        str: Success or Error message
    """
    if remember_login:
        r = hashed_login(username, password)
    else:
        r = login(username, password)
    if r == "Success":
        if remember_me:
            return (
                "Success",
                db.execute(f"SELECT password FROM users WHERE username='{username}'")[
                    0
                ][0],
            )
        return "Success", None
    return r, None


def login(username, password):
    """
    Logs in the user

    Args:
        username (str): Username
        password (str): Password

    Returns:
        str: Success or Error message
    """
    password = password.encode("utf-8")
    storedpw = db.execute(f"SELECT password FROM users WHERE username='{username}'")
    if len(storedpw) and bcrypt.checkpw(password, storedpw[0][0].encode("utf-8")):
        return "Success"
    return "Either username or password is incorrect"


def hashed_login(username, hashed_password):
    """
    Logs in the user when the user has checked remember me

    Args:
        username (str): Username
        hashed_password (str): Hashed password

    Returns:
        str: Success or Error message
    """
    storedpw = db.execute(f"SELECT password FROM users WHERE username='{username}'")
    if len(storedpw) and hashed_password == storedpw[0][0]:
        return "Success"
    return "Either username or password is incorrect"


def change_password(username, new_password):
    """
    Changes the password of the user

    Args:
        username (str): Username
        new_password (str): New Password

    Returns:
        str: Success or Error message
    """
    # old_password = old_password.encode("utf-8")
    new_password = new_password.encode("utf-8")
    # storedpw = db.execute(f"SELECT password FROM users WHERE username='{username}'")
    # if len(storedpw) and bcrypt.checkpw(old_password, storedpw[0][0].encode("utf-8")):
    #     p = str(bcrypt.hashpw(new_password, bcrypt.gensalt()))[2:-1]
    #     db.data_change(f'UPDATE users SET password="{p}" WHERE username="{username}"')
    #     return "Success"
    # return "Password is incorrect"
    p = str(bcrypt.hashpw(new_password, bcrypt.gensalt()))[2:-1]
    db.data_change(f'UPDATE users SET password="{p}" WHERE username="{username}"')
    return "Success"


# region Profile Picture


def fetch_pfp(name):
    """
    Fetches the pfp of the user

    Args:
        name (str): Username

    Returns:
        str: Base64 encoded image
    """
    pfp = load_img(name)
    if not pfp:
        return "User not found"
    return pfp


def change_pfp(username, new_pfp):
    """
    Changes the pfp of the user

    Args:
        username (str): Username
        new_pfp (str): Base64 encoded image

    Returns:
        str: Success or Error message
    """
    save_img(new_pfp, username)
    return "Success"


def save_img(img, user):
    try:
        with open(os.path.join(PFP_PATH, f"{user}_pfp.png"), "wb") as f:
            f.write(base64.b64decode(img.encode("latin1")))
    except Exception as e:
        print("Error while saving image:", e)


def load_img(user):
    if os.path.isfile(os.path.join(PFP_PATH, f"{user}_pfp.png")):
        try:
            with open(os.path.join(PFP_PATH, f"{user}_pfp.png"), "rb") as f:
                return base64.b64encode(f.read()).decode("latin1")
        except Exception as e:
            print("Error while loading image:", e)
    else:
        try:
            with open(os.path.join(PFP_PATH, f"default_pfp.png"), "rb") as f:
                with open(os.path.join(PFP_PATH, f"{user}_pfp.png"), "wb") as f2:
                    f2.write(f.read())
                f.seek(0)
                return base64.b64encode(f.read()).decode("latin1")
        except Exception as e:
            print("Error while loading image:", e)


# endregion


# region Articles


def save_article(username, title, link, image):
    """
    Saves the article for the user

    Args:
        username (str): Username
        title (str): Title of the article
        link (str): Link of the article
        image (str): Link of the image

    Returns:
        str: Success or Error message
    """
    db.data_change(
        f'INSERT INTO saved_articles (user_id, title, link, image) VALUES ((SELECT id FROM users WHERE username="{username}"), "{title}", "{link}", "{image}")'
    )
    return "Success"


def unsave_article(username, link):
    """
    Deletes the article for the user

    Args:
        username (str): Username
        link (str): Link of the article

    Returns:
        str: Success or Error message
    """
    db.data_change(
        f'DELETE FROM saved_articles WHERE user_id=(SELECT id FROM users WHERE username="{username}") AND link="{link}"'
    )
    return "Success"


def is_saved_article(username, link):
    """
    Checks if the article is saved for the user

    Args:
        username (str): Username
        link (str): Link of the article

    Returns:
        bool: True if the article is saved, False otherwise
    """
    res = db.execute(
        f'SELECT * FROM saved_articles WHERE user_id=(SELECT id FROM users WHERE username="{username}") AND link="{link}"'
    )
    return len(res) > 0


def get_saved_articles(username):
    """
    Gets the saved articles for the user

    Args:
        username (str): Username

    Returns:
        list: List of saved articles
    """
    res = db.execute(
        f'SELECT title, link, image FROM saved_articles WHERE user_id=(SELECT id FROM users WHERE username="{username}")'
    )
    return [{"title": i[0], "link": i[1], "image": i[2]} for i in res] if res else []


# endregion


# region Topics


def update_topics(username, topics):
    """
    Updates the topics for the user

    Args:
        username (str): Username
        topics (list): List of topics

    Returns:
        str: Success or Error message
    """
    db.data_change(
        f"DELETE FROM fav_topics WHERE user_id=(SELECT id FROM users WHERE username='{username}')"
    )
    for topic in topics:
        db.data_change(
            f'INSERT INTO fav_topics (user_id, topic) VALUES ((SELECT id FROM users WHERE username="{username}"), "{topic}")'
        )
    return "Success"


def save_topic(username, topic):
    """
    Adds the saved topic for the user

    Args:
        username (str): Username
        topic (str): Topic to be saved

    Returns:
        str: Success or Error message
    """
    db.data_change(
        f'INSERT INTO fav_topics (user_id, topic) VALUES ((SELECT id FROM users WHERE username="{username}"), "{topic}")'
    )
    return "Success"


def unsave_topic(username, topic):
    """
    Deletes the saved topic for the user

    Args:
        username (str): Username
        topic (str): Topic to be deleted

    Returns:
        str: Success or Error message
    """
    db.data_change(
        f'DELETE FROM fav_topics WHERE user_id=(SELECT id FROM users WHERE username="{username}") AND topic="{topic}"'
    )
    return "Success"


def is_saved_topic(username, topic):
    """
    Checks if the topic is saved for the user

    Args:
        username (str): Username
        topic (str): Topic to be checked

    Returns:
        bool: True if the topic is saved, False otherwise
    """
    res = db.execute(
        f'SELECT * FROM fav_topics WHERE user_id=(SELECT id FROM users WHERE username="{username}") AND topic="{topic}"'
    )
    return len(res) > 0


def get_fav_topics(username):
    """
    Gets the saved topics for the user

    Args:
        username (str): Username

    Returns:
        list: List of saved topics
    """
    res = db.execute(
        f'SELECT topic FROM fav_topics WHERE user_id=(SELECT id FROM users WHERE username="{username}")'
    )
    return [i[0] for i in res] if res else []


# endregion
