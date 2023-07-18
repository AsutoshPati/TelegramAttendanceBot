from dotenv import load_dotenv
import os

load_dotenv()

# Constants
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_LOCATION = os.path.join(os.getcwd(), "TA.db").replace("\\", "/")

# Super HR/Admin details
SUPER_HR = {
    "employee_id": os.environ.get("SUPER_HR_EMP_ID"),
    "fullname": os.environ.get("SUPER_HR_NAME"),
    "role": "HR",
    "temp_pwd": os.environ.get("SUPER_HR_PWD"),
    "last_chat_id": "",
    "is_active": True,
    "is_pwd_expired": False,
}

SELFIE_LOCATION_DELAY = 120  # Delay time in seconds between sending selfie & location
