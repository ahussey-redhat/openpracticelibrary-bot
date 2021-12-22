#!/usr/bin/environment python3

"""
OpenPracticeLibrary - Twitter Bot
Enumerates the OpenPracticeLibrary Git repo, enumerates the @openpracticelibrary
Twitter user, compares the two to determine if there are any missing tweets.

If there is a missing tweet, the `oplbot` will schedule the tweet with the pre-
defined format of:

```tweet
title

purpose

author tags

icon

link
```
"""

import argparse
from genericpath import isdir
import urllib3
import json
import os
import subprocess
import logging
import os
import sys

import yaml

PARSER = argparse.ArgumentParser(
    description="OpenPracticeLibrary - Twitter Bot"
)
PARSER.add_argument(
    "-c", "--config", default="config.yaml"
)
PARSER.add_argument(
    "-v", "--verbose", help="Increase application verbosity", action="store_true"
)
ARGS = PARSER.parse_args()

LOG_LEVEL = logging.INFO
if ARGS.verbose:
    LOG_LEVEL = logging.DEBUG

LOGGER = logging.getLogger("oplbot")
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


OPL_PRACTICES_LOCATION = (
    "https://github.com/openpracticelibrary/openpracticelibrary.git"
)
OPL_PRACTICES_DIRECTORY = "openpracticelibrary/src/pages/practice"
CONFIG_FILE_PATH = 'config.yaml' if os.path.isfile('config.yaml') else 'config.yml'

def _parse_config():
    """
    parses a configuration file and sets environment variables
    """
    with open(CONFIG_FILE_PATH, 'r') as fp:
        content = yaml.safe_load(fp)
        os.environ['bearer_token'] = content['bearer_token']

def _compare_lists(list1, list2):
    """
    compare two list and return the diff
    :returns: [list] diff between two lists
    """
    not_tweeted_practices = []
    for practice in list1:
        count = 0
        for tweet in list2:
            if practice['title'] == tweet:
                LOGGER.info('Tweet exist')
                count += 1
        if count == 0:
            not_tweeted_practices.append(practice)
    return not_tweeted_practices

def _get_current_tweets():
    """
    get a list of current tweets by the OpenPracticeLibrary
    returns: [list] list of current tweets
    """
    http = urllib3.PoolManager()
    resp = http.request(
        "GET",
        "https://api.twitter.com/2/users/1321838110133673984/tweets?tweet.fields=created_at&max_results=100",
        headers={'Authorization': f"Bearer {os.getenv('bearer_token')}"})
    if resp.status != 200:
        LOGGER.critical(f"HTTP Error: {resp.status}")
        sys.exit(1)
    if resp.status == 200:
        parsed_tweets = []
        for tweet in json.loads(resp.data.decode('UTF-8'))['data']:
            unparsed_tweet = tweet['text'].split('\n')
            LOGGER.debug(unparsed_tweet)
            parsed_tweet = unparsed_tweet[0].strip()
            parsed_tweets.append(parsed_tweet)
        return parsed_tweets

def _get_file_listing(directory):
    """
    get a list of all files and directories within a given directory
    :param directory: [str] file path to a directory
    :returns: [list] list of files and directories
    """
    return os.listdir(directory)


def _check_for_directory(directory):
    """
    check if a directory exists
    :param directory: [str] file path to a directory
    :returns: [bool] True/False depending on whether the directory exists
    """
    if os.path.isdir(directory):
        return True
    return False


class openpracticelibrarybot:
    """
    OpenPracticeLibrary - Twitter Bot
    Posts Tweets based on OpenPracticeLibrary Practices.
    """

    def __init__(self):
        """
        initialises the application
        """
        self.run()

    def run(self):
        """
        runs the applications
        """
        print("Starting...")
        logging.info("Gathering pre-requisits")
        cwd = os.getcwd()
        if not _check_for_directory("openpracticelibrary"):
            subprocess.run(["git", "clone", OPL_PRACTICES_LOCATION])
        os.chdir(OPL_PRACTICES_DIRECTORY)
        subprocess.run(['git', 'checkout', 'master'])
        subprocess.run(['git', 'pull'])
        os.chdir(cwd)
        _parse_config()
        self.current_practices = _get_file_listing(OPL_PRACTICES_DIRECTORY)
        LOGGER.debug(f"Practices:\n{json.dumps(self.current_practices, indent=2)}")
        self.practices = self._get_current_practices_details()
        LOGGER.debug(f"Practices Details: {json.dumps(self.practices, indent=2)}")
        LOGGER.info(f"Found {len(self.current_practices)} practices")
        LOGGER.info(f"Parsed {len(self.practices)} practices")
        self.current_tweets = _get_current_tweets()
        LOGGER.debug(f"Current tweets: {json.dumps(self.current_tweets, indent=2)}")
        self.not_tweeted_practices = _compare_lists(self.practices, self.current_tweets)
        LOGGER.info(f"Not tweeted practices: {json.dumps(self.not_tweeted_practices, indent=2)}")

    def _get_current_practices_details(self):
        """
        get details for all the current practices. IE title, purpose, author, icon, url
        :returns: dict - dictionary containing all the current practices with details
        """
        practices = []
        for practice in self.current_practices:
            practice_file_name = practice
            practice_name = practice_file_name.replace(".md", "")
            with open(f"{OPL_PRACTICES_DIRECTORY}/{practice}") as of:
                try:
                    document_details = {}
                    for document in yaml.safe_load_all(of):
                        practice_name = practice.replace(".md", "")
                        document_details["title"] = document["title"]
                        document_details["purpose"] = document["subtitle"]
                        document_details["authors"] = document["authors"]
                        document_details["icon"] = document["icon"]
                        document_details["file_name"] = practice_file_name
                        document_details[
                            "url"
                        ] = f"https://openpracticelibrary.com/practice/{practice_name}/"
                        break
                    practices.append(document_details)
                except yaml.reader.ReaderError:
                    LOGGER.warning(f"Unicode exception when parsing: \"{practice_file_name}\"")
                    pass
        return practices


def run():
    """
    responsible for starting the application correctly
    """
    openpracticelibrarybot()


if __name__ == "__main__":
    run()
