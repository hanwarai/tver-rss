import datetime
import json
import requests
import feedgenerator
import csv

feed_file = open('feed.csv')
headers = {'x-tver-platform-type': 'web'}

platform_url = 'https://platform-api.tver.jp/v2/api/platform_users/browser/create'
platform = json.loads(requests.post(platform_url, data={'device_type': 'pc'}).text)
platform_uid = platform.get('result').get('platform_uid')
platform_token = platform.get('result').get('platform_token')

for feed in csv.reader(feed_file):
    print(feed)
    sr_url = "https://statics.tver.jp/content/series/" + feed[0] + ".json"
    sr = json.loads(requests.get(sr_url).text)

    sr_ss_url = "https://service-api.tver.jp/api/v1/callSeriesSeasons/" + feed[0]
    sr_ss = json.loads(requests.get(sr_ss_url, headers=headers).text)

    rss = feedgenerator.Atom1Feed(
        title=sr.get('title'),
        link=sr.get('share').get('url'),
        description=sr.get('description'),
        language="ja",
        image="https://statics.tver.jp/images/content/thumbnail/series/xlarge/" + feed[0] + ".jpg")

    for season in sr_ss.get('result').get('contents'):
        ss_ep_url = "https://platform-api.tver.jp/service/api/v1/callSeasonEpisodes/" \
                    + season.get('content').get('id') \
                    + '?platform_uid=' + platform_uid + '&platform_token=' + platform_token
        ss_ep = json.loads(requests.get(ss_ep_url, headers=headers).text)

        for episode in ss_ep.get('result').get('contents'):
            if episode.get('type') != 'episode':
                continue

            ep_url = "https://statics.tver.jp/content/episode/" + episode.get('content').get('id') + ".json"
            ep = json.loads(requests.get(ep_url).text)

            rss.add_item(
                unique_id=episode.get('content').get('id'),
                title=ep.get('title') + ": " + ep.get('broadcastDateLabel'),
                link=ep.get('share').get('url'),
                description=ep.get('description'),
                pubdate=datetime.datetime.fromtimestamp(ep.get('viewStatus').get('startAt'))
            )

    with open('feeds/' + feed[0] + '.xml', 'w') as fp:
        rss.write(fp, 'utf-8')
