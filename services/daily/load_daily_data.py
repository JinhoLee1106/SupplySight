from services.daily.get_daily_data import get_daily_df
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import date
import pandas as pd
import os

load_dotenv(".env.loc")

db_host = os.getenv("POSTGRES_HOST")
db_username = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB")


def load_daily(start_date: date, end_date: date):
    postgres_url = f"postgresql://{db_username}:{db_password}@{db_host}:5432/{db_name}"
    engine = create_engine(postgres_url)

    df_daily = get_daily_df(start_date, end_date)

    try:
        df_daily.to_sql(
            name = "dates_shrimp",
            con = engine,
            if_exists = "append",
            index = False
        )

    except Exception as e:
        print(e)
