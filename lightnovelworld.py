#!/usr/bin/env python
# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import time
import random
import hashlib
import os
import sys
import re
import argparse

from reliq import reliq

# from curl_cffi import requests
import requests
from urllib.parse import urljoin
import browser_cookie3


class RequestError(Exception):
    pass


class AlreadyVisitedError(Exception):
    pass


def strtosha256(string):
    if isinstance(string, str):
        string = string.encode()

    return hashlib.sha256(string).hexdigest()


def int_get(obj, name):
    x = obj.get(name)
    if x is None:
        return 0
    return int(x)


def float_get(obj, name):
    x = obj.get(name)
    if x is None:
        return 0
    return float(x)


class Session(requests.Session):
    def __init__(self, browser, **kwargs):
        # super().__init__(impersonate="firefox", timeout=30)
        super().__init__()

        t = kwargs.get("timeout")
        self.timeout = 30 if t is None else t

        t = kwargs.get("user_agent")
        self.user_agent = (
            t
            if t is not None
            else "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0"
        )

        self.headers.update(
            {
                # user agent matters, and has to be the exact same as the browser uses
                "User-Agent": self.user_agent,
            }
        )

        cj = browser()
        self.cookies.update(cj)

        self.retries = int_get(kwargs, "retries")
        self.retry_wait = float_get(kwargs, "retry_wait")
        self.wait = float_get(kwargs, "wait")
        self.wait_random = int_get(kwargs, "wait_random")
        self.visited_c = kwargs.get("visited")
        if self.visited_c is None:
            self.visited_c = False
        self.visited = set()

        self.logger = kwargs.get("logger")

    @staticmethod
    def base(rq, url):
        ref = url
        u = rq.search(r'[0] head; [0] base href=>[1:] | "%(href)v"')
        if u != "":
            u = urljoin(url, u)
            if u != "":
                ref = u
        return ref

    def get_req_try(self, url, retry=False):
        if not retry:
            if self.wait != 0:
                time.sleep(self.wait)
            if self.wait_random != 0:
                time.sleep(random.randint(0, self.wait_random + 1) / 1000)

        if self.logger is not None:
            print(url, file=self.logger)

        return self.get(url, timeout=self.timeout)

    def get_req(self, url):
        if self.visited_c:
            if url in self.visited:
                raise AlreadyVisitedError(url)

            self.visited.add(url)

        tries = self.retries
        retry_wait = self.retry_wait

        instant_end_code = [400, 401, 402, 403, 404, 410, 412, 414, 421, 505]

        i = 0
        while True:
            try:
                resp = self.get_req_try(url, retry=(i != 0))
            except (
                requests.ConnectTimeout,
                requests.ConnectionError,
                requests.ReadTimeout,
                requests.exceptions.ChunkedEncodingError,
                RequestError,
            ):
                resp = None

            if resp is None or not (
                resp.status_code >= 200 and resp.status_code <= 299
            ):
                if resp is not None and resp.status_code in instant_end_code:
                    raise RequestError(
                        "failed completely {} {}".format(resp.status_code, url)
                    )
                if i >= tries:
                    raise RequestError(
                        "failed {} {}".format(
                            "connection" if resp is None else resp.status_code, url
                        )
                    )
                i += 1
                if retry_wait != 0:
                    time.sleep(retry_wait)
            else:
                return resp

    def get_html(self, url, return_cookies=False):
        resp = self.get_req(url)

        rq = reliq(resp.text)
        ref = self.base(rq, url)

        if return_cookies:
            return (rq, ref, resp.cookies.get_dict())
        return (rq, ref)


class lightnovelworld:
    def __init__(self, browser, **kwargs):
        self.ses = Session(
            browser,
            **kwargs,
        )

    def get_chapter(self, url):
        fname = strtosha256(url)
        if os.path.exists(fname):
            return

        rq, ref = self.ses.get_html(url)
        title = rq.search(
            r'h1 itemprop=headline; [0] span .chapter-title | "%Di" trim / sed "s#/#|#g"'
        )

        if len(title) == 0:
            raise Exception("failed getting chapter " + url)

        contents = rq.search(
            r'div #chapter-container; p child@ | "%DT\n\n" / trim "\n"'
        )

        with open(fname, "w") as f:
            f.write(title)
            f.write("\n\n")
            f.write(contents)

    def get_novel_chapters(self, url):
        nexturl = url
        while len(nexturl) != 0:
            rq, ref = self.ses.get_html(nexturl)

            for i in rq.search(r'[0] ul .chapter-list; a title | "%(href)v\n"').split(
                "\n"
            )[:-1]:
                i = urljoin(ref, i)
                self.get_chapter(i)

            nexturl = rq.search(r'[0] li .PagedList-skipToNext; [0] a | "%(href)v"')
            if len(nexturl) == 0:
                break
            nexturl = urljoin(ref, nexturl)

    def get_novel(self, url):
        rq, ref = self.ses.get_html(url)

        title = rq.search(r'[0] h1 .novel-title c@[0] | "%i" / sed "s#/#|#g"')
        if len(title) == 0:
            raise Exception("failed getting novel '$1'")

        try:
            os.mkdir(title)
        except FileExistsError:
            pass
        os.chdir(title)

        ch_url = url
        if ch_url[-1] == "/":
            ch_url = ch_url[:-1]
        ch_url += "/chapters"

        self.get_novel_chapters(ch_url)

        os.chdir("..")

    def get_pages(self, url):
        rq, ref = self.ses.get_html(url)

        nexturl = url
        while len(nexturl) != 0:
            rq, ref = self.ses.get_html(nexturl)

            for i in rq.search(
                r'li .novel-item; a [0] title href | "%(href)v\n"'
            ).split("\n")[:-1]:
                i = urljoin(ref, i)
                self.get_novel(i)

            nexturl = rq.search(r'[0] li .PagedList-skipToNext; [0] a | "%(href)v"')
            if len(nexturl) == 0:
                break
            nexturl = urljoin(ref, nexturl)

    def guess(self, url):
        if re.fullmatch(r"https://www.lightnovelworld.com?/novel/[^/]+/?", url):
            self.get_novel(url)
        elif re.fullmatch(
            r"https://www.lightnovelworld.com?/novel/[^/]+/chapters(\?page=[0-9]+)?",
            url,
        ):
            self.get_novel_chapters(url)
        elif re.fullmatch(r"https://www.lightnovelworld.com?/novel/[^/]+/[^/]+/?", url):
            self.get_chapter(url)
        elif re.fullmatch(
            r"https://www.lightnovelworld.com?/(browse/|ranking-|latest-updates-|searchadv/).*",
            url,
        ):
            self.get_pages(url)
        else:
            raise Exception("could not guess the url - '{}'".format(url))


def valid_directory(directory):
    try:
        return os.chdir(directory)
    except:
        raise argparse.ArgumentTypeError(
            'couldn\'t change directory to "{}"'.format(directory)
        )


def valid_browser(browser):
    match browser:
        case "chromium":
            return browser_cookie3.chromium
        case "firefox":
            return browser_cookie3.firefox
        case "edge":
            return browser_cookie3.edge
        case "lynx":
            return browser_cookie3.lynx
        case "safari":
            return browser_cookie3.safari
        case "operax":
            return browser_cookie3.opera
        case "opera_gx":
            return browser_cookie3.opera_gx
        case "w3m":
            return browser_cookie3.w3m
        case "brave":
            return browser_cookie3.brave
        case "librewolf":
            return browser_cookie3.librewolf
        case _:
            raise argparse.ArgumentTypeError('no such browser "{}"'.format(browser))


def argparser():
    parser = argparse.ArgumentParser(
        description="Crude lightnovelworld.com scraper made in annoyance",
        add_help=False,
    )

    parser.add_argument(
        "urls",
        metavar="URL",
        nargs="*",
        help="url pointing to source, type of content is automatically guessed based on it",
    )

    general = parser.add_argument_group("General")
    general.add_argument(
        "-h",
        "--help",
        action="help",
        help="Show this help message and exit",
    )

    general.add_argument(
        "-d",
        "--directory",
        metavar="DIR",
        type=valid_directory,
        help="Change directory to DIR",
    )

    types = parser.add_argument_group("Types")
    types.add_argument(
        "--chapter",
        action="append",
        metavar="URL",
        type=str,
        help="Treats the following url as chapter",
        default=[],
    )
    types.add_argument(
        "--chapters",
        action="append",
        metavar="URL",
        type=str,
        help="Treats the following url as chapters list",
        default=[],
    )
    types.add_argument(
        "--novel",
        action="append",
        metavar="URL",
        type=str,
        help="Treats the following url as novel",
        default=[],
    )
    types.add_argument(
        "--pages",
        action="append",
        metavar="URL",
        type=str,
        help="Treats the following url as page of novels",
        default=[],
    )

    request_set = parser.add_argument_group("Request settings")
    request_set.add_argument(
        "-w",
        "--wait",
        metavar="SECONDS",
        type=float,
        help="Sets waiting time for each request to SECONDS",
        default=2,
    )
    request_set.add_argument(
        "-W",
        "--wait-random",
        metavar="MILISECONDS",
        type=int,
        help="Sets random waiting time for each request to be at max MILISECONDS",
        default=3000,
    )
    request_set.add_argument(
        "-r",
        "--retries",
        metavar="NUM",
        type=int,
        help="Sets number of retries for failed request to NUM",
        default=3,
    )
    request_set.add_argument(
        "--retry-wait",
        metavar="SECONDS",
        type=float,
        help="Sets interval between each retry",
        default=30,
    )
    request_set.add_argument(
        "-m",
        "--timeout",
        metavar="SECONDS",
        type=float,
        help="Sets request timeout",
        default=30,
    )
    request_set.add_argument(
        "-A",
        "--user-agent",
        metavar="UA",
        type=str,
        help="Sets custom user agent",
    )
    request_set.add_argument(
        "-B",
        "--browser",
        metavar="BROWSER",
        type=valid_browser,
        help="Sets custom user agent",
        default=browser_cookie3.firefox,
    )

    return parser


def main():
    args = argparser().parse_args(sys.argv[1:] if sys.argv[1:] else ["-h"])

    n = lightnovelworld(
        args.browser,
        timeout=args.timeout,
        retries=args.retries,
        retry_wait=args.retry_wait,
        wait=args.wait,
        wait_random=args.wait_random,
        user_agent=args.user_agent,
        logger=sys.stderr,
    )

    for i in args.chapter:
        n.get_chapter(i)
    for i in args.chapters:
        n.get_novel_chapters(i)
    for i in args.novel:
        n.get_novel(i)
    for i in args.pages:
        n.get_pages(i)

    for i in args.urls:
        n.guess(i)


main()
