from datetime import datetime
from bs4 import BeautifulSoup 
import requests

seafood_source_url = "https://www.seafoodsource.com/pricing/archive"
seafood_source_header = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }


def get_news_seafood_source() -> list[dict]: 
    response = requests.get(seafood_source_url, headers=seafood_source_header)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('h2')

        all_news = []

        for article in articles:
            link_tag = article.find('a')

            if link_tag:
                news = dict()

                title = link_tag.get_text(strip=True)
                sub_url = link_tag.get('href')
                date = get_news_date_seafood_source(sub_url)

                news["source"] = "seafood_source"
                news["title"] = title
                news["content"] = title # content paywalled, title is basically summary
                news["url"] = sub_url # 
                news["publication_date"] = date

                all_news.append(news)

        return all_news
             
             
def get_news_date_seafood_source(sub_url: str) -> datetime.date:
    full_url = f"https://www.seafoodsource.com{sub_url}"
    response = requests.get(full_url, headers=seafood_source_header)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        date_div = soup.select_one('div.article__date')
        date_str = date_div.get_text(strip=True)
        date = datetime.strptime(date_str, "%B %d, %Y").date()
        return date
