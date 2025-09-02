#!/usr/bin/env python3
import argparse
import os
import random
import shlex
import subprocess
import sys
import time
from pathlib import Path


def read_proxy_list(proxy_file_path: str) -> list[str]:
    proxies: list[str] = []
    with open(proxy_file_path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            proxies.append(raw)
    if not proxies:
        raise ValueError("Proxy list is empty after filtering comments/blank lines")
    return proxies


def choose_proxy(proxies: list[str], strategy: str, last_index: int | None) -> tuple[str, int]:
    if strategy == "random":
        idx = random.randrange(len(proxies))
        return proxies[idx], idx
    # round-robin
    if last_index is None:
        idx = 0
    else:
        idx = (last_index + 1) % len(proxies)
    return proxies[idx], idx


def run_megadl(url: str, output_path: str | None, proxy: str, username: str | None, password: str | None, extra_args: list[str], timeout: int | None) -> int:
    cmd: list[str] = ["/usr/bin/megadl", "--proxy", proxy]
    if output_path:
        cmd.extend(["--path", output_path])
    # Keep resume enabled by default (do not pass --disable-resume)
    if username:
        cmd.extend(["--username", username])
    if password:
        cmd.extend(["--password", password])
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(url)

    try:
        proc = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr, timeout=timeout)
        return proc.returncode
    except subprocess.TimeoutExpired:
        return 124  # common timeout code


def parse_extra_args(unknown: list[str]) -> list[str]:
    # Allow passing through additional megadl args after "--"
    return unknown


def main() -> int:
    parser = argparse.ArgumentParser(description="MEGA.nz downloader with rotating proxies using megadl")
    parser.add_argument("url", help="MEGA.nz file/folder export URL")
    parser.add_argument("--proxies", required=True, help="Path to file containing proxies, one per line. Formats typically: http://host:port, socks5://host:port, http://user:pass@host:port")
    parser.add_argument("--strategy", choices=["round-robin", "random"], default="round-robin", help="Proxy rotation strategy")
    parser.add_argument("--retries", type=int, default=8, help="Total attempts across rotating proxies")
    parser.add_argument("--retry-wait", type=float, default=5.0, help="Seconds to wait between attempts")
    parser.add_argument("--output", help="Destination path (directory or filename) for megadl --path")
    parser.add_argument("--username", help="MEGA account email (optional, only if needed)")
    parser.add_argument("--password", help="MEGA account password (optional, only if needed)")
    parser.add_argument("--timeout", type=int, default=None, help="Per-attempt timeout in seconds (optional)")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle proxies once at start")
    parser.add_argument("--log-proxy", action="store_true", help="Print which proxy is used each attempt")
    parser.add_argument("--", dest="double_dash", nargs=argparse.REMAINDER, help="Pass-through extra arguments to megadl after --")

    args, unknown = parser.parse_known_args()
    extra_args = []
    if args.double_dash:
        extra_args = parse_extra_args(args.double_dash)
    elif unknown:
        # If user didn't separate by --, still pass unknowns through
        extra_args = parse_extra_args(unknown)

    proxies = read_proxy_list(args.proxies)
    if args.shuffle:
        random.shuffle(proxies)

    # Ensure output directory exists if a directory path was provided
    if args.output:
        out_path = Path(args.output)
        if out_path.exists() and out_path.is_dir():
            out_path.mkdir(parents=True, exist_ok=True)
        elif not out_path.exists():
            # If path endswith slash or looks like a directory, ensure parent exists
            try:
                out_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

    attempt = 0
    last_index: int | None = None
    while attempt < max(1, args.retries):
        proxy, last_index = choose_proxy(proxies, args.strategy, last_index)
        if args.log_proxy:
            print(f"Attempt {attempt + 1}/{args.retries} using proxy: {proxy}")

        code = run_megadl(
            url=args.url,
            output_path=args.output,
            proxy=proxy,
            username=args.username,
            password=args.password,
            extra_args=extra_args,
            timeout=args.timeout,
        )

        if code == 0:
            return 0

        # For transient failures, rotate and retry
        attempt += 1
        if attempt < args.retries:
            time.sleep(args.retry_wait)

    return code if 'code' in locals() else 1


if __name__ == "__main__":
    sys.exit(main())

