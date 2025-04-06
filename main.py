import os
import re
import csv
import logging 
import asyncio
import random
from datetime import datetime
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import aiohttp

load_dotenv()

LINKEDIN_SESSION = os.getenv("LINKEDIN_SESSION")
FILTER_KEYWORDS = [k.strip().lower() for k in os.getenv("FILTER_KEYWORDS", "react,node.js,python").split(",")]
SEARCH_TAGS = os.getenv("SEARCH_TAGS", "#hiring #javascript")
SORT_BY = os.getenv("SORT_BY", "date_posted")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
BANNER_DIR = os.path.join(OUTPUT_DIR, "banners")
MAX_POSTS = int(os.getenv("MAX_POSTS", 10))
SEEN_FILE = os.path.join(OUTPUT_DIR, "seen_links.txt")
ALLOWED_LOCATIONS = [l.strip().lower() for l in os.getenv("ALLOWED_LOCATIONS", "").split(",") if l.strip()]

HEADERS = ["Email Found"]
DISCARDED_HEADERS = ["Poster Name", "Profile Link", "Company", "Post Text", "Post Link", "Timestamp", "Banner Image URL"]

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(BANNER_DIR, exist_ok=True)

async def download_banner_image(session, url, filename):
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(filename, "wb") as f:
                    f.write(await resp.read())
                print(f"📅 Saved banner image: {filename}")
    except Exception as e:
        print(f"❌ Failed to download {url}: {e}")

async def extract_posts():
    seen_links = set()
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            seen_links = set(line.strip() for line in f.readlines())

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            java_script_enabled=True,
            bypass_csp=True,
            ignore_https_errors=True,
            storage_state={"cookies": [{
                "name": "li_at",
                "value": LINKEDIN_SESSION,
                "domain": ".linkedin.com",
                "path": "/",
                "httpOnly": True,
                "secure": True
            }]}
        )

        page = await context.new_page()

        encoded_tags = quote_plus(SEARCH_TAGS)
        search_url = f"https://www.linkedin.com/search/results/content/?keywords=%23hiring%20%23javascript&origin=FACETED_SEARCH&sid=Z%3BD&sortBy=%22date_posted%22"
        await page.goto(search_url, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(2.0, 4.0))

        posts = []
        post_contents = []
        new_links = []
        scroll_count = 0
        #log_file = os.path.join(OUTPUT_DIR, f"linkedin_scraper.log")

        #logging.basicConfig(
            #filemode='a',
            #level=logging.INFO,
           # format='%(asctime)s - %(levelname)s - %(message)s'
        #)
        async with aiohttp.ClientSession() as session:
            while scroll_count < MAX_POSTS:
                await page.mouse.wheel(0, 700)
                await asyncio.sleep(random.uniform(1.5, 2.5))
                scroll_count += 1
                #logging.info('-------------------------------')
                try:
                    elements = await page.query_selector_all("li.artdeco-card.mb2")
                except Exception as e:
                    print(f"❌ Stopping scroll loop due to page crash or redirect: {e}")
                    break
                cnt = 0
                for el in elements:
                    try:
                        content_container = await el.query_selector("div.update-components-text.relative.update-components-update-v2__commentary")
                        content_html = await content_container.inner_html() if content_container else ""
                        content_text = await content_container.inner_text() if content_container else ""
                        lower_content = content_text.lower()

                        link_container = await el.query_selector('div.feed-shared-update-v2')
                        data_urn = await link_container.get_attribute("data-urn") if link_container else None

    # Extract activity ID from urn
                        link = f"https://www.linkedin.com/feed/update/{data_urn.split(':')[-1]}" if data_urn else None
                        #md_file = os.path.join(OUTPUT_DIR, f"linkedin_post_contents.md")
                        #with open(md_file, "a", encoding="utf-8") as f:
                        #   f.writelines(lower_content)
                        #logging.info(not content_text)
                        #logging.info(not link)
                        #logging.info(link in seen_links)
                        #logging.info(cnt)
                        #logging.info(link)
                        #logging.info(seen_links)
                        cnt+=1
                        if not content_text or not link or link in seen_links:
                            continue
                        seen_links.add(link)
                        new_links.append(link)

                        # if not a match, just try downloading banner if present
                        banner_img_el = await el.query_selector("img.update-components-image__image")
                        if banner_img_el:
                            banner_src = await banner_img_el.get_attribute("src")
                            if banner_src and data_urn:
                                filename = os.path.join(BANNER_DIR, f"{data_urn.split(':')[-1]}.jpg")
                                await download_banner_image(session, banner_src, filename)
                        
                        email_match = re.findall(r'[\w\.-]+@(?:[\w\.-]+)', content_text)
                        #logging.info(any("gmail.com" in email.lower() for email in email_match))
                        #logging.info(email_match)
                        if any("gmail.com" in email.lower() for email in email_match):
                            continue
                        #logging.info(ALLOWED_LOCATIONS)
                        location_match = any(loc in lower_content for loc in ALLOWED_LOCATIONS)
                        if not location_match:
                            continue

                        matched_keywords = any(kw in lower_content for kw in FILTER_KEYWORDS)

                        if email_match and matched_keywords:
                            posts.append([", ".join(email_match)])
                            post_contents.append(f"{link}\n{datetime.now().isoformat()}\n{content_html.strip()}\n{'='*80}\n")

                    except Exception:
                        continue

        await browser.close()

        if new_links:
            with open(SEEN_FILE, "a") as f:
                for link in new_links:
                    f.write(link + "\n")

        return posts, post_contents

async def main():
    try:
        posts, post_contents = await extract_posts()
    except Exception as e:
        print(f"❌ Scraping interrupted due to error: {e}")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if posts:
        output_file = os.path.join(OUTPUT_DIR, f"linkedin_emails_{timestamp}.csv")
        with open(output_file, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
            writer.writerows(posts)
        print(f"✅ Saved {len(posts)} emails to {output_file}")

        md_file = os.path.join(OUTPUT_DIR, f"linkedin_post_contents_{timestamp}.md")
        with open(md_file, "w", encoding="utf-8") as f:
            f.writelines(post_contents)
        print(f"📝 Saved post contents to {md_file}")
    else:
        print("No relevant posts found.")

if __name__ == '__main__':
    asyncio.run(main())
