from datetime import datetime
import hashlib
import pytz


# Takes an object and return its hash ( SHA512 )
def get_hashed(message: str):
    """
    Perform SHA512 hashing on string
    :param message: string to be hashed
    :return: hashed string
    """
    hash_hex = hashlib.sha512(message.encode()).hexdigest()
    return str(hash_hex)


# Change UTC datetime to IST datetime
def to_IST(timestamp: datetime):
    """
    Convert UTC datetime to IST datetime
    :param timestamp: UTC timestamp
    :return: IST timestamp
    """
    local_tz = pytz.timezone("Asia/Kolkata")
    local_dt = timestamp.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)


# Change IST datetime to UTC datetime
def to_UTC(timestamp: datetime):
    """
    Convert IST datetime to UTC datetime
    :param timestamp: IST timestamp
    :return: UTC timestamp
    """
    local_tz = pytz.timezone("Asia/Kolkata")
    utc_dt = local_tz.localize(timestamp, is_dst=None).astimezone(pytz.utc)
    return pytz.utc.normalize(utc_dt)


# Get timestamp from epoch
def UTC_from_epoch(epoch: int):
    """
    Convert UNIX epoch to UTC timestamp
    :param epoch: UNIX epoch
    :return: UTC timestamp
    """
    return datetime.utcfromtimestamp(epoch)


def time_difference(
    timestamp_a: datetime, timestamp_b: datetime, formatted: bool = False
):
    """
    Calculate the time difference between 2 timestamps
    :param timestamp_a: timestamp with higher value
    :param timestamp_b: timestamp with lower value
    :param formatted: whether the output required in formatted string like HH:MM
    """
    time_diff = timestamp_a - timestamp_b
    if formatted:
        time_diff_hours = time_diff.seconds // 3600
        time_diff_minutes = (time_diff.seconds - (time_diff_hours * 3600)) // 60
        time_diff = f"{str(time_diff_hours).rjust(2, '0')}:{str(time_diff_minutes).rjust(2, '0')}"
    return time_diff
