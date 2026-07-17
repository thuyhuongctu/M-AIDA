#!/usr/bin/env python3
"""Regenerate every M-AIDA audio asset with the HeyGen API.

The site ships three families of audio, all listed in manifest.json:

  * guided-tour narration      voice/stop1-6.mp3 and voice/vi/stop1-6.mp3
  * atlas country notes        voice/atlas/*.mp3 (English + Vietnamese)
  * theme-song vocal track     assets/heygen/maida_song_vocal.mp3

Every file is also mirrored into docs/ for GitHub Pages; the manifest lists
both output paths so one run keeps the mirrors in sync.

HeyGen's public API produces avatar videos, not bare audio, so each script is
rendered as a minimal video (any avatar works) and the sound track is then
extracted and loudness-normalized with ffmpeg into the final mp3.

Usage:
  export HEYGEN_API_KEY=...        # never hardcode or commit the key
  python voice/heygen/generate.py --list-voices
  python voice/heygen/generate.py --dry-run
  python voice/heygen/generate.py                    # everything
  python voice/heygen/generate.py --group tour --lang vi
  python voice/heygen/generate.py --only tour_en_stop1,atlas_vi_vietnam

Requires: python3, requests, ffmpeg on PATH.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

try:
    import requests
except ImportError:  # keep the tool usable for --dry-run without requests
    requests = None

API_BASE = 'https://api.heygen.com'
POLL_INTERVAL_SECONDS = 8
POLL_TIMEOUT_SECONDS = 15 * 60
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), 'manifest.json')


def fail(message):
    print(f'error: {message}', file=sys.stderr)
    sys.exit(1)


def api_key():
    key = os.environ.get('HEYGEN_API_KEY')
    if not key:
        fail('HEYGEN_API_KEY is not set. Create a key in the HeyGen dashboard '
             '(Settings -> API) and export it; do not write it into any file.')
    return key


def api_get(path, params=None):
    response = requests.get(f'{API_BASE}{path}', params=params,
                            headers={'X-Api-Key': api_key(),
                                     'Accept': 'application/json'},
                            timeout=60)
    response.raise_for_status()
    return response.json()


def api_post(path, body):
    response = requests.post(f'{API_BASE}{path}', json=body,
                             headers={'X-Api-Key': api_key(),
                                      'Content-Type': 'application/json'},
                             timeout=60)
    response.raise_for_status()
    return response.json()


def load_manifest():
    with open(MANIFEST_PATH, encoding='utf-8') as handle:
        return json.load(handle)


def list_voices():
    voices = api_get('/v2/voices').get('data', {}).get('voices', [])
    for voice in voices:
        print(f"{voice.get('voice_id')}  {voice.get('language'):<14} "
              f"{voice.get('gender', '?'):<8} {voice.get('name')}")
    print(f'{len(voices)} voices')


def pick_voice_id(manifest, lang, overrides):
    if overrides.get(lang):
        return overrides[lang]
    configured = manifest['voices'][lang].get('voice_id')
    if configured:
        return configured
    wanted = manifest['voices'][lang]['auto_pick_language'].lower()
    voices = api_get('/v2/voices').get('data', {}).get('voices', [])
    for voice in voices:
        if wanted in (voice.get('language') or '').lower():
            print(f"note: auto-picked {lang} voice "
                  f"{voice['voice_id']} ({voice.get('name')}); set voices.{lang}."
                  f"voice_id in manifest.json to pin the Huong AI cloned voice.")
            return voice['voice_id']
    fail(f'no HeyGen voice found for language "{wanted}"; pass --voice-{lang}')


def pick_avatar_id(explicit):
    if explicit:
        return explicit
    avatars = api_get('/v2/avatars').get('data', {}).get('avatars', [])
    if not avatars:
        fail('no avatars available on this HeyGen account; pass --avatar-id')
    return avatars[0]['avatar_id']


def submit_video(text, voice_id, avatar_id, speed):
    body = {
        'video_inputs': [{
            'character': {'type': 'avatar', 'avatar_id': avatar_id,
                          'avatar_style': 'normal'},
            'voice': {'type': 'text', 'input_text': text,
                      'voice_id': voice_id, 'speed': speed},
        }],
        'dimension': {'width': 1280, 'height': 720},
    }
    data = api_post('/v2/video/generate', body).get('data') or {}
    video_id = data.get('video_id')
    if not video_id:
        fail(f'HeyGen did not return a video_id: {data}')
    return video_id


def wait_for_video(video_id):
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    while time.time() < deadline:
        data = api_get('/v1/video_status.get',
                       params={'video_id': video_id}).get('data') or {}
        status = data.get('status')
        if status == 'completed':
            return data['video_url']
        if status == 'failed':
            fail(f'HeyGen render failed for {video_id}: {data.get("error")}')
        time.sleep(POLL_INTERVAL_SECONDS)
    fail(f'timed out waiting for HeyGen video {video_id}')


def extract_mp3(video_path, mp3_path, sample_rate, loudnorm):
    subprocess.run(
        ['ffmpeg', '-y', '-loglevel', 'error', '-i', video_path, '-vn',
         '-af', f'loudnorm={loudnorm}', '-ar', str(sample_rate),
         '-codec:a', 'libmp3lame', '-q:a', '2', mp3_path],
        check=True)


def asset_text(asset):
    if 'text' in asset:
        return asset['text']
    text_path = os.path.join(REPO_ROOT, asset['text_file'])
    if not os.path.exists(text_path):
        print(f"skip {asset['id']}: {asset['text_file']} not found "
              f"({asset.get('note', 'provide the text file first')})")
        return None
    with open(text_path, encoding='utf-8') as handle:
        text = handle.read().strip()
    return text or None


def generate_asset(asset, manifest, voice_id, avatar_id, args):
    text = asset_text(asset)
    if text is None:
        return False
    outputs = [os.path.join(REPO_ROOT, path) for path in asset['outputs']]
    if asset['group'] == 'song' and not args.overwrite_song:
        outputs = [p for p in outputs
                   if os.path.basename(p) != 'maida_song.mp3']
    if args.dry_run:
        print(f"would generate {asset['id']} [{asset['lang']}] -> "
              f"{', '.join(asset['outputs'])}")
        print(f'  script: {text[:110]}{"..." if len(text) > 110 else ""}')
        return True

    defaults = manifest['defaults']
    print(f"generating {asset['id']} [{asset['lang']}] ...")
    video_id = submit_video(text, voice_id, avatar_id, defaults['speed'])
    video_url = wait_for_video(video_id)
    with tempfile.TemporaryDirectory() as workdir:
        video_path = os.path.join(workdir, 'render.mp4')
        urllib.request.urlretrieve(video_url, video_path)
        mp3_path = os.path.join(workdir, 'audio.mp3')
        extract_mp3(video_path, mp3_path,
                    defaults['sample_rate_hz'], defaults['loudnorm'])
        for output in outputs:
            os.makedirs(os.path.dirname(output), exist_ok=True)
            shutil.copyfile(mp3_path, output)
            print(f'  wrote {os.path.relpath(output, REPO_ROOT)}')
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Generate all M-AIDA audio via the HeyGen API.')
    parser.add_argument('--list-voices', action='store_true',
                        help='list HeyGen voices and exit')
    parser.add_argument('--group', choices=['tour', 'atlas', 'song'],
                        help='only this asset group')
    parser.add_argument('--lang', choices=['en', 'vi'],
                        help='only this language')
    parser.add_argument('--only', help='comma-separated asset ids')
    parser.add_argument('--voice-en', help='override English voice_id')
    parser.add_argument('--voice-vi', help='override Vietnamese voice_id')
    parser.add_argument('--avatar-id',
                        help='HeyGen avatar used for rendering (audio is '
                             'extracted, so any avatar works)')
    parser.add_argument('--overwrite-song', action='store_true',
                        help='allow the song entry to overwrite '
                             'assets/maida_song.mp3 if listed as an output')
    parser.add_argument('--dry-run', action='store_true',
                        help='print what would be generated, no API calls')
    args = parser.parse_args()

    manifest = load_manifest()

    if args.list_voices:
        if requests is None:
            fail('the requests package is required: pip install requests')
        list_voices()
        return

    assets = manifest['assets']
    if args.group:
        assets = [a for a in assets if a['group'] == args.group]
    if args.lang:
        assets = [a for a in assets if a['lang'] == args.lang]
    if args.only:
        wanted = {token.strip() for token in args.only.split(',')}
        unknown = wanted - {a['id'] for a in manifest['assets']}
        if unknown:
            fail(f'unknown asset ids: {", ".join(sorted(unknown))}')
        assets = [a for a in assets if a['id'] in wanted]
    if not assets:
        fail('no assets matched the given filters')

    if not args.dry_run:
        if requests is None:
            fail('the requests package is required: pip install requests')
        if shutil.which('ffmpeg') is None:
            fail('ffmpeg is required on PATH to extract mp3 audio')

    overrides = {'en': args.voice_en, 'vi': args.voice_vi}
    voice_ids, avatar_id = {}, None
    if not args.dry_run:
        for lang in sorted({a['lang'] for a in assets}):
            voice_ids[lang] = pick_voice_id(manifest, lang, overrides)
        avatar_id = pick_avatar_id(args.avatar_id)

    done = sum(
        1 for asset in assets
        if generate_asset(asset, manifest, voice_ids.get(asset['lang']),
                          avatar_id, args))
    print(f'{done}/{len(assets)} assets processed')


if __name__ == '__main__':
    main()
