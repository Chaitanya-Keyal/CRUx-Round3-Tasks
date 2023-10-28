import random

import requests
from bs4 import BeautifulSoup


def get_soup(url):
    response = requests.get(
        url, headers={"Referer": "https://www.google.com/", "User-Agent": "Mozilla/5.0"}
    )
    soup = BeautifulSoup(response.content, "xml")
    return soup


def remove_cdata(text: str):
    return text.replace("<![CDATA[", "").replace("]]>", "").strip()


def get_articles_from_rss(url, limit=15):
    """
    Parses the XML data from the news websites.

    Args:
        url (str): The URL of the rss feed.
        limit (int): The number of articles to return.

    Returns:
        list: A list of dictionaries. [{'title': '...', 'link': '...', 'image': '...'}, ...]
    """
    soup = get_soup(url)
    items = soup.find_all("item")
    if items:
        items = random.sample(items, limit)
    else:
        print(url)
    news = []
    for item in items:
        d = {
            "title": remove_cdata(item.title.text),
            "link": remove_cdata(item.link.text),
        }
        try:
            if "https://timesofindia.indiatimes.com" in url:
                d["image"] = item.enclosure["url"]
            elif "http://feeds.bbci.co.uk" in url:
                s = get_soup(d["link"])
                d["image"] = s.find("meta", property="og:image")["content"]
            else:
                d["image"] = item.find("media:content")["url"]
        except TypeError:
            d["image"] = soup.find("image").url.text
        news.append(d)
    return news
