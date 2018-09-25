#!/usr/bin/env python
# coding: utf-8

import re
import requests
from bs4 import BeautifulSoup
import time
import codecs
import csv
from threading import Thread, RLock
import socket
import argparse
socket.setdefaulttimeout(10.0)

search_url = 'http://pub.xhsd.com.cn/books/searchfull.asp'
index_url = 'http://pub.xhsd.com.cn/books/index.asp'
base_book_url = 'http://pub.xhsd.com.cn/books/'


def get_plu_key(page):
    soup = BeautifulSoup(page, 'html.parser')
    inputs = soup.find_all('input')
    plu_key = filter(lambda x: x['name'] == 'plu_key', inputs)
    return plu_key[0]['value']


def get_first_plu_key():
    resp = requests.get(index_url)
    if resp.status_code == 200:
        html_doc = resp.content
        return get_plu_key(html_doc)


def get_book_info(href):
    resp = requests.get(base_book_url + href)
    in_store = []
    sale_info = ''
    if resp.status_code == 200:
        book_doc = resp.content
        soup = BeautifulSoup(book_doc, 'html.parser')
        tds = soup.find_all('td')
        in_store_td = filter(lambda x: x.get('onmouseover') == "style.background='#f6bf1c'", tds)
        for store in in_store_td:
            store_name = store.contents[0]
            store_quantity = store.find('b').string
            in_store.append(store_name + ':' + store_quantity)
        sale_soup = soup.find(text=re.compile(u'查询零售信息'))
        sale_table = None
        for sibling in sale_soup.next_siblings:
            if sibling.name == 'table':
                sale_table = sibling
                break
        sale_status = sale_table.find_all('tr')[1].find_all('td')[0]
        for ss in sale_status:
            if not ss.name:
                sale = ss.strip().replace('&nbsp;', '').replace(u'\uff1a', u':')
                conn_str = ' '
                sale_info += conn_str + sale
    return {'store': ','.join(in_store), 'sale': sale_info}


def get_book_by_isbn(book_data, file_writer):
    import ipdb;ipdb.set_trace()
    print book_data, type(book_data)
    with requests.session() as s:
        plu_key = get_first_plu_key()
        # plu_title = book_data.get('isbn')
        plu_title = book_data[0]
        data = {
            'plu_title': plu_title,
            'plu_key': plu_key,
            'B1': u'图书搜索'
        }
        resp = s.post(search_url, data=data)
        if resp.status_code == 200:
            html_doc = resp.content
            soup = BeautifulSoup(html_doc, 'html.parser')
            hrefs = soup.find_all('a')
            book_href = filter(lambda x: x['href'].startswith('views.asp?plucode'), hrefs)
            book_info = get_book_info(book_href[0]['href'])
            book_data.extend(book_info.values())
            file_writer.writerow(book_data)


def run(rfile):
    if not rfile:
        return
    wfile = 'result-' + rfile
    th_pool = []
    with open(rfile) as rf, open(wfile, 'a+') as wf:
        wf.write(codecs.BOM_UTF8)
        # reader = csv.DictReader(rf)
        reader = csv.reader(rf)
        count = 0
        writer = csv.writer(wf)
        for line in reader:
            # count += 1
            # if count % 5 == 0:
            #     for t in th_pool:
            #         t.join()
            #     count = 0
            #     time.sleep(1)
            # th = Thread(target=get_book_by_isbn, args=(line, writer))
            # th.start()
            # th_pool.append(th)
            get_book_by_isbn(line, writer)


if __name__ == '__main__':
    # get_book_by_isbn('978-7-5596-0240-4')
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, help='file name')
    args = parser.parse_args()
    src_file = args.file
    if src_file:
        run(src_file)
    else:
        print u'请输入文件名，例如: python bookinfo.py --file example.csv'