from datetime import datetime
from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String, DateTime, func, or_
from sqlalchemy.orm import DeclarativeBase

from db_backend import db_session, engine, debug_query
from helpers import get_hashed
from settings import SUPER_HR


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_account"

    id = Column(Integer, primary_key=True)
    employee_id = Column(String(30), unique=True)
    fullname = Column(String(30))
    role = Column(String(10))
    temp_pwd = Column(String(10))
    last_chat_id = Column(String(10))
    is_active = Column(Boolean, default=True)
    is_pwd_expired = Column(Boolean, default=False)

    @classmethod
    def get_by_emp_id(cls, employee_id: str):
        """
        Get user record by their employee ID
        :param employee_id: employee ID of user
        """
        query = db_session.query(cls).filter(cls.employee_id == employee_id, cls.is_active.isnot(False))
        return query.first()

    @classmethod
    def get_by_chat_id(cls, chat_id: str):
        """
        Get user record by their chat ID
        :param chat_id: chat ID of user
        """
        query = db_session.query(cls).filter(cls.last_chat_id == chat_id, cls.is_active.isnot(False))
        return query.first()

    @classmethod
    def is_valid_credential(cls, employee_id: str, temp_pwd: str):
        """
        Get user with their correct credential
        :param employee_id: employee ID of user
        :param temp_pwd: OTP provided to user
        """
        query = db_session.query(cls).filter(
            cls.employee_id == employee_id,
            cls.temp_pwd == get_hashed(temp_pwd),
            cls.is_active.isnot(False),
            cls.is_pwd_expired.isnot(True)
        )
        print(debug_query(query))
        return query.first()


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user_account.id'))
    selfie = Column(JSON, unique=True)
    selfie_time = Column(DateTime(timezone=True))
    location = Column(JSON)
    location_time = Column(DateTime(timezone=True))

    @classmethod
    def get_last_attendance_record(cls, user_id: int, timestamp: datetime):
        """
        Get the last attendance record of a date
        :param user_id: user ID of user
        :param timestamp: UTC timestamp
        """
        # For other databases -- not tested yet
        # return db_session.query(cls).filter(
        #     cls.user_id == user_id,
        #     or_(
        #         cls.selfie_time.date() == timestamp.date(),
        #         cls.selfie_time.date() == timestamp.date()
        #     )
        # ).desc().first()

        # For sqlite
        return db_session.query(cls).filter(
            cls.user_id == user_id,
            or_(
                func.DATE(cls.selfie_time) == str(timestamp.date()),
                func.DATE(cls.selfie_time) == str(timestamp.date())
            )
        ).order_by(cls.id.desc()).first()


# Create/Update models
Base.metadata.create_all(engine)

# Create Super HR if not exists
if not User.get_by_emp_id(SUPER_HR["employee_id"]):
    SUPER_HR["temp_pwd"] = get_hashed(SUPER_HR["temp_pwd"])
    super_hr = User(**SUPER_HR)
    db_session.add(super_hr)
    db_session.commit()
