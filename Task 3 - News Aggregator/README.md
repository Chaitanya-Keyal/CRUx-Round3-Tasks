# News Aggregator

A tkinter GUI program to aggregate news from various sources.

### Features:
- Login System
- Search for articles
- Save articles to read later
- Select favourite topics for a news feed

### Usage:
- [Install MySQL](https://dev.mysql.com/doc/refman/8.0/en/installing.html)
- `cd` into the directory containing `script.py`
- Install the required packages using `pip install -r requirements.txt`
- Run `util/create_mysql.py` to create the database and tables.
- Create a file `credentials.json` with the following contents:
    ```json
    {
        "password": "<your_mysql_password>"
    }
    ```
- Run `script.py` to start the program.

### Notes:
- The tkinter GUI is made for a 16:9 aspect ratio.
- Windows is the intended OS for this program, in terms of the GUI.
