import csv
import datetime
import json
import os

import feedgenerator
import requests
from jinja2 import Environment, FileSystemLoader

SSL_VERIFY = os.getenv('SSL_VERIFY', 'True') == 'True'
feed_file = open('feed.csv')
headers = {'x-tver-platform-type': 'web'}

platform_url = 'https://platform-api.tver.jp/v2/api/platform_users/browser/create'
platform = json.loads(requests.post(platform_url, data={'device_type': 'pc'}, verify=SSL_VERIFY).text)
platform_uid = platform.get('result').get('platform_uid')
platform_token = platform.get('result').get('platform_token')

rendered_feeds = []
for feed in csv.reader(feed_file):
    print(feed)
    sr_url = "https://statics.tver.jp/content/series/" + feed[0] + ".json"
    sr = json.loads(requests.get(sr_url, verify=SSL_VERIFY).text)

    sr_ss_url = "https://service-api.tver.jp/api/v1/callSeriesSeasons/" + feed[0]
    sr_ss = json.loads(requests.get(sr_ss_url, headers=headers, verify=SSL_VERIFY).text)

    title = sr.get('title')
    rendered_feeds.append({'id': feed[0], 'title': title})

    rss = feedgenerator.Atom1Feed(
        title=title,
        link=sr.get('share').get('url'),
        description=sr.get('description'),
        language="ja",
        image="https://statics.tver.jp/images/content/thumbnail/series/xlarge/" + feed[0] + ".jpg")

    for season in sr_ss.get('result').get('contents'):
        ss_ep_url = "https://platform-api.tver.jp/service/api/v1/callSeasonEpisodes/" \
                    + season.get('content').get('id') \
                    + '?platform_uid=' + platform_uid + '&platform_token=' + platform_token
        ss_ep = json.loads(requests.get(ss_ep_url, headers=headers, verify=SSL_VERIFY).text)

        for episode in ss_ep.get('result').get('contents'):
            if episode.get('type') != 'episode':
                continue

            ep_url = "https://statics.tver.jp/content/episode/" + episode.get('content').get('id') + ".json"
            ep = json.loads(requests.get(ep_url, verify=SSL_VERIFY).text)

            rss.add_item(
                unique_id=episode.get('content').get('id'),
                title=ep.get('title') + ": " + ep.get('broadcastDateLabel'),
                link=ep.get('share').get('url'),
                description=ep.get('description'),
                pubdate=datetime.datetime.fromtimestamp(ep.get('viewStatus').get('startAt')),
                content=""
            )

    with open('feeds/' + feed[0] + '.xml', 'w') as fp:
        rss.write(fp, 'utf-8')

# Generate index.html
jinja_env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=True
)
jinja_template = jinja_env.get_template('index.html')
index = open('feeds/index.html', 'w')
index.write(jinja_template.render(feeds=rendered_feeds))
