#!/usr/bin/env python
# coding: utf-8

import re
import string
import requests
import codecs
import csv
import socket
import argparse
from bs4 import BeautifulSoup

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
    if not href:
        return {'store': '', 'sale': ''}
    resp = requests.get(base_book_url + href)
    in_store = []
    sale_info = ''
    if resp.status_code == 200:
        book_doc = resp.content
        soup = BeautifulSoup(book_doc, 'html.parser')
        tds = soup.find_all('td')
        in_store_td = filter(lambda x: x.get('onmouseover') == "style.background='#f6bf1c'", tds)
        for store in in_store_td:
            store_name = store.contents[0].strip()
            if not store_name:
                store_name = store.find(text=re.compile(ur'^.*[店厦城].*$'))
            store_quantity = store.find('b').string.strip()
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
    with requests.session() as s:
        plu_key = get_first_plu_key()
        chn_punctuation = u'_·！？｡＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏.'
        book_tilte = book_data[0].strip().decode('utf8')
        plu_title = re.sub(ur'[%s%s]+' % (chn_punctuation, string.punctuation), ' ', book_data[0].decode('utf8'))
        print book_tilte
        isbn = book_data[1].strip().decode('utf8')
        res = False
        count = 0
        while not res and count < 2:
            data = {
                'plu_title': plu_title,
                'plu_key': plu_key,
                'B1': u'图书搜索'
            }
            resp = s.post(search_url, data=data)
            row_data = [book_tilte, isbn]
            if resp.status_code == 200:
                count += 1
                html_doc = resp.content
                soup = BeautifulSoup(html_doc, 'html.parser')
                hrefs = soup.find_all('a')
                book_hrefs = filter(lambda x: x['href'].startswith('views.asp?plucode'), hrefs)
                if len(book_hrefs) == 0:
                    plu_title = isbn
                    if count != 2:
                        continue
                bhref = ''
                if len(book_hrefs) > 1:
                    for item in book_hrefs:
                        if item.text.strip() == book_tilte:
                            bhref = item.get('href')
                if len(book_hrefs) == 1:
                    bhref = book_hrefs[0].get('href')
                book_info = get_book_info(bhref)
                row_data.extend(book_info.values())
                try:
                    file_writer.writerow([item.encode('utf8') for item in row_data])
                    res = True
                except:
                    print row_data
                    import traceback;traceback.print_exc()


def run(rfile):
    if not rfile:
        return
    wfile = 'result-' + rfile
    with open(rfile) as rf, open(wfile, 'w') as wf:
        wf.write(codecs.BOM_UTF8)
        reader = csv.reader(rf)
        writer = csv.writer(wf)
        for line in reader:
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