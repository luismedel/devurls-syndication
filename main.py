import os
import requests
import bs4
import jinja2
import re


RSS_TEMPLATE = """
<rss version="2.0">
<channel>
    <title>{{ title }}</title>
    <link>{{ link }}</link>
    <description>{{ description }}</description>
    {% for item in items %}
    <item>
        <title>{{ item.title }}</title>
        <link>{{ item.link }}</link>
        <pubDate>{{ item.published }}</pubDate>
    </item>
    {% endfor %}
</channel>
</rss>
"""
_rss_template = jinja2.Template(RSS_TEMPLATE)


INDEX_TEMPLATE = """
<html>
    <body>
        <ul>
        <li><a href="all.xml">All feeds</a></li>
        {% for feed in feeds %}
            <li><a href="{{ feed.slug }}.xml">{{ feed.title }}</a></li>
        {% endfor %}
        </ul>
    </body>
</html>
"""
_index_template = jinja2.Template(INDEX_TEMPLATE)


def slugify(value: str) -> str:
    if not value:
        return value
    value = re.sub(r"[^a-z0-9-]+", "-", value.lower())
    return re.sub(r"\-+", "-", value)


def download_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def process_html(html) -> dict:
    soup = bs4.BeautifulSoup(html, 'html.parser')

    result: dict = {}

    for feed_block in soup.select('div.publisher-block'):
        items: list = []

        title = feed_block.select_one('.publisher-text .title').text
        feed = {
            "title": title,
            "slug": slugify(title),
            "link": feed_block.select_one('.publisher-icon a')["href"],
            "items": items
        }
        result[feed["slug"]] = feed

        for publisher_block in feed_block.select('.publisher-link'):
            published = publisher_block.select_one('.aside > .text')["title"].split('on ')[1]
            link = publisher_block.select_one('.link > a')

            items.append({
                "title": link.text,
                "published": published,
                "link": link["href"],
            })

    return result


def render_feed(feed: dict) -> None:
    with open(f"output/{feed["slug"]}.xml", "w") as f:
        f.write(_rss_template.render(**feed))

def render_index(feeds: dict) -> None:
    with open(f"output/index.html", "w") as f:
        f.write(_index_template.render(feeds=feeds.values()))

if __name__ == "__main__":
    TITLE = "DevURLs"
    URL = "https://devurls.com/"

    os.makedirs("output", exist_ok=True)

    html_content = download_html(URL)

    feeds = process_html(html_content)
    all_items = []
    for slug, feed in feeds.items():
        if not slug:
            print(f"[*] Item without slug? {feed}")
            continue
        render_feed(feed)

        all_items.extend(feed["items"])

    render_feed({
        "title": TITLE,
        "link": URL,
        "slug": "all",
        "items": all_items
    })

    render_index(feeds)
