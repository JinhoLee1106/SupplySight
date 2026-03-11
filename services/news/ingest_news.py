from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
from services.postgres_helper import PostgresHelper
from services.news.db_setup import set_up
from services.news.transform import generate_structured_news
from anthropic import AsyncAnthropic
import asyncio
import uuid
import requests
import os


load_dotenv()
newsapi_api_key = os.getenv("NEWSAPI_API_KEY")
claude_api_key = os.getenv("CLAUDE_API_KEY")
db_host = os.getenv("POSTGRES_HOST")
db_username = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB")

base_url = "https://newsapi.org/v2/everything"
model = "claude-haiku-4-5"
client = AsyncAnthropic(api_key = claude_api_key)


def get_news(params: dict)-> list:
    '''
    Get the relevant news

    Parameters
    params (dict) : 
        {
            "apiKey": str,
            "from": str(%Y-%m-%d),
            "to": str(%Y-%m-%d),
            "language": str,
            "q": str
        }
    '''
    response = requests.get(base_url, params=params).json()
    raw_articles = response.get("articles")
    articles = [
        {
            "uuid": str(uuid.uuid4()),
            "source": raw_article.get("source", {}).get("name"),
            "title": raw_article.get("title"),
            "description": raw_article.get("description"),
            "publishedAt": raw_article.get("publishedAt"),
            "url": raw_article.get("url"),
            "processed": False
        }
        for raw_article in raw_articles
    ]
    return articles


def store_raw_news(params: dict)-> list:
    '''
    Store news that have not been transformed to a database
    For data recovery in case of crash
    '''
    raw_news = get_news(params)
    if not raw_news:
        print("No news to write")
        return
    
    loader = PostgresHelper(db_host, db_username, db_password, 5432, db_name)
    try:
        loader.update_table("rawnews", raw_news, primary_key="uuid")
        print(f"{len(raw_news)} articles wrote to rawnews")
        
    except Exception as e:
        print(e)
    finally:
        if 'loader' in locals():
            loader.close()


def get_raw_news()-> list:
    '''
    get all unprocessed news items
    '''
    table = []
    try:
        reader = PostgresHelper(db_host, db_username, db_password, 5432, db_name)
        filter = {"processed": False}
        filter["source"] = "Fox News"
        sort = {"publishedAt": False}
        table = reader.read_table("rawnews", filter, sort)
    except Exception as e:
        print(e)
    finally:
        if 'reader' in locals():
            reader.close()

    raw_news = [
        {
            "uuid": article[0],
            "source": article[1],
            "title": article[2],
            "description": article[3],
            "publishedAt": article[4]
        }
        for article in table
    ]
    return raw_news

async def process_raw_news(raw_news):
    tasks = [generate_structured_news(
        {"article": article["description"], "title": article["title"]}, 
        client) 
    for article in raw_news]
    evaluations = await asyncio.gather(*tasks)

    to_raw_news, to_news  = [], []

    for i, eval in enumerate(evaluations):
        raw, structured = {"uuid": raw_news[i]["uuid"], "processed": True}, raw_news[i]
        to_raw_news.append(raw)
        if not eval:
            continue
        
        structured["score"] = eval.get("score")
        structured["products"] = eval.get("affected_products")
        to_news.append(structured)

    writer = PostgresHelper(db_host, db_username, db_password, 5432, db_name)
    try:
        if to_news:
            writer.update_table("news", to_news, primary_key="uuid")
        writer.update_table("rawnews", to_raw_news, primary_key="uuid")
    except Exception as e:
        print(e)
    finally:
        if 'writer' in locals():
            writer.close()

    print(f"Successfully processed {len(to_raw_news)} raw news. {len(to_news)} of them were relevant.")


'''set_up()
date_yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime('%Y-%m-%d')
p = {
    "apiKey": newsapi_api_key,
    "from": date_yesterday,
    "to": date_yesterday,
    "language": "en",
    "q": "tomato OR avocado"
}
store_raw_news(p)
raw_news = get_raw_news()
asyncio.run(process_raw_news(raw_news))'''
