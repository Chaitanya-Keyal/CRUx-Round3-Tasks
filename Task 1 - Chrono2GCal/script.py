import calendar
import datetime
import json
import os

import pdfplumber
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build as api_build

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def auth():
    """
    Authorises the app to access the user's Google Calendar

    Args:
        None
    Returns:
        google.oauth2.credentials.Credentials: Google Calendar API credentials
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())  # Refreshes the token if it is expired
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )  # Gets the user to login and authorise the app
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


# region Holidays


def get_holidays(filepath):
    """
    Extracts list of holidays from the pdf

    Args:
        filepath (str): Path to the holiday calendar pdf file
    Returns:
        list: List of holidays in the format YYYY-MM-DD
    """
    pdf = pdfplumber.open(filepath)
    tables = []
    for i in pdf.pages:
        tables.extend(i.extract_tables())  # Extract all tables from the pdf
    holidays = []
    for i in tables:
        for j in i:
            if j[1] and j[1].endswith("(H)"):
                holidays.append(
                    datetime.datetime.strptime(j[0][: j[0].index("(")].strip(), "%B %d")
                )  # Extracts the date from the table
    for i in range(len(holidays)):
        holidays[i] = (
            holidays[i]
            .replace(
                year=datetime.datetime.today().year
                + (not (datetime.datetime.today().month <= holidays[i].month))
            )
            .strftime("%Y-%m-%d")
        )  # If the holiday is in the next year, add 1 to the year
    return sorted(holidays)


def delete_classes_on_holidays(service, holidays):
    """
    Deletes all classes on holidays

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        holidays (list): List of holidays in the format YYYY-MM-DD
    Returns:
        None
    """
    print("Deleting classes on holidays...")
    for i in holidays:
        events = get_events(service, i, i)
        for event in events:
            try:
                if event["colorId"] not in ["9", "10", "11"]:
                    continue
            except KeyError:
                continue
            service.events().delete(calendarId="primary", eventId=event["id"]).execute()
            print(f"Event deleted: {event['summary']}")


# endregion


# region Calendar Helper Functions


def get_events(service, start_date, end_date):
    """
    Gets all events in the given date range

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        start_date (str): Start date in the format YYYY-MM-DD
        end_date (str): End date in the format YYYY-MM-DD
    Returns:
        list: List of events
    """
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start_date + "T00:00:00+05:30",
            timeMax=end_date + "T23:59:59+05:30",
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])


def del_events(
    service,
    start_date,
    end_date,
    excludeEvent=[],
    excludeColorId=[],
    onlyColorId=[],
    force=False,
):
    """
    Deletes all events in the given date range
    Can exclude events by name or colorId
    Can delete only events with a particular colorId
    Can force delete without confirmation

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        start_date (str): Start date in the format YYYY-MM-DD
        end_date (str): End date in the format YYYY-MM-DD
        excludeEvent (list): List of event names to exclude
        excludeColorId (list): List of colorIds to exclude
        onlyColorId (list): List of colorIds to include
        force (bool): Whether to force delete without confirmation
    Returns:
        None
    """
    # split date interval into months - [(start_date, end_date), ...)] - to avoid exceeding API quota
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    intervals = []
    while start_date <= end_date:
        if start_date.month == end_date.month:
            intervals.append(
                (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            )
            break
        month_end = datetime.datetime(
            start_date.year,
            start_date.month,
            calendar.monthrange(start_date.year, start_date.month)[1],
        )
        intervals.append(
            (start_date.strftime("%Y-%m-%d"), month_end.strftime("%Y-%m-%d"))
        )
        start_date = month_end + datetime.timedelta(days=1)

    # delete events in each interval
    for start_date, end_date in intervals:
        events = get_events(service, start_date, end_date)
        if not force:
            f = input(
                f"Are you sure you want to delete all events in the range {start_date} to {end_date}? (y/n): "
            )
            if f.lower() != "y":
                continue
        for event in events:
            try:
                if event["colorId"] in excludeColorId:
                    continue
                if onlyColorId and event["colorId"] not in onlyColorId:
                    continue
            except KeyError:
                continue
            if event["summary"] in excludeEvent:
                continue
            service.events().delete(calendarId="primary", eventId=event["id"]).execute()
            print(f"Event deleted: {event['summary']}")


# endregion


# region Classes and Exams


def add_classes(service, classes, start_date, end_date):
    """
    Adds all classes in the given date range

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        classes (list): List of classes
        start_date (str): Start date in the format YYYY-MM-DD
        end_date (str): End date in the format YYYY-MM-DD
    Returns:
        None
    """
    colors_dict = {
        "Tutorial": "9",
        "Lecture": "10",
        "Practical": "11",
    }
    start_date_original = start_date
    name_changed = {}  # For changing titles of classes
    for i in classes:
        original_name = i["title"]
        if original_name not in name_changed:
            f = input(
                f"\nAdding {i['title']}.\nDo you want to change the Event title? (y/n): "
            )
            while f.lower() == "y":
                i["title"] = input("Enter name: ")
                f = input(
                    f"\nChanged title to {i['title']}.\nDo you want to change it again? (y/n): "
                )
            name_changed[original_name] = i["title"]

        i["title"] = name_changed[original_name]

        # Finding the first date of the class
        start_date = datetime.datetime.strptime(start_date_original, "%Y-%m-%d")
        while start_date.strftime("%A").upper()[:2] not in i["days"]:
            start_date += datetime.timedelta(days=1)
        start_date = start_date.strftime("%Y-%m-%d")

        desc = (
            f"<ul><li><b>{i['type']} - {i['section']}</b></li><li><b>{i['name']}</b></li>"
            + (f"<li>{original_name}</li>" if original_name != i["title"] else "")
            + "<br><u>Instructors</u>:<li>"
            + "</li><li>".join(i["instructors"])
            + "</li></ul>"
        )

        event = {
            "summary": i["title"],
            "location": i["location"],
            "description": desc,
            "start": {
                "dateTime": f"{start_date}T{i['start']}+05:30",
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": f"{start_date}T{i['end']}+05:30",
                "timeZone": "Asia/Kolkata",
            },
            "recurrence": [
                f"RRULE:FREQ=WEEKLY;BYDAY={','.join(i['days'])};UNTIL={end_date.replace('-','')}T000000Z"
            ],
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 10}],
            },
            "colorId": colors_dict[i["type"]],
        }
        service.events().insert(calendarId="primary", body=event).execute()
        print(f"Classes Added: {event['summary']}")


def add_exams(service, exams, exams_start_end_dates: dict):
    """
    Adds all exams and deletes classes during exams

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        exams (list): List of exams
        exams_start_end_dates (dict): Start and end dates of midsems and compres
    Returns:
        None
    """
    for i in exams:
        # Error in Chrono's Data
        if i.split("|")[0] == "CHEM F111":
            i = i.replace("CHEM", "EEE")
        elif i.split("|")[0] == "EEE F111":
            i = i.replace("EEE", "CHEM")

        exam = {
            "summary": i.split("|")[0],
            "start": {"dateTime": i.split("|")[2], "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": i.split("|")[3], "timeZone": "Asia/Kolkata"},
            "description": i.split("|")[1],
            "colorId": "5" if i.split("|")[1] == "MIDSEM" else "6",
        }
        service.events().insert(calendarId="primary", body=exam).execute()
        print(f"{i.split('|')[1]} added: {i.split('|')[0]}")

    print("Deleting Classes during Exams...")
    del_events(
        service,
        exams_start_end_dates["midsem_start_date"],
        exams_start_end_dates["midsem_end_date"],
        onlyColorId=["9", "10", "11"],
        force=True,
    )
    del_events(
        service,
        exams_start_end_dates["compre_start_date"],
        exams_start_end_dates["compre_end_date"],
        onlyColorId=["9", "10", "11"],
        force=True,
    )


def init_classes_exams(service, timetable_ID, start_date, end_date):
    """
    Makes lists of classes and exams and calls the respective functions

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        timetable_ID (int): Chrono timetable ID
        start_date (str): Start date in the format YYYY-MM-DD
        end_date (str): End date in the format YYYY-MM-DD
    Returns:
        None
    """
    # Found Chrono API endpoints by inspecting network traffic

    timetable = json.loads(
        requests.get(
            f"https://chrono.crux-bphc.com/backend/timetable/{timetable_ID}"
        ).text
    )

    try:
        if not timetable["sections"]:
            print("ID Error. Can't access timetable.")
            exit()
    except KeyError:
        print("ID Error. Can't access timetable.")
        exit()

    courses_details = {}
    for i in json.loads(
        requests.get(f"https://chrono.crux-bphc.com/backend/course").text
    ):
        courses_details[i["id"]] = i

    exams_start_end_dates = get_exams_start_end_dates()

    def convert_slots_to_days_hr(slot: str) -> (str, str):
        """
        Converts chrono's time slot format to google calendar's format

        Args:
            slot (str): Slot in the format D:HH
        Returns:
            (str, str): (Day, Hour)
        """
        days = {
            "M": "MO",
            "T": "TU",
            "W": "WE",
            "Th": "TH",
            "F": "FR",
            "S": "SA",
            "Su": "SU",
        }
        hours = {
            "1": "08:00:00",
            "2": "09:00:00",
            "3": "10:00:00",
            "4": "11:00:00",
            "5": "12:00:00",
            "6": "13:00:00",
            "7": "14:00:00",
            "8": "15:00:00",
            "9": "16:00:00",
            "10": "17:00:00",
            "11": "18:00:00",
        }
        d, t = (
            slot.split(":") if ":" in slot else ("".join(slot[:-1]), "".join(slot[-1]))
        )
        return (days[d], hours[t])

    types_dict = {"L": "Lecture", "T": "Tutorial", "P": "Practical"}
    classes = []
    for i in timetable["sections"]:
        timings = [
            convert_slots_to_days_hr(j.split(":")[2] + j.split(":")[3])
            for j in i["roomTime"]
        ]
        class_times = []
        for j in timings:
            block_period = [k for k in timings if k[0] == j[0]]
            if len(block_period) > 1 and block_period not in class_times:
                class_times.append(block_period)
            diff_hrs = [k for k in timings if k[1] == j[1]]
            if diff_hrs not in class_times and len(block_period) == 1:
                class_times.append(diff_hrs)
        for k in class_times:
            days = [x[0] for x in k]
            classes.append(
                {
                    "title": i["roomTime"][0].split(":")[0],
                    "location": i["roomTime"][0].split(":")[1],
                    "days": list(set(days)),
                    "start": k[0][1],
                    "end": k[0][1][:2] + ":50:00"
                    if days.count(days[0]) == 1
                    else str(int(k[0][1][:2]) + days.count(days[0]) - 1) + ":50:00",
                    "section": i["type"] + str(i["number"]),
                    "instructors": i["instructors"],
                    "type": types_dict[i["type"]],
                    "name": courses_details[i["courseId"]]["name"].title(),
                }
            )

    for i in classes:
        if i["location"] == "WS":  # QOL
            i["location"] = "Workshop"
        elif i["location"] == "A222":  # Error in Chrono's Data
            i["type"] = "Practical"
            i["section"] = "P" + i["section"][1:]
        elif i["location"] == "B124":  # Error in Chrono's Data
            i["type"] = "Practical"
            i["section"] = "P" + i["section"][1:]

    add_classes(service, classes, start_date, end_date)
    add_exams(service, timetable["examTimes"], exams_start_end_dates)


# endregion


# region Timetable Helper Functions


def get_exams_start_end_dates():
    """
    Gets the start and end dates of midsems and compres

    Args:
        None
    Returns:
        dict: Start and end dates of midsems and compres
    """
    courses_details = {}
    for i in json.loads(
        requests.get(f"https://chrono.crux-bphc.com/backend/course").text
    ):
        courses_details[i["id"]] = i

    return {
        "midsem_start_date": min(
            courses_details.values(),
            key=lambda x: x["midsemStartTime"]
            if x["midsemStartTime"]
            else "9999-12-31T00:00:00Z",
        )["midsemStartTime"].split("T")[0],
        "midsem_end_date": max(
            courses_details.values(),
            key=lambda x: x["midsemEndTime"]
            if x["midsemEndTime"]
            else "0000-01-01T00:00:00Z",
        )["midsemEndTime"].split("T")[0],
        "compre_start_date": min(
            courses_details.values(),
            key=lambda x: x["compreStartTime"]
            if x["compreStartTime"]
            else "9999-12-31T00:00:00Z",
        )["compreStartTime"].split("T")[0],
        "compre_end_date": max(
            courses_details.values(),
            key=lambda x: x["compreEndTime"]
            if x["compreEndTime"]
            else "0000-01-01T00:00:00Z",
        )["compreEndTime"].split("T")[0],
    }


def get_courses_enrolled(timetable_ID):
    """
    Gets all courses enrolled in the given timetable

    Args:
        timetable_ID (int): Chrono timetable ID
    Returns:
        list: List of courses enrolled (course IDs)
    """
    timetable = json.loads(
        requests.get(
            f"https://chrono.crux-bphc.com/backend/timetable/{timetable_ID}"
        ).text
    )

    try:
        if not timetable["sections"]:
            print("ID Error. Can't access timetable.")
            exit()
    except KeyError:
        print("ID Error. Can't access timetable.")
        exit()

    courses_enrolled = []
    for i in timetable["examTimes"]:
        courses_enrolled.append(i.split("|")[0])

    return courses_enrolled


# endregion


# region Exam Rooms


def get_room_numbers(filepath, courses_enrolled, student_ID):
    """
    Extracts room numbers for enrolled courses from the pdf
    **For Midsems 2023-24 Sem 1 PDF Only (idk they might just change format randomly)**

    Args:
        filepath (str): Path to the seating arrangement pdf file
        courses_enrolled (list): List of courses enrolled (course IDs)
        student_ID (str): Student ID
    Returns:
        dict: Dictionary of course IDs and room numbers
    """
    pdf = pdfplumber.open(filepath)
    tables = []
    for i in pdf.pages:
        tables.extend(i.extract_tables())  # Extract all tables from the pdf

    room_numbers = {}

    # Parsing the tables of the pdf
    cur_course = ""
    for i in tables:
        for j in i:
            if j[0].startswith("SEATING") or j[0].startswith("COURSE"):  # Skip headers
                continue
            if j[0] in courses_enrolled:  # If course is enrolled
                cur_course = j[0]
            elif j[0] != "":  # For courses with multiple rooms
                cur_course = ""
            if cur_course:
                if j[4] == "ALL THE STUDENTS":
                    room_numbers[cur_course] = j[3]
                    continue
                else:
                    ids = j[4].split(" to ")
                    if ids[0] <= student_ID <= ids[1]:
                        room_numbers[cur_course] = j[3]
                        continue

    return room_numbers


def add_exam_rooms(service, room_numbers, examtype):
    """
    Adds room numbers to the already created exam events

    Args:
        service (googleapiclient.discovery.Resource): Google Calendar API service
        room_numbers (dict): Dictionary of course IDs and room numbers
        examtype (str): midsem or compre
    Returns:
        None
    """
    exams_start_end_dates = get_exams_start_end_dates()
    events = get_events(
        service,
        exams_start_end_dates[f"{examtype}_start_date"],
        exams_start_end_dates[f"{examtype}_end_date"],
    )
    for event in events:
        if event["summary"] in room_numbers:
            event["location"] = room_numbers[event["summary"]]
            service.events().update(
                calendarId="primary", eventId=event["id"], body=event
            ).execute()
            print(f"Room number added to {event['summary']}")
        else:
            print(f"Room number not found for {event['summary']}")
    print("Rooms Added")


# endregion


def main(creds):
    """
    Main function to run the script

    Args:
        creds (google.oauth2.credentials.Credentials): Google Calendar API credentials
    Returns:
        None
    """
    service = api_build("calendar", "v3", credentials=creds)

    start_date = None
    while True:
        start_date = input(
            "Enter start date (YYYY-MM-DD) [Leave blank to start today]: "
        )
        if not start_date:
            start_date = datetime.datetime.today().strftime("%Y-%m-%d")
            break
        try:
            datetime.datetime.strptime(start_date, "%Y-%m-%d")
            break
        except ValueError:
            print("\nIncorrect date format, should be YYYY-MM-DD")
            continue

    end_date = None
    while True:
        end_date = input("Enter semester end date (Excluded) (YYYY-MM-DD): ")
        try:
            datetime.datetime.strptime(end_date, "%Y-%m-%d")
            break
        except ValueError:
            print("\nIncorrect date format, should be YYYY-MM-DD")
            continue

    timetable_ID = int(input("Enter timetable ID: "))

    student_ID = None
    while True:
        student_ID = input("Enter your Student ID: ").strip().upper()
        if (
            len(student_ID) != 13
            or student_ID[:4] not in ["2018", "2019", "2020", "2021", "2022", "2023"]
            or not student_ID[8:12].isdigit()
            or student_ID[-1] != "H"
        ):
            print("Incorrect Student ID")
            continue
        break

    init_classes_exams(service, timetable_ID, start_date, end_date)
    delete_classes_on_holidays(service, get_holidays("BPHC_Calendar_23_24.pdf"))

    add_exam_rooms(
        service,
        get_room_numbers(
            "Midsem_Seating_Sem1.pdf",
            get_courses_enrolled(timetable_ID),
            student_ID,
        ),
        "midsem",
    )


if __name__ == "__main__":
    creds = auth()
    main(creds=creds)
