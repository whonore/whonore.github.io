#!/usr/bin/env python3
# pylint: disable
# flake8: noqa
# type: ignore
import argparse
import contextlib
import os
import socket
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer, test
from pathlib import Path
from threading import Thread
from typing import Any

from pathspec import PathSpec
from watchfiles import Change, DefaultFilter, run_process

DIR = Path(__file__).parent
ROOT = DIR.parent

WATCH = ["index.html", "src/", "assets/"]


class GitIgnoreFilter(DefaultFilter):
    def __init__(self, gitignore: Path) -> None:
        super().__init__()
        with open(gitignore, "r", encoding="utf-8") as f:
            self.gitignore = PathSpec.from_lines("gitwildmatch", f)
            print(self.gitignore)

    def __call__(self, change: Change, path: str) -> bool:
        print(change, path)
        return super().__call__(change, path) and (
            not self.gitignore.match_file(Path(path).resolve().relative_to(ROOT))
        )


class CacheBusterHandler(SimpleHTTPRequestHandler):
    def send_head(self) -> Any:
        del self.headers["If-Modified-Since"]
        return super().send_head()

    def end_headers(self) -> None:
        # See https://stackoverflow.com/questions/9884513/avoid-caching-of-the-http-responses
        self.send_header("Expires", "Thu, 01 Jan 1970 00:00:01 GMT")
        self.send_header("Last-Modified", self.date_time_string())
        self.send_header(
            "Cache-control",
            "max-age=0, no-cache, must-revalidate, proxy-revalidate",
        )
        super().end_headers()


# Copied from
# https://github.com/python/cpython/blob/9a95fa9267590c6cc66f215cd9808905fda1ee25/Lib/http/server.py
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-b",
        "--bind",
        metavar="ADDRESS",
        help="bind to this address (default: all interfaces)",
    )
    parser.add_argument(
        "-d",
        "--directory",
        default=os.getcwd(),
        help="serve this directory (default: current directory)",
    )
    parser.add_argument(
        "-p",
        "--production",
        action="store_true",
        help="build the production version (default: %(default)s)",
    )
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="automatically rebuild (default: %(default)s)",
    )
    parser.add_argument(
        "port",
        default=8000,
        type=int,
        nargs="?",
        help="bind to this port (default: %(default)s)",
    )
    args = parser.parse_args()

    class DualStackServer(ThreadingHTTPServer):
        def server_bind(self) -> Any:
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

        def finish_request(self, request: Any, client_address: Any) -> Any:
            self.RequestHandlerClass(
                request,
                client_address,
                self,
                directory=args.directory,
            )

    if args.watch:

        def log_changes(changes: set[tuple[Change, str]]) -> None:
            for change, path in changes:
                msg = (
                    "ADDED"
                    if change == Change.added
                    else "DELETED"
                    if change == Change.deleted
                    else "MODIFIED"
                )
                print(f"{msg}: {path}", file=sys.stderr)

        Thread(
            target=run_process,
            args=WATCH,
            kwargs={
                "target": "make -j" if not args.production else "make install -j",
                "target_type": "command",
                "watch_filter": GitIgnoreFilter(ROOT / ".gitignore"),
                "callback": log_changes,
            },
            daemon=True,
        ).start()

    test(
        HandlerClass=CacheBusterHandler,
        ServerClass=DualStackServer,
        port=args.port,
        bind=args.bind,
        protocol="HTTP/1.1",
    )
