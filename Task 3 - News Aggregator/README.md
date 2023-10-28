# News Aggregator

A tkinter GUI program to aggregate news from various sources.

### Features:
- Login System
- News feed for a topic from various sources
- Save articles to read later
- Choose favourite topics
- Dark mode using a custom `ttk` theme


### Usage:
- [Install MySQL](https://dev.mysql.com/doc/refman/8.0/en/installing.html)
- `cd` into the directory containing `script.py`
- Install the required packages using `pip install -r requirements.txt`
- Create a file `credentials.json` with the following contents:
    ```json
    {
        "password": "<your_mysql_password>"
    }
    ```
- Run `util/create_mysql.py` to create the database and tables.
- Run `script.py` to start the program.

### Notes:
- The tkinter GUI is made for a 16:9 aspect ratio.
- Windows is the intended OS for this program, in terms of the GUI.
- Spamming different topics tabs may make the program laggy (processing too many tkinter widgets at once can be slow).
