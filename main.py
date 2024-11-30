import os
import requests
import bs4
import jinja2
import re

ROOT_URL = "https://luismedel.github.io/devurls-syndication/"

jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader("./templates"))

ATOM_TEMPLATE = jinja_env.get_template("template.atom")
RSS_TEMPLATE = jinja_env.get_template("template.rss")
INDEX_TEMPLATE = jinja_env.get_template("index.html")
OPML_TEMPLATE = jinja_env.get_template("index.opml")
HOME_TEMPLATE = jinja_env.get_template("home.html")


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


def process_html(html: str) -> dict:
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


def render(template: jinja2.Template, slug: str, feed: dict, ext: str) -> None:
    with open(f"output/{slug}/{feed['slug']}.{ext}", "w") as f:
        f.write(template.render(url_slug=slug, **feed))


def render_index(template: jinja2.Template, slug: str, feeds: list, ext: str) -> None:
    with open(f"output/{slug}/index.{ext}", "w") as f:
        f.write(template.render(feeds=feeds, url_slug=slug))


def generate(url: str) -> str:
    print(f"[*] Processing {url}...")
    
    url_slug = slugify(url.replace("https://", "")
                       .replace("http://", "")
                       .replace("/", ""))
    os.makedirs(f"output/{url_slug}", exist_ok=True)

    html_content = download_html(url)
    feeds = process_html(html_content)
    all_items = []

    for slug, feed in feeds.items():
        all_items.extend(feed["items"])
        if not slug:
            print(f"[*] Item without slug? {feed}")
            continue
        render(RSS_TEMPLATE, url_slug, feed, "xml")
        render(ATOM_TEMPLATE, url_slug, feed, "atom")

    all_feeds = {
        "title": f"{url_slug} syndication",
        "link": f"{ROOT_URL}{url_slug}/",
        "slug": "all",
        "items": all_items
    }

    render(RSS_TEMPLATE, url_slug, all_feeds, "xml")
    render(ATOM_TEMPLATE, url_slug, all_feeds, "atom")
    render_index(INDEX_TEMPLATE, url_slug, feeds.values(), "html")
    render_index(OPML_TEMPLATE, url_slug, feeds.values(), "opml")

    return f"{ROOT_URL}{url_slug}/"


if __name__ == "__main__":
    pages: dict = {}
    
    for url in ["https://devurls.com/", "https://techurls.com/", 
                "https://sciurls.com/", "https://mathurls.com/",
                "https://hwurls.com/", "https://finurls.com/",
                "https://physurls.com/", "https://tuxurls.com/"]:
        output = generate(url)
        pages[url] = output

    with open("output/index.html", "w") as f:
        f.write(HOME_TEMPLATE.render(pages=pages))
