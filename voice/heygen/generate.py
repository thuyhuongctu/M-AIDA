#!/usr/bin/env python3
"""Regenerate every M-AIDA audio asset with HeyGen.

The site ships three families of audio, all listed in manifest.json:

  * guided-tour narration      voice/stop1-6.mp3 and voice/vi/stop1-6.mp3
  * atlas country notes        voice/atlas/*.mp3 (English + Vietnamese)
  * theme-song vocal track     assets/heygen/maida_song_vocal.mp3

Every file is also mirrored into docs/ for GitHub Pages; the manifest lists
both output paths so one run keeps the mirrors in sync.

Two engines are supported:

  cli (preferred)  The official HeyGen CLI v3 text-to-speech:
                     heygen voice speech create --text ... --voice-id ...
                   Direct audio output, no video render needed. Install:
                     curl -fsSL https://static.heygen.ai/cli/install.sh | bash
                   Auth: HEYGEN_API_KEY env var, or `heygen auth login`.
                   This is the path recommended by HeyGen's official skills
                   package (github.com/heygen-com/skills), which deprecates
                   the v1/v2 REST endpoints.

  api (fallback)   Legacy REST v2: renders a minimal avatar video per line
                   via POST /v2/video/generate and extracts the sound track.
                   Deprecated by HeyGen; kept only for accounts where the
                   CLI is unavailable. Requires HEYGEN_API_KEY and ffmpeg.

Either way the raw audio is loudness-normalized (EBU R128) and resampled
with ffmpeg into the final 44.1 kHz mp3.

Usage:
  export HEYGEN_API_KEY=...        # never hardcode or commit the key
  python voice/heygen/generate.py --list-voices
  python voice/heygen/generate.py --dry-run
  python voice/heygen/generate.py                    # everything
  python voice/heygen/generate.py --group tour --lang vi
  python voice/heygen/generate.py --only tour_en_stop1,atlas_vi_vietnam

Requires: python3, ffmpeg on PATH; the HeyGen CLI (engine cli) or the
requests package (engine api).
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
except ImportError:  # only the legacy api engine needs requests
    requests = None

API_BASE = 'https://api.heygen.com'
POLL_INTERVAL_SECONDS = 8
POLL_TIMEOUT_SECONDS = 15 * 60
CLI_TIMEOUT_SECONDS = 10 * 60
LOCALES = {'en': 'en-US', 'vi': 'vi-VN'}
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), 'manifest.json')


def fail(message):
    print(f'error: {message}', file=sys.stderr)
    sys.exit(1)


def load_manifest():
    with open(MANIFEST_PATH, encoding='utf-8') as handle:
        return json.load(handle)


def pick_engine(requested):
    if requested != 'auto':
        return requested
    if shutil.which('heygen'):
        return 'cli'
    print('note: HeyGen CLI not found, falling back to the deprecated REST v2 '
          'engine. Prefer the CLI: '
          'curl -fsSL https://static.heygen.ai/cli/install.sh | bash')
    return 'api'


# ---------------------------------------------------------------- cli engine

def run_cli(argv):
    result = subprocess.run(['heygen'] + argv, capture_output=True, text=True,
                            timeout=CLI_TIMEOUT_SECONDS)
    if result.returncode != 0:
        fail(f"heygen {' '.join(argv[:3])} failed: "
             f'{result.stderr.strip() or result.stdout.strip()}')
    return result.stdout


def cli_json(argv):
    stdout = run_cli(argv)
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        fail(f"could not parse JSON from `heygen {' '.join(argv[:3])}`; "
             f'run it with --help to check the arguments. Output was: '
             f'{stdout[:400]}')


def find_audio_ref(payload):
    """Locate a local file path or audio URL anywhere in a CLI response."""
    stack = [payload]
    url = None
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str):
                    if key in ('path', 'file', 'output_path') and \
                            os.path.exists(value):
                        return ('path', value)
                    if value.startswith('http') and (
                            'audio' in key or value.endswith(
                                ('.mp3', '.wav', '.m4a', '.aac'))):
                        url = url or value
                else:
                    stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)
    return ('url', url) if url else (None, None)


def cli_list_voices():
    for lang in ('en', 'vi'):
        payload = cli_json(['voice', 'list', '--language', lang,
                            '--limit', '50'])
        voices = payload.get('data', payload)
        if isinstance(voices, dict):
            voices = voices.get('voices') or voices.get('items') or []
        for voice in voices:
            print(f"{voice.get('voice_id')}  {lang}  "
                  f"{voice.get('gender', '?'):<8} {voice.get('name')}")


def cli_pick_voice_id(manifest, lang, overrides):
    if overrides.get(lang):
        return overrides[lang]
    configured = manifest['voices'][lang].get('voice_id')
    if configured:
        return configured
    payload = cli_json(['voice', 'list', '--language', lang, '--limit', '5'])
    voices = payload.get('data', payload)
    if isinstance(voices, dict):
        voices = voices.get('voices') or voices.get('items') or []
    if not voices:
        fail(f'no HeyGen voice found for language "{lang}"; pass --voice-{lang}')
    voice = voices[0]
    print(f"note: auto-picked {lang} voice {voice['voice_id']} "
          f"({voice.get('name')}); set voices.{lang}.voice_id in "
          f'manifest.json to pin the Huong AI cloned voice.')
    return voice['voice_id']


def cli_synthesize(text, voice_id, lang, workdir):
    payload = cli_json(['voice', 'speech', 'create', '--text', text,
                        '--voice-id', voice_id, '--input-type', 'text',
                        '--language', lang, '--locale', LOCALES[lang]])
    kind, ref = find_audio_ref(payload)
    if kind == 'path':
        return ref
    if kind == 'url':
        raw_path = os.path.join(workdir, 'speech-download')
        urllib.request.urlretrieve(ref, raw_path)
        return raw_path
    fail(f'no audio path or URL in `heygen voice speech create` response: '
         f'{json.dumps(payload)[:400]}')


# ------------------------------------------------- legacy api engine (v2)

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


def api_list_voices():
    voices = api_get('/v2/voices').get('data', {}).get('voices', [])
    for voice in voices:
        print(f"{voice.get('voice_id')}  {voice.get('language'):<14} "
              f"{voice.get('gender', '?'):<8} {voice.get('name')}")
    print(f'{len(voices)} voices')


def api_pick_voice_id(manifest, lang, overrides):
    if overrides.get(lang):
        return overrides[lang]
    configured = manifest['voices'][lang].get('voice_id')
    if configured:
        return configured
    wanted = manifest['voices'][lang]['auto_pick_language'].lower()
    voices = api_get('/v2/voices').get('data', {}).get('voices', [])
    for voice in voices:
        if wanted in (voice.get('language') or '').lower():
            print(f"note: auto-picked {lang} voice {voice['voice_id']} "
                  f"({voice.get('name')}); set voices.{lang}.voice_id in "
                  f'manifest.json to pin the Huong AI cloned voice.')
            return voice['voice_id']
    fail(f'no HeyGen voice found for language "{wanted}"; pass --voice-{lang}')


def api_pick_avatar_id(explicit):
    if explicit:
        return explicit
    avatars = api_get('/v2/avatars').get('data', {}).get('avatars', [])
    if not avatars:
        fail('no avatars available on this HeyGen account; pass --avatar-id')
    return avatars[0]['avatar_id']


def api_synthesize(text, voice_id, avatar_id, speed, workdir):
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
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    while time.time() < deadline:
        data = api_get('/v1/video_status.get',
                       params={'video_id': video_id}).get('data') or {}
        status = data.get('status')
        if status == 'completed':
            video_path = os.path.join(workdir, 'render.mp4')
            urllib.request.urlretrieve(data['video_url'], video_path)
            return video_path
        if status == 'failed':
            fail(f'HeyGen render failed for {video_id}: {data.get("error")}')
        time.sleep(POLL_INTERVAL_SECONDS)
    fail(f'timed out waiting for HeyGen video {video_id}')


# ------------------------------------------------------------------ shared

def to_mp3(raw_path, mp3_path, sample_rate, loudnorm):
    subprocess.run(
        ['ffmpeg', '-y', '-loglevel', 'error', '-i', raw_path, '-vn',
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


def generate_asset(asset, manifest, engine, voice_id, avatar_id, args):
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
    print(f"generating {asset['id']} [{asset['lang']}] via {engine} ...")
    with tempfile.TemporaryDirectory() as workdir:
        if engine == 'cli':
            raw_path = cli_synthesize(text, voice_id, asset['lang'], workdir)
        else:
            raw_path = api_synthesize(text, voice_id, avatar_id,
                                      defaults['speed'], workdir)
        mp3_path = os.path.join(workdir, 'audio.mp3')
        to_mp3(raw_path, mp3_path,
               defaults['sample_rate_hz'], defaults['loudnorm'])
        for output in outputs:
            os.makedirs(os.path.dirname(output), exist_ok=True)
            shutil.copyfile(mp3_path, output)
            print(f'  wrote {os.path.relpath(output, REPO_ROOT)}')
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Generate all M-AIDA audio via HeyGen.')
    parser.add_argument('--engine', choices=['auto', 'cli', 'api'],
                        default='auto',
                        help='cli = official HeyGen CLI v3 TTS (preferred); '
                             'api = deprecated REST v2 video render; '
                             'auto picks cli when installed (default)')
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
                        help='api engine only: avatar used for the video '
                             'render the audio is extracted from')
    parser.add_argument('--overwrite-song', action='store_true',
                        help='allow the song entry to overwrite '
                             'assets/maida_song.mp3 if listed as an output')
    parser.add_argument('--dry-run', action='store_true',
                        help='print what would be generated, no API calls')
    args = parser.parse_args()

    manifest = load_manifest()
    engine = pick_engine(args.engine)

    if engine == 'api' and not args.dry_run and requests is None:
        fail('the requests package is required for the api engine: '
             'pip install requests')
    if engine == 'cli' and not args.dry_run and shutil.which('heygen') is None:
        fail('the heygen CLI is not on PATH: '
             'curl -fsSL https://static.heygen.ai/cli/install.sh | bash')

    if args.list_voices:
        cli_list_voices() if engine == 'cli' else api_list_voices()
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

    if not args.dry_run and shutil.which('ffmpeg') is None:
        fail('ffmpeg is required on PATH to produce normalized mp3 audio')

    overrides = {'en': args.voice_en, 'vi': args.voice_vi}
    voice_ids, avatar_id = {}, None
    if not args.dry_run:
        pick = cli_pick_voice_id if engine == 'cli' else api_pick_voice_id
        for lang in sorted({a['lang'] for a in assets}):
            voice_ids[lang] = pick(manifest, lang, overrides)
        if engine == 'api':
            avatar_id = api_pick_avatar_id(args.avatar_id)

    done = sum(
        1 for asset in assets
        if generate_asset(asset, manifest, engine,
                          voice_ids.get(asset['lang']), avatar_id, args))
    print(f'{done}/{len(assets)} assets processed')


if __name__ == '__main__':
    main()
