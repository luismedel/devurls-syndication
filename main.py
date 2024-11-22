import os
import requests
import bs4
import jinja2
import re

jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader("./templates"))

ATOM_TEMPLATE = jinja_env.get_template("template.atom")
RSS_TEMPLATE = jinja_env.get_template("template.rss")
INDEX_TEMPLATE = jinja_env.get_template("index.html")


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


def render(template: jinja2.Template, feed: dict, ext: str) -> None:
    with open(f"output/{feed['slug']}.{ext}", "w") as f:
        f.write(template.render(**feed))


def render_index(feeds: list) -> None:
    with open(f"output/index.html", "w") as f:
        f.write(INDEX_TEMPLATE.render(feeds=feeds))


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)

    html_content = download_html("https://devurls.com/")

    feeds = process_html(html_content)
    all_items = []

    for slug, feed in feeds.items():
        all_items.extend(feed["items"])
        if not slug:
            print(f"[*] Item without slug? {feed}")
            continue
        render(RSS_TEMPLATE, feed, "xml")
        render(ATOM_TEMPLATE, feed, "atom")

    all_feeds = {
        "title": "devurls syndication",
        "link": "https://luismedel.github.io/devurls-syndication/",
        "slug": "all",
        "items": all_items
    }

    render(RSS_TEMPLATE, all_feeds, "xml")
    render(ATOM_TEMPLATE, all_feeds, "atom")
    render_index(feeds.values())
