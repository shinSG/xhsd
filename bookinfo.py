#!/usr/bin/env python
# coding: utf-8

import datetime
import re
import string
import requests
import codecs
import csv
import socket
import argparse
from bs4 import BeautifulSoup
import xlrd

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
        plu_title = ''
        book_tilte = ''
        isbn = ''
        if len(book_data) == 1:
            if re.search(r'[0-9\-]', book_data[0]):
                isbn = book_data[0].strip().decode('utf8')
            else:
                book_tilte = book_data[0].strip().decode('utf8')
            plu_title = book_data[0].strip().decode('utf8')
        elif len(book_data) > 1:
            chn_punctuation = u'_·！？｡＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏.'
            book_tilte = book_data[0].strip().decode('utf8')
            plu_title = re.sub(ur'[%s%s]+' % (chn_punctuation, string.punctuation), ' ', book_data[0].decode('utf8'))
            print book_tilte
            isbn = book_data[1].strip().decode('utf8')
        res = False
        count = 0
        row_data = [book_tilte, isbn]
        book_info = {
            'store': '',
            'sale': ''
        }
        while not res and count < 2:
            data = {
                'plu_title': plu_title,
                'plu_key': plu_key,
                'B1': u'图书搜索'
            }
            resp = s.post(search_url, data=data)
            if resp.status_code == 200:
                count += 1
                html_doc = resp.content
                soup = BeautifulSoup(html_doc, 'html.parser')
                hrefs = soup.find_all('a')
                book_hrefs = filter(lambda x: x['href'].startswith('views.asp?plucode'), hrefs)
                if len(book_hrefs) == 0:
                    if len(book_data) == 1:
                        break
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
                    if not book_tilte:
                        print book_hrefs[0].text
                        row_data[0] = book_hrefs[0].text
                book_info = get_book_info(bhref)
                res = True
        try:
            dict_data = {
                u'书名': row_data[0],
                u'ISBN': row_data[1],
                u'库存信息': book_info.get('store'),
            }
            sale_info = book_info.get('sale').split(')')
            for si in sale_info:
                kv = si.split(':')
                if len(kv) > 1:
                    dict_data.update(
                        {
                            kv[0].strip(): re.sub(r'[()（）]+', '', kv[1])
                        }
                    )
            row_data.extend(book_info.values())
            file_writer.writerow({k.encode('utf8'): v.encode('utf8') for k, v in dict_data.iteritems()})
        except:
            print row_data
            import traceback;traceback.print_exc()


def get_csv_writer(wf):
    wf.write(codecs.BOM_UTF8)
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month
    title = [u'书名', u'ISBN', u'库存信息', ]
    month = int(current_month) + 1
    for i in xrange(0, 12):
        month -= 1
        if month < 1:
            month = 12
            current_year = current_year - 1
        title.append(unicode(str(current_year) + '-' + (str(month) if month > 9 else '0' + str(month))))
    title = [item.encode('utf-8') for item in title]
    writer = csv.DictWriter(wf, title, restval='')
    writer.writeheader()
    return writer


def process_csv(rfile, wfile):
    with open(rfile) as rf, open(wfile, 'w') as wf:
        reader = csv.reader(rf)
        writer = get_csv_writer(wf)
        for line in reader:
            get_book_by_isbn(line, writer)


def process_excel(rfile, wfile):
    book = xlrd.open_workbook(rfile)
    sh = book.sheet_by_index(0)
    with open(wfile, 'w') as wf:
        writer = get_csv_writer(wf)
        for rx in range(sh.nrows):
            get_book_by_isbn(sh.row_values(rx), writer)


def run(rfile):
    if not rfile:
        return
    wfile = 'result-' + rfile.split('.')[0] + '-' + datetime.date.today().strftime('%Y-%m-%d') + '.csv'
    if rfile.endswith('.csv'):
        process_csv(rfile, wfile)
    elif rfile.endswith('.xls') or rfile.endswith('.xlsx'):
        process_excel(rfile, wfile)
    else:
        print u'文件类型错误，仅支持.csv .xls .xlsx文件'




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, help='file name')
    args = parser.parse_args()
    src_file = args.file
    if src_file:
        run(src_file)
    else:
        print u'请输入文件名，例如: python bookinfo.py --file example.csv'