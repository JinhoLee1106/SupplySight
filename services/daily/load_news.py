from services.PostgresHelper import PostgresHelper
from services.daily.get_news import (
    get_news_seafood_source,
    get_news_newsapi
)
from dotenv import load_dotenv
from datetime import date
import os, uuid

load_dotenv(".env.loc")
db_host = os.getenv("POSTGRES_HOST")
db_username = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB")


def load_news_seafood_source(start_date: date = None):
    '''
    use yesterday's date for daily ingestion
    leave start_date empty to write all
    '''
    news_seafood_source = get_news_seafood_source()
    relevant_news = []

    for n in news_seafood_source:
        if not start_date or start_date < n["publication_date"]:    # avoid overwrite using date check
            n["id"] = str(uuid.uuid4())
            n["status"] = "new"
            relevant_news.append(n)
    
    print(f"Found {len(relevant_news)} pieces of news from seafoodsource.com after {start_date}.")

    loader = PostgresHelper(db_host, db_username, db_password, 5432, db_name)
    try:
        loader.update_table("news", relevant_news, "id")
    except Exception as e:
        print(e)
    finally:
        if "loder" in locals():
            loader.close()


def load_news_newsapi(start_date: date, end_date: date):
    '''
    has a date range due to api limit
    for daily ingestion use: start_date = yesterday, end_date = today
    most set up a mechanism to avoid overwrite
    '''
    keywords = ["shrimp", "seafood", "ocean", "india", "ecuador", "indonesia", "vietnam", "thailand"]
    news_newsapi = get_news_newsapi(start_date, end_date, keywords)
    relevant_news = []

    for n in news_newsapi:
        n["id"] = str(uuid.uuid4())
        n["status"] = "new"
        relevant_news.append(n)

    print(f"Found {len(relevant_news)} pieces of potentially relevant news from newsapi between {start_date} and {end_date}.")

    loader = PostgresHelper(db_host, db_username, db_password, 5432, db_name)
    try:
        loader.update_table("news", relevant_news, "id")
    except Exception as e:
        print(e)
    finally:
        if "loader" in locals():
            loader.close()


if __name__ == "__main__":
    load_news_seafood_source(date(2025, 1, 1))
    load_news_newsapi(date(2026, 3, 1), date(2026, 3, 10))
    