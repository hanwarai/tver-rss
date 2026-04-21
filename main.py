import csv
import datetime
import os

import feedgenerator
import requests
from jinja2 import Environment, FileSystemLoader

SSL_VERIFY = os.getenv('SSL_VERIFY', 'True') == 'True'
TIMEOUT = (5, 30)
TVER_HEADERS = {'x-tver-platform-type': 'web'}


def fetch_json(method, url, **kwargs):
    response = requests.request(method, url, verify=SSL_VERIFY, timeout=TIMEOUT, **kwargs)
    response.raise_for_status()
    return response.json()


def create_platform_session():
    result = fetch_json(
        'POST',
        'https://platform-api.tver.jp/v2/api/platform_users/browser/create',
        data={'device_type': 'pc'},
    )
    return result['result']['platform_uid'], result['result']['platform_token']


def build_series_feed(series_id, platform_uid, platform_token):
    sr = fetch_json('GET', f'https://statics.tver.jp/content/series/{series_id}.json')
    sr_ss = fetch_json(
        'GET',
        f'https://service-api.tver.jp/api/v1/callSeriesSeasons/{series_id}',
        headers=TVER_HEADERS,
    )

    title = sr['title']
    rss = feedgenerator.Atom1Feed(
        title=title,
        link=sr['share']['url'],
        description=sr.get('description'),
        language='ja',
        image=f'https://statics.tver.jp/images/content/thumbnail/series/xlarge/{series_id}.jpg',
    )

    for season in sr_ss['result']['contents']:
        season_id = season['content']['id']
        ss_ep = fetch_json(
            'GET',
            f'https://platform-api.tver.jp/service/api/v1/callSeasonEpisodes/{season_id}',
            headers=TVER_HEADERS,
            params={'platform_uid': platform_uid, 'platform_token': platform_token},
        )

        for episode in ss_ep['result']['contents']:
            if episode.get('type') != 'episode':
                continue

            ep_id = episode['content']['id']
            ep = fetch_json('GET', f'https://statics.tver.jp/content/episode/{ep_id}.json')

            rss.add_item(
                unique_id=ep_id,
                title=f'{ep["title"]}: {ep["broadcastDateLabel"]}',
                link=ep['share']['url'],
                description=ep.get('description'),
                pubdate=datetime.datetime.fromtimestamp(
                    ep['viewStatus']['startAt'], tz=datetime.timezone.utc
                ),
                content='',
            )

    return title, rss


def main():
    platform_uid, platform_token = create_platform_session()

    rendered_feeds = []
    with open('feed.csv') as feed_file:
        for feed in csv.reader(feed_file):
            series_id = feed[0]
            print(feed)
            try:
                title, rss = build_series_feed(series_id, platform_uid, platform_token)
                with open(f'feeds/{series_id}.xml', 'w') as fp:
                    rss.write(fp, 'utf-8')
                rendered_feeds.append({'id': series_id, 'title': title})
            except Exception as exc:
                print(f'[ERROR] {series_id}: {exc}')

    jinja_env = Environment(loader=FileSystemLoader('templates'), autoescape=True)
    with open('feeds/index.html', 'w') as index:
        index.write(jinja_env.get_template('index.html').render(feeds=rendered_feeds))


if __name__ == '__main__':
    main()
