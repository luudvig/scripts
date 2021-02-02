#!/usr/bin/env python3

from argparse import ArgumentParser
from json import dump, loads
from math import log10
from os import environ, remove
from os.path import splitext
from re import fullmatch
from requests import get
from subprocess import CalledProcessError, PIPE, Popen, run
from sys import exit
from tempfile import NamedTemporaryFile

quality_choices = [4320, 2160, 1440, 1080, 720, 480, 360, 240, 144]

parser = ArgumentParser()
parser.add_argument('-d', '--download', action='store_true', help='download selected video')
parser.add_argument('-i', '--id', action='store_true', help='query argument is treated as video id')
parser.add_argument('-q', '--quality', default=720, type=int, choices=quality_choices, help='max quality (default: 720)', metavar='QUALITY')
parser.add_argument('-r', '--results', default=5, type=int, choices=range(1, 51), help='max results when searching (default: 5)', metavar='RESULTS')
parser.add_argument('-s', '--sort', action='store_const', const='date', default='relevance', help='sort by date when searching')
required_args = parser.add_argument_group('required arguments')
required_args.add_argument('-k', '--api-key', required=True, help='api key to use when searching')
required_args.add_argument('query', nargs='+', help='query to use when searching or url to stream/download')
args = parser.parse_args()

bin_vlc, bin_ytdl = run(['which', 'vlc', 'youtube-dl'], stdout=PIPE, check=True, text=True).stdout.splitlines()

if args.id or fullmatch('https:\/\/(www\.)?youtu\.?be(\.com)?\/(watch\?v=)?[a-zA-Z0-9-_]{11}', args.query[0]):
    webpage_id = args.query[0][-11:]
else:
    locator = 'https://youtube.googleapis.com/youtube/v3'
    headers = {'accept': 'application/json'}

    search_payload = {'part': 'id', 'maxResults': args.results, 'order': args.sort, 'q': ' '.join(args.query), 'type': 'video', 'key': args.api_key}
    search_response = get('{0}/search'.format(locator), headers=headers, params=search_payload)

    videos_payload = {'part': ['contentDetails', 'snippet'], 'id': [i['id']['videoId'] for i in search_response.json()['items']], 'key': args.api_key}
    videos_response = get('{0}/videos'.format(locator), headers=headers, params=videos_payload)
    videos_items = videos_response.json()['items']

    for c, i in enumerate(videos_items, 1):
        print('{0:>{1}}. [{2} {3} {4}] {5} ({6})'.format(c, int(log10(len(videos_items))) + 1, i['snippet']['publishedAt'][:10], i['id'],
            i['snippet']['channelTitle'], i['snippet']['title'], i['contentDetails']['duration'][2:].lower()))

    try:
        webpage_id = videos_items[int(input('[ytsearch] Select video to stream/download [1]: ') or '1') - 1]['id']
    except KeyboardInterrupt:
        exit('')

ytdl_selector = ''.join(['bestvideo{1}[vcodec^=av01]+bestaudio{0}/best{1}{2}/bestvideo{1}{2}+bestaudio{0}/'
    .format('[ext=m4a]', '[height<={0}][height>{1}]'.format(quality_choices[c - 1], q), '[vcodec^=avc1]')
    for c, q in enumerate(quality_choices + [0]) if q < args.quality])[:-1]

try:
    ytdl_process = run([bin_ytdl, '--dump-json', '--format', ytdl_selector, 'https://www.youtube.com/watch?v={0}'.format(webpage_id)],
        stdout=PIPE, check=True, text=True)
except CalledProcessError:
    exit()

ytdl_result = loads(ytdl_process.stdout)

if not args.download:
    ytdl_format_ids = ytdl_result['format_id'].split('+')
    ytdl_urls = [f['url'] for f in ytdl_result['formats'] if f['format_id'] in ytdl_format_ids]

    vlc_command = [bin_vlc, '--meta-title', splitext(ytdl_result['_filename'])[0], ytdl_urls[0]]
    if len(ytdl_urls) > 1:
        vlc_command.extend(['--input-slave', ytdl_urls[1]])

    Popen(vlc_command, stdout=PIPE, stderr=PIPE)
elif ytdl_result['is_live']:
    print('[ytsearch] Ignoring live stream')
else:
    with NamedTemporaryFile(mode='w', delete=False) as ytdl_temp:
        dump(ytdl_result, ytdl_temp)

    try:
        run([bin_ytdl, '--output', '{0}/Downloads/{1}'.format(environ['HOME'], ytdl_result['_filename']),
            '--load-info-json', ytdl_temp.name, '--format', ytdl_result['format_id']])
    except KeyboardInterrupt:
        exit()
    finally:
        remove(ytdl_temp.name)
