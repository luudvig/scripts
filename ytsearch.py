#!/usr/bin/env python3

from argparse import ArgumentParser
from json import dump, loads
from os import environ, remove
from os.path import splitext
from re import match
from requests import get
from subprocess import CalledProcessError, PIPE, Popen, run
from sys import exit
from tempfile import NamedTemporaryFile

quality_choices = [4320, 2160, 1440, 1080, 720, 480, 360, 240, 144]

parser = ArgumentParser()
parser.add_argument('-d', '--download', action='store_true', help='download all selected videos')
parser.add_argument('-q', '--quality', default=720, type=int, choices=quality_choices, help='max quality (default: 720)', metavar='QUALITY')
parser.add_argument('-r', '--results', default=5, type=int, choices=range(1, 51), help='max results when searching (default: 5)', metavar='RESULTS')
parser.add_argument('-s', '--sort', action='store_const', const='date', default='relevance', help='sort by date when searching')
required_arguments = parser.add_argument_group('required arguments')
required_arguments.add_argument('-k', '--api-key', required=True, help='api key to use when searching')
required_arguments.add_argument('query', nargs='+', help='query to use when searching or url to stream/download')
arguments = parser.parse_args()

bin_ytdl = run(['which', 'youtube-dl'], stdout=PIPE, check=True, text=True).stdout.rstrip()
bin_vlc = run(['which', 'vlc'], stdout=PIPE, check=True, text=True).stdout.rstrip()

if len(arguments.query) == 1 and match('https:\/\/(www\.)?youtu\.?be(\.com)?\/(watch\?v=)?[a-zA-Z0-9-_]{11}', arguments.query[0]):
    webpage_urls = arguments.query
else:
    locator = 'https://youtube.googleapis.com/youtube/v3'
    headers = dict(accept='application/json')

    search_payload = dict(part='id', maxResults=arguments.results, order=arguments.sort, q=' '.join(arguments.query), type='video', key=arguments.api_key)
    search_response = get('{0}/search'.format(locator), headers=headers, params=search_payload)

    videos_payload = dict(part=['contentDetails', 'snippet'], id=[i['id']['videoId'] for i in search_response.json()['items']], key=arguments.api_key)
    videos_response = get('{0}/videos'.format(locator), headers=headers, params=videos_payload)
    videos_items = videos_response.json()['items']

    for c, i in enumerate(videos_items, 1):
        print('{0}. [{1} {2}] {3} ({4})'.format(c, i['snippet']['publishedAt'][:10], i['snippet']['channelTitle'],
            i['snippet']['title'], i['contentDetails']['duration'][2:].lower()))

    try:
        selections = input('[ytsearch] Select video(s) to stream/download (space separated) [1]: ') or '1'
    except KeyboardInterrupt:
        exit('')

    webpage_urls = ['https://www.youtube.com/watch?v={0}'.format(videos_items[int(s) - 1]['id']) for s in selections.split()]
    print('[ytsearch] Video(s) selected: {0}'.format(' '.join(webpage_urls)))

ytdl_selector = ''.join(['(bestvideo{0}/bestvideo{1}){2}+bestaudio{3}/best{2}/bestvideo{2}+bestaudio{3}/(bestvideo{0}/bestvideo{1}/bestvideo){2}+bestaudio/'
    .format('[vcodec^=av01]', '[vcodec=vp9]', '[height<={0}][height>{1}]'.format(quality_choices[c - 1], q), '[ext=m4a]')
    for c, q in enumerate(quality_choices + [0]) if q < arguments.quality])[:-1]

for c, u in enumerate(webpage_urls):
    while True:
        try:
            ytdl_process = run([bin_ytdl, '--dump-json', '--format', ytdl_selector, u], stdout=PIPE, check=True, text=True)
        except CalledProcessError:
            continue
        except KeyboardInterrupt:
            exit('')
        else:
            break

    ytdl_result = loads(ytdl_process.stdout)

    if not (c or arguments.download):
        ytdl_format_ids = ytdl_result['format_id'].split('+')
        ytdl_formats = [f for f in ytdl_result['formats'] if f['format_id'] in ytdl_format_ids]

        vlc_command = [bin_vlc, '--meta-title', splitext(ytdl_result['_filename'])[0], ytdl_formats[0]['url']]
        if len(ytdl_formats) > 1:
            vlc_command.extend(['--input-slave', ytdl_formats[1]['url']])

        Popen(vlc_command, stdout=PIPE, stderr=PIPE)
        continue
    elif ytdl_result['is_live']:
        print('[ytsearch] Ignoring live stream: {0}'.format(u))
        continue

    with NamedTemporaryFile(mode='w', delete=False) as ytdl_temp:
        dump(ytdl_result, ytdl_temp)

    try:
        run([bin_ytdl, '--output', '{0}/Downloads/{1}'.format(environ['HOME'], ytdl_result['_filename']),
            '--load-info-json', ytdl_temp.name, '--format', ytdl_result['format_id']])
    except KeyboardInterrupt:
        continue
    finally:
        remove(ytdl_temp.name)
