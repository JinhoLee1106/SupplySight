from services.postgres_helper import PostgresHelper
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv("POSTGRES_HOST")
db_username = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
base_url = "https://newsapi.org/v2/everything"


def set_up():
    try:
        db_creater = PostgresHelper(db_host, db_username, db_password, 5432)
        db_creater.create_database("SUPPLYSIGHT")
    except Exception as e:
        print(e)
    finally:
        if 'db_creater' in locals():
            db_creater.close()

    try:
        table_creator = PostgresHelper(db_host, db_username, db_password, 5432, "SUPPLYSIGHT")

        raw_news_table_format = {
            "uuid": "TEXT PRIMARY KEY",
            "source": "TEXT",
            "title": "TEXT",
            "description": "TEXT",
            "publishedAt": "TIMESTAMP",
            "url": "TEXT",
            "processed": "BOOLEAN"
        }
        table_creator.create_table("rawnews", raw_news_table_format)

        news_table_format = {
            "uuid": "TEXT PRIMARY KEY",
            "source": "TEXT",
            "title": "TEXT",
            "description": "TEXT",
            "publishedAt": "TIMESTAMP",
            "url": "TEXT",
            "score": "INTEGER",
            "products": "TEXT[]"
        }
        table_creator.create_table("news", news_table_format)
        
    except Exception as e:
        print(e)
    finally:
        if 'Exception' in locals():
            Exception.close()
    
    print("Complete database setup")
