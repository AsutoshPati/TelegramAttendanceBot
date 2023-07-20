from datetime import datetime, timedelta
import os
import pdfkit
import telebot

from db_backend import db_session
from helpers import UTC_from_epoch, get_hashed, time_difference, to_IST, to_UTC
from models import Attendance, User
from settings import BOT_TOKEN, SELFIE_LOCATION_DELAY

bot = telebot.TeleBot(BOT_TOKEN)


# Create a new attendance record
def new_attendance(
    user_id: int,
    selfie: list = None,
    selfie_time: datetime = None,
    location: dict = None,
    location_time: datetime = None,
):
    if selfie_time or location_time:
        if selfie_time:
            attendance = Attendance(
                user_id=user_id, selfie=selfie, selfie_time=selfie_time
            )
        else:
            attendance = Attendance(
                user_id=user_id, location=location, location_time=location_time
            )

        db_session.add(attendance)
        db_session.commit()
    else:
        AssertionError("Either selfie or location required")


# When user starts a flow; welcome them
@bot.message_handler(commands=["start", "hello"])
@bot.message_handler(func=lambda msg: msg.text in ["start", "hello"])
def welcome_user(message):
    chat_id = message.chat.id
    known_user = User.get_by_chat_id(chat_id)
    if known_user:
        bot.reply_to(
            message,
            f"Hi, *{known_user.fullname}*; Welcome back",
            parse_mode="MarkdownV2",
        )
    else:
        bot.reply_to(
            message,
            "Please use command /login to interact further; example\n/login\nemployee ID\npassword \n\n"
            "or /help for other commands",
            parse_mode="MarkdownV2",
        )


# Show help options to users
@bot.message_handler(commands=["help"])
@bot.message_handler(func=lambda msg: msg.text in ["help"])
def help_msg(message):
    bot.reply_to(
        message,
        "/login \\- to login a user with employee ID and OTP followed by command\n"
        "/logout \\- to logout a user\n"
        "/create \\- HR can create a new user with their employee ID, name, role, OTP followed by command\n"
        "/download \\- user can download their monthly attendance by providing the month & year followed by command\n"
        "/rstpwd \\- HR can reset user password by providing employee ID & OTP followed by command\n"
        "/deactive \\- HR can deactivate an user by providing employee ID followed by command\n"
        "/reactive \\- HR can reactive an user by providing employee ID followed by command",
        parse_mode="MarkdownV2",
    )


# Login a user with employeeID & OTP
@bot.message_handler(commands=["login"])
@bot.message_handler(func=lambda msg: msg.text in ["login"])
def login_user(message):
    chat_id = message.chat.id
    try:
        _, emp_id, pwd = list(map(lambda x: x.strip(), message.text.split("\n")))
        known_user = User.is_valid_credential(emp_id, pwd)
        if not known_user:
            bot.reply_to(message, "Sorry, login failed; Try again")
        else:
            logged_in_user = User.get_by_emp_id(emp_id)
            logged_in_user.last_chat_id = str(chat_id)
            logged_in_user.is_pwd_expired = True
            db_session.add(logged_in_user)
            db_session.commit()
            bot.reply_to(
                message, f"Hello *{known_user.fullname}*", parse_mode="MarkdownV2"
            )
    except ValueError:
        bot.reply_to(
            message,
            "Please use command /login to interact further; example\n/login\nemployee ID\npassword",
            parse_mode="MarkdownV2",
        )


# Logout a logged in user
@bot.message_handler(commands=["logout"])
@bot.message_handler(func=lambda msg: msg.text in ["logout"])
def logout_user(message):
    chat_id = message.chat.id
    known_user = User.get_by_chat_id(chat_id)
    if known_user:
        known_user.last_chat_id = None
        db_session.add(known_user)
        db_session.commit()
        bot.reply_to(
            message,
            "You have been logged out; to login again ask your HR for a new password",
        )
    else:
        bot.reply_to(message, "You are not yet logged in")


# Create a new user with their employeeID, name, role & OTP
@bot.message_handler(commands=["create"])
@bot.message_handler(func=lambda msg: msg.text in ["create"])
def create_user(message):
    chat_id = message.chat.id
    known_user = User.get_by_chat_id(chat_id)
    if known_user:
        if known_user.role == "HR":
            try:
                _, emp_id, full_name, role, pwd = list(
                    map(lambda x: x.strip(), message.text.split("\n"))
                )
                if role.title() == "Employee":
                    role = "Employee"
                elif role.upper() == "HR":
                    role = "HR"
                else:
                    bot.reply_to(message, "Please provide Employee/HR as role")
                pwd = get_hashed(pwd)
                new_user = User(
                    employee_id=emp_id, fullname=full_name, role=role, temp_pwd=pwd
                )
                db_session.add(new_user)
                db_session.commit()
                bot.reply_to(message, "User has been added ", parse_mode="MarkdownV2")
            except ValueError:
                bot.reply_to(
                    message,
                    "Please use command /create to create user; "
                    "example\n/create\nemployee ID\nfull name\nrole\nOTP",
                    parse_mode="MarkdownV2",
                )
        else:
            bot.reply_to(message, "Sorry!! you can't use this command")
    else:
        bot.reply_to(message, "You are not yet logged in")


# Reset a password with employeeID & OTP
@bot.message_handler(commands=["rstpwd"])
@bot.message_handler(func=lambda msg: msg.text in ["rstpwd"])
def reset_password(message):
    chat_id = message.chat.id
    known_user = User.get_by_chat_id(chat_id)
    if known_user:
        if known_user.role == "HR":
            try:
                _, emp_id, pwd = list(
                    map(lambda x: x.strip(), message.text.split("\n"))
                )
                pwd = get_hashed(pwd)
                user = User.get_by_emp_id(emp_id)
                if user:
                    user.temp_pwd = pwd
                    user.is_pwd_expired = False
                    db_session.add(user)
                    db_session.commit()
                    bot.reply_to(
                        message, "New OTP has been updated", parse_mode="MarkdownV2"
                    )
                else:
                    bot.reply_to(
                        message,
                        "Employee doesn't exist or deactivated",
                        parse_mode="MarkdownV2",
                    )
            except ValueError:
                bot.reply_to(
                    message,
                    "Please use command /rstpwd to create user; "
                    "example\n/rstpwd\nemployee ID\nOTP",
                    parse_mode="MarkdownV2",
                )
        else:
            bot.reply_to(message, "Sorry!! you can't use this command")
    else:
        bot.reply_to(message, "You are not yet logged in")


# Deactivate user by their employee ID
@bot.message_handler(commands=["deactive"])
@bot.message_handler(func=lambda msg: msg.text in ["deactive"])
def deactivate_user(message):
    chat_id = message.chat.id
    known_user = User.get_by_chat_id(chat_id)
    if known_user:
        if known_user.role == "HR":
            try:
                _, emp_id = list(map(lambda x: x.strip(), message.text.split("\n")))
                user = User.get_by_emp_id(emp_id)
                if user:
                    user.is_active = False
                    db_session.add(user)
                    db_session.commit()
                    bot.reply_to(
                        message, "User has been deactivated", parse_mode="MarkdownV2"
                    )
                else:
                    bot.reply_to(
                        message,
                        "Employee doesn't exist or deactivated",
                        parse_mode="MarkdownV2",
                    )
            except ValueError:
                bot.reply_to(
                    message,
                    "Please use command /deactive to create user; "
                    "example\n/deactive\nemployee ID",
                    parse_mode="MarkdownV2",
                )
        else:
            bot.reply_to(message, "Sorry!! you can't use this command")
    else:
        bot.reply_to(message, "You are not yet logged in")


# Reactivate user with their employeeID
@bot.message_handler(commands=["reactive"])
@bot.message_handler(func=lambda msg: msg.text in ["reactive"])
def reactivate_user(message):
    chat_id = message.chat.id
    known_user = User.get_by_chat_id(chat_id)
    if known_user:
        if known_user.role == "HR":
            try:
                _, emp_id = list(map(lambda x: x.strip(), message.text.split("\n")))
                user = User.get_by_emp_id(emp_id, only_active=False)
                if user:
                    user.is_active = True
                    db_session.add(user)
                    db_session.commit()
                    bot.reply_to(
                        message, "User has been reactivated", parse_mode="MarkdownV2"
                    )
                else:
                    bot.reply_to(
                        message,
                        "Employee doesn't exist or deactivated",
                        parse_mode="MarkdownV2",
                    )
            except ValueError:
                bot.reply_to(
                    message,
                    "Please use command /deactive to create user; "
                    "example\n/deactive\nemployee ID",
                    parse_mode="MarkdownV2",
                )
        else:
            bot.reply_to(message, "Sorry!! you can't use this command")
    else:
        bot.reply_to(message, "You are not yet logged in")


# When user send a picture (selfie)
@bot.message_handler(content_types=["photo"])
def handle_attendance_selfie(message):
    chat_id = message.chat.id
    known_user = User.get_by_chat_id(chat_id)
    if known_user:
        curr_time = UTC_from_epoch(message.date)
        last_attendance = Attendance.get_last_attendance_record(
            known_user.id, curr_time
        )
        pictures = []
        for pic in message.photo:
            pictures.append(
                {
                    "file_id": pic.file_id,
                    "file_unique_id": pic.file_unique_id,
                    "width": pic.width,
                    "height": pic.height,
                    "file_size": pic.file_size,
                }
            )

        # Add face recognition on message.photo[2]; which is a good quality image

        if last_attendance:
            # if a attendance is already present for today
            if last_attendance.selfie_time and last_attendance.location_time:
                # if the last record already have a selfie & location; create a new record
                new_attendance(
                    user_id=known_user.id, selfie=pictures, selfie_time=curr_time
                )
                bot.reply_to(
                    message,
                    "Selfie has been has been added, Please share your location for attendance",
                )

            elif last_attendance.selfie_time:
                # if already selfie is present
                if (
                    curr_time - last_attendance.selfie_time
                ).seconds > SELFIE_LOCATION_DELAY:
                    # but the slack time is already passed
                    new_attendance(
                        user_id=known_user.id, selfie=pictures, selfie_time=curr_time
                    )
                    bot.reply_to(
                        message,
                        f"😩 Oops.. You are unable to send location with in <b>{SELFIE_LOCATION_DELAY / 60:.1f}</b>"
                        " minutes",
                        parse_mode="HTML",
                    )
                    bot.send_message(
                        chat_id,
                        f"We have added your selfie, Please share your location with in "
                        f"<b>{SELFIE_LOCATION_DELAY / 60:.1f}</b> minutes for attendance",
                        parse_mode="HTML",
                    )
                else:
                    # if still have some time left
                    time_left = (
                        SELFIE_LOCATION_DELAY
                        - (curr_time - last_attendance.selfie_time).seconds
                    )
                    bot.reply_to(
                        message,
                        "Selfie has been already received; "
                        f"Please send your location in <b>{time_left/60:.1f}</b> minutes for attendance",
                        parse_mode="HTML",
                    )

            elif last_attendance.location_time:
                # if location is already exists
                if (
                    curr_time - last_attendance.location_time
                ).seconds > SELFIE_LOCATION_DELAY:
                    # but slack time passed
                    new_attendance(
                        user_id=known_user.id, selfie=pictures, selfie_time=curr_time
                    )
                    bot.reply_to(
                        message,
                        f"😩 Oops.. You are unable to send selfie with in <b>{SELFIE_LOCATION_DELAY / 60:.1f}</b>"
                        " minutes",
                        parse_mode="HTML",
                    )
                    bot.send_message(
                        chat_id,
                        "We have added your selfie, Please share your location with in "
                        f"<b>{SELFIE_LOCATION_DELAY / 60:.1f}</b> minutes for attendance",
                        parse_mode="HTML",
                    )
                else:
                    # selfie sent with in the slack time
                    last_attendance.selfie = pictures
                    last_attendance.selfie_time = curr_time
                    db_session.add(last_attendance)
                    db_session.commit()
                    bot.reply_to(message, "Your attendance has been added 👍")

        else:
            # if there are no record create a new record
            new_attendance(
                user_id=known_user.id, selfie=pictures, selfie_time=curr_time
            )
            bot.reply_to(
                message,
                "Selfie has been has been added, Please share your location for attendance",
            )

    else:
        bot.reply_to(message, "You are not yet logged in")


# When user send location
@bot.message_handler(content_types=["location"])
def handle_attendance_location(message):
    chat_id = message.chat.id
    known_user = User.get_by_chat_id(chat_id)
    if known_user:
        curr_time = UTC_from_epoch(message.date)
        last_attendance = Attendance.get_last_attendance_record(
            known_user.id, curr_time
        )
        location = {
            "longitude": message.location.longitude,
            "latitude": message.location.latitude,
        }
        if last_attendance:
            # if a attendance is already present for today
            if last_attendance.selfie_time and last_attendance.location_time:
                # but both selfie and location has been added; create a new record
                new_attendance(
                    user_id=known_user.id, location=location, location_time=curr_time
                )
                bot.reply_to(
                    message,
                    "Location has been has been added, Please share your selfie for attendance",
                )
            elif last_attendance.selfie_time:
                # and selfie is already present
                if (
                    curr_time - last_attendance.selfie_time
                ).seconds > SELFIE_LOCATION_DELAY:
                    # location is sent after slack time is over
                    new_attendance(
                        user_id=known_user.id,
                        location=location,
                        location_time=curr_time,
                    )
                    bot.reply_to(
                        message,
                        f"😩 Oops.. You are unable to send location with in <b>{SELFIE_LOCATION_DELAY / 60:.1f}</b>"
                        " minutes",
                        parse_mode="HTML",
                    )
                    bot.send_message(
                        chat_id,
                        "We have added your location, Please share your selfie with in "
                        f"<b>{SELFIE_LOCATION_DELAY / 60:.1f}</b> minutes for attendance",
                        parse_mode="HTML",
                    )
                else:
                    # location sent with in the slack time
                    last_attendance.location = location
                    last_attendance.location_time = curr_time
                    db_session.add(last_attendance)
                    db_session.commit()
                    bot.reply_to(message, "Your attendance has been added 👍")
            elif last_attendance.location_time:
                # and location is already present
                if (
                    curr_time - last_attendance.location_time
                ).seconds > SELFIE_LOCATION_DELAY:
                    # if location is sent after slack time
                    new_attendance(
                        user_id=known_user.id,
                        location=location,
                        location_time=curr_time,
                    )
                    bot.reply_to(
                        message,
                        f"😩 Oops.. You are unable to send selfie with in <b>{SELFIE_LOCATION_DELAY / 60:.1f}</b>"
                        " minutes",
                        parse_mode="HTML",
                    )
                    bot.send_message(
                        chat_id,
                        "We have added your location, Please share your selfie with in "
                        f"<b>{SELFIE_LOCATION_DELAY / 60:.1f}</b> minutes for attendance",
                        parse_mode="HTML",
                    )
                else:
                    # if still have some time left
                    time_left = (
                        SELFIE_LOCATION_DELAY
                        - (curr_time - last_attendance.selfie_time).seconds
                    )
                    bot.reply_to(
                        message,
                        "Location has been already received; "
                        f"Please send your selfie in <b>{time_left / 60:.1f}</b> minutes for attendance",
                        parse_mode="HTML",
                    )
        else:
            # if there are no record create a new record
            new_attendance(
                user_id=known_user.id, location=location, location_time=curr_time
            )
            bot.reply_to(
                message,
                "Location has been has been added, Please share your selfie for attendance",
            )
    else:
        bot.reply_to(message, "You are not yet logged in")


# Download attendance report
@bot.message_handler(commands=["download"])
@bot.message_handler(func=lambda msg: msg.text in ["download"])
def download_report(message):
    chat_id = message.chat.id
    known_user = User.get_by_chat_id(chat_id)
    if known_user:
        curr_time = UTC_from_epoch(message.date)
        data = list(map(lambda x: x.strip(), message.text.split("\n")))
        if known_user.role == "HR":
            if len(data) == 1:
                start_date = datetime(
                    year=curr_time.year, month=curr_time.month, day=curr_time.day
                )
                end_date = datetime(
                    year=curr_time.year,
                    month=curr_time.month,
                    day=curr_time.day,
                    hour=23,
                    minute=59,
                    second=59,
                )
                start_date = to_UTC(start_date)
                end_date = to_UTC(end_date)
                attendance_records = Attendance.get_attendance_records(
                    start_date, end_date
                )
            elif len(data) == 2 or len(data) == 3:
                emp_id = None
                try:
                    _, dmy = data
                except ValueError:
                    _, dmy, emp_id = data

                try:
                    start_date = datetime.strptime(dmy, "%d %m %Y")
                    end_date = datetime(
                        year=start_date.year,
                        month=start_date.month,
                        day=start_date.day,
                        hour=23,
                        minute=59,
                        second=59,
                    )
                except ValueError:
                    try:
                        start_date = datetime.strptime(dmy, "%m %Y")
                        next_month = start_date.replace(day=28) + timedelta(days=4)
                        last_day = next_month - timedelta(days=next_month.day)
                        end_date = datetime(
                            year=start_date.year,
                            month=start_date.month,
                            day=last_day.day,
                            hour=23,
                            minute=59,
                            second=59,
                        )
                    except ValueError:
                        try:
                            start_date = datetime.strptime(dmy, "%Y")
                            end_date = datetime(
                                year=start_date.year,
                                month=12,
                                day=31,
                                hour=23,
                                minute=59,
                                second=59,
                            )
                        except ValueError:
                            bot.reply_to(
                                message,
                                "Please use command /download to download report; "
                                "example\n/download\nDate[Optional] Month[Optional] Year[Optional] "
                                "[DD MM YYYY/ MM YYYY/ YYYY]\nemployee ID[Optional]",
                                parse_mode="MarkdownV2",
                            )
                            return

                start_date = to_UTC(start_date)
                end_date = to_UTC(end_date)
                if emp_id:
                    user = User.get_by_emp_id(emp_id)
                    emp_id = user.id
                attendance_records = Attendance.get_attendance_records(
                    start_date, end_date, emp_id
                )

            else:
                bot.reply_to(
                    message,
                    "Please use command /download to download report; "
                    "example\n/download\nDate[Optional] Month[Optional] Year[Optional] [DD MM YYYY/ MM YYYY/ YYYY]"
                    "\nemployee ID[Optional]",
                    parse_mode="MarkdownV2",
                )
                return

            if len(attendance_records) < 1:
                bot.reply_to(message, "No attendance record to download")
                return

            start_date = to_IST(start_date)
            end_date = to_IST(end_date)

            html_text = f"""
            <html>
            <body>
            <center>
            <table width='100%' border='2px solid'>
            <tr>
            <td colspan='6' style='text-align:center;font-weight:bold;'>Attendance Report</td>
            </tr>
            <tr>
            <td colspan='3'>Start Date: {start_date.strftime('%d-%B-%Y')}</td>
            <td colspan='3'>End Date: {end_date.strftime('%d-%B-%Y')}</td>
            </tr>
            <tr>
            <th width='5%'>Sl. No.</td>
            <th width='20%'>Employee ID</td>
            <th width='20%'>Selfie Time</td>
            <th width='20%'>Location Time</td>
            <th width='20%'>Location</td>
            <th width='*'>Time Diff</td>
            </tr>
            """

            file_name = f"Attendance-{message.date}"
            ctr = 0
            last_record = None
            for record in attendance_records:
                if ctr % 2 == 0:
                    last_record = record
                    user = User.get_by_user_id(last_record.user_id, only_active=False)
                    html_text += f"""
                    <tr>
                        <td>{ctr+1}</td>
                        <td>{user.employee_id}</td>
                        <td>{to_IST(last_record.selfie_time).strftime("%d-%m-%Y %H:%M")}</td>
                        <td>{to_IST(last_record.location_time).strftime("%d-%m-%Y %H:%M")}</td>
                        <td>Long: {last_record.location["longitude"]}, Lat: {last_record.location["latitude"]}</td>
                        <td></td>
                    </tr>
                    """
                else:
                    user = User.get_by_user_id(record.user_id, only_active=False)
                    time_diff = time_difference(
                        to_IST(record.selfie_time),
                        to_IST(last_record.selfie_time),
                        formatted=True,
                    )
                    time_diff = (
                        None  # Remove when records are aggregated by employee ID
                    )

                    html_text += f"""
                    <tr>
                        <td>{ctr + 1}</td>
                        <td>{user.employee_id}</td>
                        <td>{to_IST(record.selfie_time).strftime("%d-%m-%Y %H:%M")}</td>
                        <td>{to_IST(record.location_time).strftime("%d-%m-%Y %H:%M")}</td>
                        <td>Long: {record.location["longitude"]}, Lat: {record.location["latitude"]}</td>
                        <td>{time_diff}</td>
                    </tr>
                    """
                ctr += 1
            html_text += "</table></center></body></html>"

            file = open(f"{file_name}.html", "wb")
            file.write(html_text.encode())
            file.close()
            pdfkit.from_file(f"{file_name}.html", f"{file_name}.pdf")
            file = open(f"{file_name}.pdf", "rb")
            bot.send_document(
                known_user.last_chat_id, document=file, reply_to_message_id=message.id
            )
            file.close()
            os.remove(f"{file_name}.html")
            os.remove(f"{file_name}.pdf")
        else:
            if len(data) == 1:
                start_date = datetime(
                    year=curr_time.year, month=curr_time.month, day=curr_time.day
                )
                end_date = datetime(
                    year=curr_time.year,
                    month=curr_time.month,
                    day=curr_time.day,
                    hour=23,
                    minute=59,
                    second=59,
                )
                start_date = to_UTC(start_date)
                end_date = to_UTC(end_date)
            elif len(data) == 2:
                _, dmy = data

                try:
                    start_date = datetime.strptime(dmy, "%d %m %Y")
                    end_date = datetime(
                        year=start_date.year,
                        month=start_date.month,
                        day=start_date.day,
                        hour=23,
                        minute=59,
                        second=59,
                    )
                except ValueError:
                    try:
                        start_date = datetime.strptime(dmy, "%m %Y")
                        next_month = start_date.replace(day=28) + timedelta(days=4)
                        last_day = next_month - timedelta(days=next_month.day)
                        end_date = datetime(
                            year=start_date.year,
                            month=start_date.month,
                            day=last_day.day,
                            hour=23,
                            minute=59,
                            second=59,
                        )
                    except ValueError:
                        try:
                            start_date = datetime.strptime(dmy, "%Y")
                            end_date = datetime(
                                year=start_date.year,
                                month=12,
                                day=31,
                                hour=23,
                                minute=59,
                                second=59,
                            )
                        except ValueError:
                            bot.reply_to(
                                message,
                                "Please use command /download to download report; "
                                "example\n/download\nDate[Optional] Month[Optional] Year[Optional] "
                                "[DD MM YYYY/ MM YYYY/ YYYY]\nemployee ID[Optional]",
                                parse_mode="MarkdownV2",
                            )
                            return

                start_date = to_UTC(start_date)
                end_date = to_UTC(end_date)
            else:
                bot.reply_to(
                    message,
                    "Please use command /download to download report; "
                    "example\n/download\nDate[Optional] Month[Optional] Year[Optional] [DD MM YYYY/ MM YYYY/ YYYY]",
                    parse_mode="MarkdownV2",
                )
                return

            attendance_records = Attendance.get_attendance_records(
                start_date, end_date, known_user.id
            )

            start_date = to_IST(start_date)
            end_date = to_IST(end_date)

            if len(attendance_records) == 0:
                bot.reply_to(message, "No attendance record found")
            elif attendance_records <= 2:
                msg = "Attendance report\n"
                msg += f"Start Date: {start_date.strftime('%d-%B-%Y')}\n"
                msg += f"End Date: {end_date.strftime('%d-%B-%Y')}\n\n"
                msg += f"IN: {to_IST(attendance_records[0].selfie_time).strftime('%d-%m-%Y %H:%M')}\n"
                if len(attendance_records) == 2:
                    time_diff = time_difference(
                        to_IST(attendance_records[1].selfie_time),
                        to_IST(attendance_records[0].selfie_time),
                        formatted=True,
                    )
                    msg += f"OUT: {to_IST(attendance_records[1].selfie_time).strftime('%d-%m-%Y %H:%M')}\n"
                    msg += f"Duration: {time_diff}"
                bot.reply_to(message, msg, parse_mode="MarkdownV2")
            else:
                html_text = f"""
                <html>
                <body>
                <center>
                <table width='100%' border='2px solid'>
                <tr>
                <td colspan='5' style='text-align:center;font-weight:bold;'>Attendance Report</td>
                </tr>
                <tr style='text-align:center;font-weight:bold;'>
                <td colspan='3'>Employee Name: {known_user.fullname}</td>
                <td colspan='2'>Employee ID: {known_user.employee_id}</td>
                </tr>
                <tr>
                <td colspan='3'>Start Date: {start_date.strftime('%d-%B-%Y')}</td>
                <td colspan='2'>End Date: {end_date.strftime('%d-%B-%Y')}</td>
                </tr>
                <tr>
                <th width='5%'>Sl. No.</td>
                <th width='25%'>Selfie Time</td>
                <th width='25%'>Location Time</td>
                <th width='25%'>Location</td>
                <th width='*'>Time Diff</td>
                </tr>
                """

                file_name = f"Attendance-{message.date}"
                ctr = 0
                last_record = None
                for record in attendance_records:
                    if ctr % 2 == 0:
                        last_record = record
                        html_text += f"""
                        <tr>
                        <td>{ctr + 1}</td>
                        <td>{to_IST(last_record.selfie_time).strftime("%d-%m-%Y %H:%M")}</td>
                        <td>{to_IST(last_record.location_time).strftime("%d-%m-%Y %H:%M")}</td>
                        <td>Long: {last_record.location["longitude"]}, Lat: {last_record.location["latitude"]}</td>
                        <td></td>
                        </tr>
                        """
                    else:
                        time_diff = time_difference(
                            to_IST(record.selfie_time),
                            to_IST(last_record.selfie_time),
                            formatted=True,
                        )
                        html_text += f"""
                        <tr>
                        <td>{ctr + 1}</td>
                        <td>{to_IST(record.selfie_time).strftime("%d-%m-%Y %H:%M")}</td>
                        <td>{to_IST(record.location_time).strftime("%d-%m-%Y %H:%M")}</td>
                        <td>Long: {record.location["longitude"]}, Lat: {record.location["latitude"]}</td>
                        <td>{time_diff}</td>
                        </tr>
                        """
                    ctr += 1
                html_text += "</table></center></body></html>"

                file = open(f"{file_name}.html", "wb")
                file.write(html_text.encode())
                file.close()
                pdfkit.from_file(f"{file_name}.html", f"{file_name}.pdf")
                file = open(f"{file_name}.pdf", "rb")
                bot.send_document(
                    known_user.last_chat_id,
                    document=file,
                    reply_to_message_id=message.id,
                )
                file.close()
                os.remove(f"{file_name}.html")
                os.remove(f"{file_name}.pdf")
    else:
        bot.reply_to(message, "You are not yet logged in")


# When user send any message except the commands, picture or location (Fallback State)
@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    bot.reply_to(
        message,
        "Sorry I can't help you in this; Please checkout /help or contact your administrator",
    )


bot.infinity_polling()


# @bot.message_handler(commands=['menu'])
# @bot.message_handler(func=lambda msg: msg.text in ["menu"])
# # import argparse
# from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
#
# # parser = argparse.ArgumentParser(description="")
# # parser.add_argument("-ch")
#
# def show_menu(message):
#     chat_id = message.chat.id
#     known_user = User.get_by_chat_id(chat_id)
#     if known_user:
#         if known_user.role == "HR":
#             menu_main = [
#                 [InlineKeyboardButton('Create Users', callback_data='m1')],
#                 [InlineKeyboardButton('Reset Password', callback_data='m2')]
#             ]
#             reply_markup = InlineKeyboardMarkup(menu_main)
#             bot.reply_to(message, "Here is your menu", parse_mode="MarkdownV2", reply_markup=reply_markup)
#         else:
#             bot.reply_to(
#                 message,
#                 f"we will come to this ----- ---------------------------------",
#                 parse_mode="MarkdownV2"
#             )
#     else:
#         bot.reply_to(message, "You are not yet logged in", parse_mode="MarkdownV2")
#
#
# @bot.callback_query_handler(func=lambda msg: True)
# def test_chosen(message):
#     print(message)
#
#
#
#
# bot.send_message(1887658587, "Bot Restarted")
