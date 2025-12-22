"""
RSS -> Fediverse gateway

Based on rss2mastodon.py by AI6YR - Nov 2022
"""

import argparse
import logging

import configparser
from mastodon import Mastodon
import random
import requests
import time
import dateutil
import json
import feedparser
from bs4 import BeautifulSoup
import re
import tempfile
import shutil
from PIL import Image


def clean_text(text_in):
    # strip html tags
    text = re.sub("<.*?>", "", text_in)
    text = text.replace("&amp;", "&")
    text = text.replace("&nbsp;", " ")
    return text.strip()


def rss_watcher(config, dry_run=False, process_all=False):

    logger = logging.getLogger(__name__)

    feedurl = config["feed"]["feed_url"]
    feedname = config["feed"]["feed_name"]
    feedvisibility = config["feed"]["feed_visibility"]
    feedtags = config["feed"]["feed_tags"]
    feeddelay = int(config["feed"]["feed_delay"])
    if feeddelay < 60:
        feeddelay = 300
    # max_image_size = int(config["mastodon"]["max_image_size"])

    logger.info("Starting RSS watcher:" + feedname)

    # connect to mastodon
    mastodonBot = Mastodon(
        access_token=config["mastodon"]["access_token"],
        api_base_url=config["mastodon"]["app_url"],
    )

    lastspottime = 0
    seen_entries = []
    while 1:
        data = feedparser.parse(feedurl)
        entries = data["entries"]

        if process_all == False and lastspottime == 0:
            # on first run set lastspot time to the latest entry currently in the feed
            for entry in entries:
                if "published" in entry.keys():
                    spottime = dateutil.parser.parse(
                        entry["published"], tzinfos={"UT": 0}
                    ).timestamp()
                    if spottime > lastspottime:
                        lastspottime = spottime
                if "id" in entry.keys():
                    if entry["id"] not in seen_entries:
                        seen_entries.append(entry["id"])

            logger.debug("Set initial lastspottime={}".format(lastspottime))
            time.sleep(feeddelay * random.random())
            continue

        nextspottime = lastspottime

        logger.debug("Checking feed...")
        for entry in reversed(entries):
            for key in ("id", "link", "published", "title"):
                if key not in entry.keys():
                    logger.warning("skipping entry without key {}".format(key))
                    continue

            spottime = dateutil.parser.parse(
                entry["published"], tzinfos={"UT": 0}
            ).timestamp()
            logger.debug(
                "lastspottime={}, spottime={}, nextspottime={}".format(
                    lastspottime, spottime, nextspottime
                )
            )

            if spottime <= lastspottime:
                logger.debug("skipped old entry...")
                continue

            if entry["id"] in seen_entries:
                logger.warning("skipping new entry with seen id: {}".format(entry["id"]))
                continue

            # good to post

            if spottime > nextspottime:
                logger.debug("Found new later nextspottime={}".format(spottime))
                nextspottime = spottime

            logger.debug("process entry: " + repr(entry))

            tags = []
            if "tags" in entry.keys():
                for tagentry in entry["tags"]:
                    if "term" not in tagentry.keys():
                        continue
                    logger.debug("processing tag term: {}".format(repr(tagentry["term"])))

                    hashtag = ""
                    for word in re.sub("[^ _0-9A-Za-z]", "", tagentry["term"]).split(" "):
                        if word == "":
                            continue
                        hashtag = hashtag + word.capitalize()
                    logger.debug("yeilds tag: #{}".format(hashtag))
                    tags.append("#{}".format(hashtag))

            toot_text = clean_text(entry["title"]) + " " + entry["link"]

            if len(feedtags) > 0:
                toot_text += " " + feedtags

            if len(tags) > 0:
                toot_text += " " + " ".join(tags)

            if len(toot_text) > 475:
                toot_text = toot_text[:472] + "..."

            medialist = []

            #soup = BeautifulSoup(entry["summary"], "html.parser")
            #for img in soup.findAll("img"):
            #    print("***IMAGE:", img.get("src"))
            #    imgfile = img.get("src")
            #    temp = tempfile.NamedTemporaryFile()
            #    res = requests.get(imgfile, stream=True)
            #    if res.status_code == 200:
            #        shutil.copyfileobj(res.raw, temp)
            #        print("Image sucessfully Downloaded")
            #        print(temp.name)
            #        image = Image.open(temp.name)
            #        if (image.size[0] > max_image_size) or (
            #            image.size[1] > max_image_size
            #        ):
            #            origx = image.size[0]
            #            origy = image.size[1]
            #            if origx > origy:
            #                newx = int(max_image_size)
            #                newy = int(origy * (max_image_size / origx))
            #            else:
            #                newy = int(max_image_size)
            #                newx = int(origx * (max_image_size / origy))
            #            image = image.resize((newx, newy))
            #            print("new image size", image.size)
            #            image.save(temp, format="png")
            #        mediaid = mastodonBot.media_post(
            #            temp.name, mime_type="image/jpeg"
            #        )
            #        medialist.append(mediaid)
            #    else:
            #        print("Image Couldn't be retrieved")
            #    temp.close()

            logger.info("Sending toot:{}".format(re.sub("\n", "<nl>", toot_text)))

            if not dry_run:
                try:
                    postedToot = mastodonBot.status_post(
                        toot_text, None, medialist, False, feedvisibility
                    )
                except Exception as e:
                    logger.error(e)

            seen_entries.append(entry["id"])
        lastspottime = nextspottime
        logger.debug("Updated lastspottime to nextspottime: {}".format(lastspottime))
        time.sleep(feeddelay)


def main():

    parser = argparse.ArgumentParser(prog="rss2mastodon")
    parser.add_argument("-c", "--config")
    parser.add_argument("-a", "--all", action="store_true")
    parser.add_argument("-n", "--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-d", "--debug", action="store_true")
    args = parser.parse_args()

    # Debug
    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(filename)s:%(lineno)d %(funcName)s %(levelname)s %(message)s",
        )
    # Verbose
    elif args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Load the config
    config = configparser.ConfigParser()
    config.read(args.config)

    rss_watcher(config=config, dry_run=args.dry_run, process_all=args.all)
