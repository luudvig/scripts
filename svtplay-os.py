#!/usr/bin/env python3

from argparse import ArgumentParser
from os import environ
from subprocess import PIPE, run

parser = ArgumentParser()
parser.add_argument('-f', '--format', default='h264', help='format to download (default: h264)')
parser.add_argument('-m', '--method', default='DASH', help='method to use when downloading (default: DASH)')
parser.add_argument('-o', '--offset', default=1, type=int, help='quality offset to download (default: 1)')
parser.add_argument('-u', '--username', help='username to use when downloading')
parser.add_argument('-p', '--password', help='password to use when downloading')
required_args = parser.add_argument_group('required arguments')
required_args.add_argument('urls', nargs='+', help='url(s) to download', metavar='url')
args = parser.parse_args()

podman_bin = run(['which', 'podman'], stdout=PIPE, check=True, text=True).stdout.rstrip()
podman_cmd = [podman_bin, 'run', '--interactive', '--rm', '--tty', '--volume',
    '{0}/Downloads:/data:Z'.format(environ['HOME']), 'spaam/svtplay-dl']

if args.username and args.password:
    podman_cmd.extend(['--username', args.username, '--password', args.password])

for url in args.urls:
    podman_lines = run(podman_cmd + ['--list-quality', url], stdout=PIPE, check=True, text=True).stdout.splitlines()
    quality_list = {c[1] for c in [l.split() for l in podman_lines[1:]] if c[2] == args.method and c[3] == args.format}

    if not quality_list:
        print('[svtplay-os] No qualities found: {0}'.format(url))
        continue

    quality_pick = sorted(quality_list, key=int, reverse=True)[args.offset]
    run(podman_cmd + ['--quality', quality_pick, '--subtitle', url], check=True)
