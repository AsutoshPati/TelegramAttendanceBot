import base64
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from datetime import datetime
import hashlib
import pytz
import os

from settings import ENC_KEY

# Encryption method
cipher = ChaCha20Poly1305(base64.b64decode(ENC_KEY))
NULL_BYTE = b""
NONCE_SIZE = 12     # Nonce size in bytes
NONCE_LENGTH = 16   # For nonce size 12; nonce string length will be 16


def cryptography_service(message: str, serv_type: str = "encrypt"):
    """
    Encrypt or decrypt a string
    :param message: string to encrypt or decrypt
    :param serv_type: "encrypt" to perform encryption & "decrypt" for decryption
    :return: encrypted/decrypted string
    """
    if serv_type == "encrypt":
        nonce = os.urandom(NONCE_SIZE)
        nonce_str = str(base64.b64encode(nonce), encoding="utf8")
        encrypted_str = cipher.encrypt(nonce, message.encode(), NULL_BYTE)
        return nonce_str+str(base64.b64encode(encrypted_str), encoding="utf8")

    elif serv_type == "decrypt":
        nonce, data = base64.b64decode(message[:NONCE_LENGTH]), base64.b64decode(message[NONCE_LENGTH:])
        return cipher.decrypt(nonce, data, NULL_BYTE).decode()

    else:
        AssertionError(
            f"Invalid value for argument 'serv_type': '{serv_type}';"
            "Please check the docstring for valid options"
        )


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
    local_tz = pytz.timezone('Asia/Kolkata')
    local_dt = timestamp.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)


# Get timestamp from epoch
def UTC_from_epoch(epoch: int):
    """
    Convert UNIX epoch to UTC timestamp
    :param epoch: UNIX epoch
    :return: UTC timestamp
    """
    return datetime.utcfromtimestamp(epoch)
