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
import csv
import json
import os
import subprocess
import logging
import os
import sys

from genericpath import isdir

import urllib3
import yaml

VERSION = '0.0.1'

PARSER = argparse.ArgumentParser(
    description="OpenPracticeLibrary - Twitter Bot"
)
PARSER.add_argument(
    "-a", "--all", help="Schedule tweets for all practices, not just ones that haven't been tweeted before"
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
    if ARGS.all:
        not_tweeted_practices = list1
    if not ARGS.all:
        not_tweeted_practices = []
        for practice in list1:
            count = 0
            for tweet in list2:
                if practice['title'] == tweet:
                    count += 1
            if count == 0:
                not_tweeted_practices.append(practice)
                LOGGER.debug(f"Not tweeted: {json.dumps(practice, indent=2)}")
    return not_tweeted_practices

def _parse_tweets(tweets, parsed_tweets):
    """
    parse a json blob of tweets
    :param array: tweets, each tweet is a dict
    :param array: tweets that have already been parsed
    :returns: parsed_tweets
    """
    for tweet in tweets:
        unparsed_tweet = tweet['text'].split('\n')
        LOGGER.debug(unparsed_tweet)
        parsed_tweet = unparsed_tweet[0].strip()
        LOGGER.debug(f"Parsed tweet: {parsed_tweet}")
        parsed_tweets.append(parsed_tweet)
    return parsed_tweets

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
        meta_data = json.loads(resp.data.decode('UTF-8'))['meta']
        parsed_tweets = _parse_tweets(json.loads(resp.data.decode('UTF-8'))['data'], parsed_tweets)
        try:
            while meta_data['next_token']:
                LOGGER.debug(f"Next token: {json.dumps(meta_data['next_token'], indent=2)}")
                LOGGER.debug('Parsing next page')
                resp = http.request(
                    "GET",
                    f"https://api.twitter.com/2/users/1321838110133673984/tweets?tweet.fields=created_at&max_results=100&pagination_token={meta_data['next_token']}",
                    headers={'Authorization': f"Bearer {os.getenv('bearer_token')}"})
                meta_data = json.loads(resp.data.decode('UTF-8'))['meta']
                parsed_tweets = _parse_tweets(json.loads(resp.data.decode('UTF-8'))['data'], parsed_tweets)
        except KeyError as key_err:
            parsed_tweets = _parse_tweets(json.loads(resp.data.decode('UTF-8'))['data'], parsed_tweets)
        return  parsed_tweets

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

def _convert_to_csv(json_blob):
    """
    receive a json blob which as an array with nested dictionaries, and
    convert them into a csv file
    :param json_blob: json array with nested dictionaries
    """

    fieldnames = json_blob[0].keys()
    with open('opl_practices.csv', 'w') as of:
        csvwriter = csv.DictWriter(of, fieldnames=fieldnames)
        csvwriter.writeheader()
        for practice in json_blob:
            csvwriter.writerow(practice)

def _convert_from_csv(path_to_csv):
    """
    convert a CSV file to a list
    :param str path_to_csv: path to the CSV file
    :returns dict: dictionary of each author mapped to their Twitter ID
    """
    authors = {}
    with open(path_to_csv, 'r') as fp:
        reader = csv.reader(fp)
        data = list(reader)
    for author_instance in data:
        if author_instance == data[0]:
            continue
        author = author_instance[0].split('.')[0]
        if author_instance[1] == "" or author_instance[1] == "--":
            twitter_handle = f"https://github.com/{author}"
        if author_instance[1] != "" and author_instance[1] != "--":
            twitter_handle = f"@{author_instance[1]}"
        authors[author.lower()] = twitter_handle
    return authors

def _get_scheduled_tweets():
    """
    get scheduled tweets
    :returns: array of dicts of each scheduled tweet or None
    """
    http = urllib3.PoolManager()
    resp = http.request(
        "GET",
        "https://api.twitter.com/10/accounts/1321838110133673984/scheduled_tweets",
        headers={'Authorization': f"Bearer {os.getenv('bearer_token')}"})
    if resp.status != 200:
        LOGGER.critical(f"HTTP Error: {resp.status}")
        sys.exit(1)
    if resp.status == 200:
        print(json.dumps(resp.data))
        return resp.json

class openpracticelibrarytweetbot:
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
        subprocess.run(['git', 'checkout', 'main'])
        subprocess.run(['git', 'pull'])
        os.chdir(cwd)
        _parse_config()
        self.current_practices = _get_file_listing(OPL_PRACTICES_DIRECTORY)
        LOGGER.debug(f"Practices:\n{json.dumps(self.current_practices, indent=2)}")
        self.authors = _convert_from_csv('authors.csv')
        LOGGER.debug(f"Authors: {json.dumps(self.authors, indent=2)}")
        LOGGER.info(f"Authors mapped: {len(self.authors)}")
        self.practices = self._get_current_practices_details()
        LOGGER.debug(f"Practices Details: {json.dumps(self.practices, indent=2)}")
        LOGGER.info(f"Found {len(self.current_practices)} practices")
        LOGGER.info(f"Parsed {len(self.practices)} practices")
        self.current_tweets = _get_current_tweets()
        LOGGER.debug(f"Current tweets: {json.dumps(self.current_tweets, indent=2)}")
        self.not_tweeted_practices = _compare_lists(self.practices, self.current_tweets)
        LOGGER.debug(f"Not tweeted practices: {json.dumps(self.not_tweeted_practices, indent=2)}")
        _convert_to_csv(self.not_tweeted_practices)
        #self.scheduled_tweets = _get_scheduled_tweets()
        LOGGER.info('Complete')

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
                        document_details[
                            "url"
                        ] = f"https://openpracticelibrary.com/practice/{practice_name}/"
                        try:
                            authors = []
                            for author in document["authors"]:
                                authors.append(f"🙏🏻 {self.authors[author.lower()]}")
                            document_details["authors"] = ' '.join(authors)
                        except KeyError as key_err:
                            LOGGER.warning(f"Missing author details: {key_err} for practice \'{document['title']}\'")
                            document_details["authors"] = ' '.join([f"🙏🏻 https://github.com/" + sub for sub in document["authors"]])
                            pass
                        document_details["icon"] = f"https://openpracticelibrary.com{document['icon']}"
                        document_details["file_name"] = practice_file_name
                        break
                    practices.append(document_details)
                except yaml.reader.ReaderError:
                    LOGGER.warning(f"Unicode exception when parsing: \"{practice_file_name}\"")
                    pass
        return practices


def main():
    """
    responsible for starting the application correctly
    """
    openpracticelibrarytweetbot()


if __name__ == "__main__":
    main()
