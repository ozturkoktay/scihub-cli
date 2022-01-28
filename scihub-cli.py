#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import random
import argparse
import requests
import time
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import List


ALL_UAS = 'https://gist.githubusercontent.com/ozturkoktay/f1073b3038cab632c16231ef73353d7c/raw' \
          '/cf847b76a142955b1410c8bcef3aabe221a63db1/user-agents.txt'

parser = argparse.ArgumentParser()
parser.add_argument(
    '--doi', help="The DOI number of the paper.", type=str, required=True)
args = parser.parse_args()


def select_random_uas() -> str:
    '''
    Selects a random user agent from the list of user agents.
    '''
    req = requests.get(ALL_UAS)
    if req.status_code == 200:
        urls: List[str] = req.text.split('\n')
        return random.choice(urls).strip()
    return ''


def _request(method, url, params=None, data=None, headers=None, timeout=10, response_callback=None,
             allow_redirects=True, stream=False):
    '''
    Wrapper for requests.get()
    '''
    _retries = 5
    _session = requests.Session()
    headers = {'User-Agent': select_random_uas()}
    for attempt in range(_retries + 1):
        req = _session.prepare_request(requests.Request(
            method, url, params=params, data=data, headers=headers))
        try:
            r = _session.send(
                req, allow_redirects=allow_redirects, timeout=timeout, stream=stream)
        except requests.exceptions.RequestException:
            print('Retrying...' if attempt < _retries else '', 'error')
        else:

            if response_callback is not None:
                success, msg = response_callback(r)
            else:
                success, msg = (True, None)
            if success:
                return r
            else:
                print('Retrying...' if attempt < _retries else '', 'error')
        if attempt < _retries:
            sleep_time = 1.0 * 2 ** attempt
            time.sleep(sleep_time)
    msg = f'{_retries + 1} requests to {req.url} failed, giving up.'
    raise Exception(msg)


def _get(*args, **kwargs) -> requests.Response:
    return _request('GET', *args, **kwargs)


def get_scihub_url():
    '''
    Finds available scihub urls via https://www.sci-hub.pub/
    '''
    res = _get('https://www.sci-hub.pub/')
    soup = BeautifulSoup(res.content, 'html.parser')
    scihub_urls = [link.get('href') for link in soup.select("p.main > a")]
    return random.choice(scihub_urls)


def download_file(url, filename=False):
    '''
    Downloads the file from the url.
    '''
    if not filename:
        local_filename = os.path.join(".", url.split('/')[-1])
    else:
        local_filename = filename
    r = _get(url, stream=True)
    chunk = 1
    chunk_size = 1024
    num_bars = int(r.headers['Content-Length']) // chunk_size
    with open(local_filename, 'wb') as fp:
        for chunk in tqdm(
            r.iter_content(chunk_size=chunk_size), total=num_bars, unit='KB', desc=local_filename, leave=True
        ):
            fp.write(chunk)


def convert_to_url(string: str):
    '''
    Convert the pdf url to a url that can be downloaded.
    '''
    return f"https:{string}" if string.startswith('//') else string


def main():
    '''
    Main function that downloads the pdf file from the doi.
    '''
    req = _get(f"{get_scihub_url()}{args.doi}")
    bs = BeautifulSoup(req.text, 'html.parser')
    if "not found" or "sorry" in req.text.lower():
        print(f"[!] {args.doi} not found! Check the DOI number.")
        exit(1)
    try:
        pdf_url = bs.select("iframe#pdf")[0].get("src")
        converted_pdf_url = convert_to_url(pdf_url)
    except IndexError:
        pdf_url = bs.select("embed#pdf")[0].get("src")
        converted_pdf_url = convert_to_url(pdf_url)

    print(f"[>] {args.doi} found! Downloading...")
    file_name = args.doi.replace('/', '_') + '.pdf'
    download_file(converted_pdf_url, filename=file_name)


if __name__ == "__main__":
    main()
