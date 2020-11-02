#!/usr/bin/env python3

from argparse import ArgumentParser
from datetime import timedelta
from json import loads
from os import environ
from re import match
from subprocess import PIPE, Popen, run

parser = ArgumentParser()
parser.add_argument('-d', '--download', action='store_true', help='download the video(s)')
parser.add_argument('-n', '--number', type=int, default=1, help='number of search results')
parser.add_argument('-r', '--resolution', type=int, default=1080, help='maximum resolution (height)')
parser.add_argument('search', nargs='+', help='string to search for')
arguments = parser.parse_args()

bin_ytdl = '/usr/local/bin/youtube-dl'
bin_vlc = '/usr/bin/vlc'

if len(arguments.search) == 1 and match('https:\/\/(www\.)?youtu\.?be(\.com)?\/(watch\?v=)?[a-zA-Z0-9-_]{11}', arguments.search[0]):
    webpage_urls = arguments.search
else:
    command = [bin_ytdl, '-j', 'ytsearch{0}:{1}'.format(arguments.number, ' '.join(arguments.search))]
    process = run(command, stdout=PIPE, stderr=PIPE, check=True, text=True)
    results = list(map(lambda l : loads(l), process.stdout.splitlines()))

    for i, r in enumerate(results, 1):
        print('{0}. [{1}] {2} ({3})'.format(i, r['uploader'], r['title'], timedelta(seconds=r['duration'])))

    selections = input('INPUT: Select video(s) to download (space separated) [1]: ') or '1'
    webpage_urls = list(map(lambda s : results[int(s) - 1]['webpage_url'], selections.split()))

command = [bin_ytdl, '-f', 'bestvideo[height<={0}]+bestaudio/best[height<={0}]'.format(arguments.resolution)]

if arguments.download:
    run(command + ['-o', '{0}/Downloads/%(title)s-%(id)s.%(ext)s'.format(environ['HOME'])] + webpage_urls)
else:
    process = run(command + ['-g', webpage_urls[0]], stdout=PIPE, stderr=PIPE, check=True, text=True)
    results = process.stdout.splitlines()

    command = [bin_vlc, '--no-video-title-show', results[0]]
    if len(results) == 2:
        command.extend(['--input-slave', results[1]])

    Popen(command, stdout=PIPE, stderr=PIPE)
