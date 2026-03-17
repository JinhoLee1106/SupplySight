from services.postgres_helper import PostgresHelper
from services.news.get_news import (
    get_news_seafood_source
)
from dotenv import load_dotenv
from datetime import date
import os, uuid

load_dotenv(".env.loc")
newsapi_api_key = os.getenv("NEWSAPI_API_KEY")
claude_api_key = os.getenv("CLAUDE_API_KEY")
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
        if not start_date or start_date < n["publication_date"]:
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
            