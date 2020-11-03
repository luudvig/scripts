#!/usr/bin/env python3

from argparse import ArgumentParser
from datetime import timedelta
from json import dump, loads
from os import environ, remove
from re import match
from subprocess import CalledProcessError, PIPE, Popen, run
from tempfile import NamedTemporaryFile

parser = ArgumentParser()
parser.add_argument('-d', '--download', action='store_true', help='download all videos')
parser.add_argument('-n', '--number', type=int, default=1, help='number of search results')
parser.add_argument('-r', '--resolution', type=int, default=1080, help='maximum resolution (height)')
parser.add_argument('search', nargs='+', help='string to search for')
arguments = parser.parse_args()

bin_ytdl = run(['which', 'youtube-dl'], stdout=PIPE, stderr=PIPE, check=True, text=True).stdout.rstrip()
bin_vlc = run(['which', 'vlc'], stdout=PIPE, stderr=PIPE, check=True, text=True).stdout.rstrip()

command = [bin_ytdl, '--dump-single-json', '--format', 'bestvideo[height<={0}]+bestaudio/best[height<={0}]'.format(arguments.resolution)]

if len(arguments.search) == 1 and match('https:\/\/(www\.)?youtu\.?be(\.com)?\/(watch\?v=)?[a-zA-Z0-9-_]{11}', arguments.search[0]):
    command.append(arguments.search[0])
else:
    command.append('ytsearch{0}:{1}'.format(arguments.number, ' '.join(arguments.search)))

while True:
    try:
        process = run(command, stdout=PIPE, stderr=PIPE, check=True, text=True)
    except CalledProcessError:
        continue
    else:
        break

results = loads(process.stdout)

if 'entries' in results:
    for i, e in enumerate(results['entries'], 1):
        print('{0}. [{1}] {2} ({3})'.format(i, e['uploader'], e['title'], timedelta(seconds=e['duration'])))
    selections = input('INPUT: Select video(s) to stream/download (space separated) [1]: ') or '1'
    entries = list(map(lambda s : results['entries'][int(s) - 1], selections.split()))
else:
    entries = [results]

if not arguments.download:
    e = entries.pop(0)
    format_ids = e['format_id'].split('+')
    formats = list(filter(lambda f : f['format_id'] in format_ids, e['formats']))
    command = [bin_vlc, '--meta-title', e['title'], '--meta-artist', e['uploader'], formats[0]['url']]
    if len(formats) > 1:
        command.extend(['--input-slave', formats[1]['url']])
    Popen(command, stdout=PIPE, stderr=PIPE)

for e in entries:
    fp = NamedTemporaryFile(mode='w', delete=False)
    dump(e, fp)
    fp.close()
    run([bin_ytdl, '--output', '{0}/Downloads/%(title)s-%(id)s.%(ext)s'.format(environ['HOME']), '--load-info-json', fp.name, '--format', e['format_id']])
    remove(fp.name)
