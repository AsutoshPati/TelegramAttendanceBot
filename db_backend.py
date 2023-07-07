from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from settings import DB_LOCATION

engine = create_engine("sqlite:///" + DB_LOCATION)  # , echo=True, hide_parameters=False
db_session = sessionmaker(bind=engine)()


def debug_query(query):
    print(query.statement.compile(compile_kwargs={"literal_binds": True}))
