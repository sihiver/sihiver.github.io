#!/usr/bin/env python3
"""Launch an HLS radio stream in VLC with the right HTTP headers.

This is handy for streams that require a specific User-Agent and/or Referer.

Examples:
  python3 radio/stream_vlc.py
  python3 radio/stream_vlc.py --vlc vlc --verbose
  python3 radio/stream_vlc.py --print-m3u

Notes:
- VLC supports passing headers via CLI options like --http-user-agent and --http-referrer.
- If your VLC build doesn't honor these options for HLS, use the generated M3U entry
  (see --print-m3u) and open it in VLC.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class StreamConfig:
    name: str
    url: str
    user_agent: str
    referer: str


DEFAULT_STREAM = StreamConfig(
    name="GEN 98.7 FM (Wowza/HLS)",
    # Based on the captured request: Host wz.mari.co.id:1936 + path /web_genfm/genfm/playlist.m3u8
    url="http://wz.mari.co.id:1936/web_genfm/genfm/playlist.m3u8",
    user_agent=(
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    ),
    referer="https://gen987fm.com/",
)


def _find_vlc(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    return shutil.which("vlc") or shutil.which("cvlc")


def build_vlc_command(
    vlc: str,
    stream: StreamConfig,
    *,
    extra_args: list[str],
    verbose: bool,
) -> list[str]:
    cmd = [vlc]

    # Keep the UI when using vlc; for cvlc it's fine too.
    if verbose:
        cmd += ["-vvv"]

    # Set HTTP headers/options.
    cmd += [
        f"--http-user-agent={stream.user_agent}",
        f"--http-referrer={stream.referer}",
    ]

    # Some VLC builds need HLS demux hints; harmless otherwise.
    cmd += ["--demux=hls"]

    cmd += extra_args
    cmd += [stream.url]
    return cmd


def print_m3u_entry(stream: StreamConfig) -> None:
    # VLC-specific per-item options inside M3U
    print("#EXTINF:-1," + stream.name)
    print("#EXTVLCOPT:http-user-agent=" + stream.user_agent)
    print("#EXTVLCOPT:http-referrer=" + stream.referer)
    print(stream.url)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Launch a radio stream in VLC with User-Agent/Referer headers.",
    )
    p.add_argument(
        "--vlc",
        default=None,
        help="Path to VLC binary (default: auto-detect vlc/cvlc in PATH).",
    )
    p.add_argument(
        "--url",
        default=DEFAULT_STREAM.url,
        help="Stream URL (default: GENFM playlist.m3u8).",
    )
    p.add_argument(
        "--user-agent",
        default=DEFAULT_STREAM.user_agent,
        help="HTTP User-Agent header value.",
    )
    p.add_argument(
        "--referer",
        default=DEFAULT_STREAM.referer,
        help="HTTP Referer header value.",
    )
    p.add_argument(
        "--name",
        default=DEFAULT_STREAM.name,
        help="Display name used for --print-m3u.",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose VLC logs (-vvv).",
    )
    p.add_argument(
        "--print-m3u",
        action="store_true",
        help="Print an M3U snippet for VLC (instead of launching VLC).",
    )
    p.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Extra args passed to VLC after a '--'. Example: -- --no-video",
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    stream = StreamConfig(
        name=args.name,
        url=args.url,
        user_agent=args.user_agent,
        referer=args.referer,
    )

    if args.print_m3u:
        print_m3u_entry(stream)
        return 0

    vlc = _find_vlc(args.vlc)
    if not vlc:
        print(
            "VLC tidak ditemukan. Install VLC atau beri path via --vlc /path/ke/vlc",
            file=sys.stderr,
        )
        return 2

    extra_args = args.extra_args
    if extra_args and extra_args[0] == "--":
        extra_args = extra_args[1:]

    cmd = build_vlc_command(vlc, stream, extra_args=extra_args, verbose=args.verbose)

    # Show the command for transparency/debugging.
    print("Running:")
    print("  " + " ".join(shlex.quote(c) for c in cmd))

    try:
        # Use exec-style replacement where possible.
        if os.name == "posix":
            os.execvp(cmd[0], cmd)
        subprocess.run(cmd, check=True)
        return 0
    except FileNotFoundError:
        print("VLC binary tidak ditemukan: " + str(vlc), file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        return exc.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
