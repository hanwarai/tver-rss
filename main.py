import json
import requests
import feedgenerator
import csv

feed_file = open('feed.csv')
for feed in csv.reader(feed_file):
    print(feed)
    url = "https://statics.tver.jp/content/episode/" + feed[0] + ".json"
    json_text = requests.get(url).text
    json_dict = json.loads(json_text)

    rss = feedgenerator.Atom1Feed(
        title=feed[1],
        link=json_dict.get('share').get('url'),
        description="",
        language="ja", )

    rss.add_item(
        title=json_dict.get('title'),
        link=json_dict.get('share').get('url'),
        description=json_dict.get('description'))

    with open('feeds/' + feed[0] + '.xml', 'w') as fp:
        rss.write(fp, 'utf-8')
