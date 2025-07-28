"""Download metadata and individual responses
of Dutch government online consultations
"""

from pathlib import Path, PosixPath
import re
import datetime
import time
import requests
import pandas as pd
from nltk import ngrams
import textract
import networkx as nx
from bs4 import BeautifulSoup as bs


BASE = 'https://www.internetconsultatie.nl'
SEP = '\n###\n'
NR_RESP = r'Reacties op consultatie \[([0-9]+)\]'


def get_url(item):
    """Extract href and return as full url"""
    a = item.find('a')
    if not a:
        return None
    return f'{BASE}{a.get("href")}'


# def get_next_link(soup):
#     """Extract link to next page, if exists"""
#     nxt = soup.find('li', class_='next')
#     if nxt:
#         return get_url(nxt)
#     return None


def get_result_urls(soup):
    """Extract links to individual responses"""
    results_div = soup.find('div', class_='result--list')
    results = results_div.find_all('li')
    result_urls = [get_url(li) for li in results]
    return [url for url in result_urls if url]


def extract_kv(row):
    """Try to extract key and value from row"""
    try:
        key = row.find('th').text.strip()
    except AttributeError:
        key = None
    try:
        value = row.find('td').text.strip()
    except AttributeError:
        value = None
    return key, value


def parse_table(table):
    """Convert table to dict"""
    kv = [extract_kv(row) for row in table.find_all('tr')]
    data = {key:value for key, value in kv if key}
    return data


def get_response(url, name, dir_attachments, download_attachments):
    """Download and parse response"""
    resp = requests.get(url)
    html = resp.text
    soup = bs(html, 'lxml')
    table = soup.find('table', class_='table__data-overview')
    response = parse_table(table)
    if not name:
        response.pop('Naam', None)
    response['url'] = url
    response['text'] = SEP.join([
        question.text.strip() for question in soup.find_all('blockquote')
    ])
    if download_attachments:
        response['attachment'] = download_files(soup, dir_attachments)
    return response


def download_files(soup, dir_attachments):
    """Download and save any attachments"""
    download_ids = []
    download_urls = [
        f'{BASE}{a.get("href")}' for a
        in soup.find_all('a', class_='icon--download')
    ]
    for url in download_urls:
        download_id = url.split('/')[-2]
        resp = requests.get(url, stream=True)
        path = dir_attachments / f'{download_id}.pdf'
        with open(path, 'wb') as f:
            f.write(resp.content)
        download_ids.append(download_id)
    return ','.join(download_ids)


def extract_text(df, dir_attachments):
    """Extract text from attachtments"""
    df = df.reset_index(drop=True)
    df['text_attachment'] = None
    for i, attachment_name in enumerate(df.attachment):
        if pd.notna(attachment_name) and attachment_name != '':
            path = dir_attachments / f'{int(attachment_name)}.pdf'
            try:
                text_attachment = textract.process(path).decode('utf8')
            except TypeError:
                text_attachment = None
                print('Failed to open', path.name)
            df.loc[i, 'text_attachment'] = text_attachment
    return df


def get_ngrams(text, text_attachment, n):
    """Extract unique sentences from response"""
    if pd.notna(text_attachment):
        txt = text_attachment
    else:
        txt = text
    if pd.isna(txt) or txt == '':
        return None
    return set(ngrams(txt.split(), n))


def jaccard_similarity(ngrams1, ngrams2):
    """Calculate jaccard similarity"""
    if not ngrams1 or not ngrams2:
        return None
    intersection = float(len(ngrams1.intersection(ngrams2)))
    union = len(ngrams1.union(ngrams2))
    if union == 0:
        return None
    return  intersection / union


def add_components(df, n=5, threshold=0.3, dir_attachments='../data/attachments'):
    """Find clusters of similar docs"""
    df = df.reset_index(drop=True)
    df['component'] = None
    if not isinstance(dir_attachments, PosixPath):
        dir_attachments = Path(dir_attachments)
    if 'text_attachment' not in df.columns:
        df = extract_text(df, dir_attachments)
    n_grams = [
        get_ngrams(text, text_attachment, n)
        for text, text_attachment
        in zip(df.text, df.text_attachment)
    ]
    edges = []
    for i, n_gram1 in enumerate(n_grams):
        for j, n_gram2 in enumerate(n_grams):
            if not j > i:
                continue
            similarity = jaccard_similarity(n_gram1, n_gram2)
            if not similarity:
                continue
            if similarity >= threshold:
                edges.append((i, j))
    G = nx.Graph()
    G.add_edges_from(edges)
    for i, component in enumerate(nx.connected_components(G)):
        for j in component:
            df.loc[j, 'component'] = i
    return df


def download_responses(consultation, name=False, dir_responses='../data',
                       download_attachments=True,
                       dir_attachments='../data/attachments',
                       extract_text_attachment=True, components=True, n=5,
                       threshold=0.3):
    """Download responses to consultation

    :param consultation: name of the consultation, taken from its url
    :param name: if True, the name of respondent will be saved (default False)
    :param dir_responses: directory where responses will be saved
    :param download_attachments: if True, attachments will be downloaded
    :param dir_attachments: directory where attachments will be saved
    :param extract_text_attachment: if True, text will be extracted from
        attachments and stored in a column 'text_attachment'
    :param components: if True, groups of similar responses will be
        identified in a column 'component'
    :param n: n to be used to extract ngrams (if add_components is set)
    :param threshold: threshold value to determine if texts are similar, based
        on jaccard similarity of ngrams (if add_components is set)
    """
    if not isinstance(dir_responses, PosixPath):
        dir_responses = Path(dir_responses)
    if not isinstance(dir_attachments, PosixPath):
        dir_attachments = Path(dir_attachments)
    dir_responses.mkdir(exist_ok=True)
    dir_attachments.mkdir(exist_ok=True)
    filename = f'responses_{consultation}.ods'
    path_responses = dir_responses / filename
    try:
        df = pd.read_excel(path_responses)
        done = list(df.url)
        responses = [dict(row) for _, row in df.iterrows()]
    except FileNotFoundError:
        done = []
        responses = []
    max_page = None
    page = 1
    while True:

        if page % 10 == 0 and responses:
            df = pd.DataFrame(responses)
            df.to_excel(path_responses, index=False)
            print(page, datetime.datetime.now().strftime('%H:%M:%S'))

        url = f'{BASE}/{consultation}/reacties/datum/{page}'
        resp = requests.get(url)
        html = resp.text
        soup_results = bs(html, 'lxml')
        result_urls = get_result_urls(soup_results)
        responses.extend([
            get_response(url, name, dir_attachments, download_attachments)
            for url in result_urls
            if url not in done
        ])
        
        page += 1
        if not max_page:
            pagination = soup_results.find('div', class_='pagination')
            max_page = max([
                int(a.text)
                for a
                in pagination.find_all('a')
                if a.has_attr('href')
            ])
        if page > max_page:
            break

        time.sleep(1)
    df = pd.DataFrame(responses)
    if extract_text_attachment or components:
        print('extracting text', datetime.datetime.now().strftime('%H:%M:%S'))
        df = extract_text(df, dir_attachments)
    if components:
        print('adding components', datetime.datetime.now().strftime('%H:%M:%S'))
        df = add_components(
            df, n=n, threshold=threshold, dir_attachments=dir_attachments
        )
    df.to_excel(path_responses, index=False)
    return df


def parse_consultation(url, save_html, dir_html):
    """Extract metadata"""
    resp = requests.get(url)
    html = resp.text
    if 'De website is tijdelijk niet beschikbaar' in html:
        return {'url': url}
    result_soup = bs(html, 'lxml')
    table = result_soup.find('table', class_='table__data-overview')
    consultation = parse_table(table)
    consultation['title'] = result_soup.find('h1').text.strip()
    nr = None
    try:
        nr_text = result_soup.find('span', class_='reacties__sublabel')
        nr, _ = nr_text.text.split()
    except AttributeError:
        nr_results = re.findall(NR_RESP, html)
        for nr in nr_results:
            break
    consultation['nr_responses'] = nr
    consultation['url'] = url
    if 'mainContentPlaceHolder_consultatierapportDocumentDownloadLink_typeAnchor' in html:
        consultation['report'] = True
    else:
        consultation['report'] = False
    if save_html:
        filename = url.replace(BASE, '').replace('/', '_')
        filename = re.sub(r'^_', '', filename)
        path_html = dir_html / f'{filename}.html'
        path_html.write_text(html)
        consultation['html'] = filename
    time.sleep(0.1)
    return consultation


def download_consultations(path_consultations='../data/consultations.ods',
                           save_html=False, dir_html='../data/html'):
    """Download metadata of past consultations

    :param path_consultations: path where consultation metadata will be stored
    """

    nxt = f'{BASE}/geslotenconsultaties'
    try:
        df = pd.read_excel(path_consultations)
        done = list(df.url)
        consultations = [dict(row) for _, row in df.iterrows()]
    except FileNotFoundError:
        done = []
        consultations = []
    if save_html and not isinstance(dir_html, PosixPath):
        dir_html = Path(dir_html)
    if save_html:
        dir_html.mkdir(exist_ok=True)

    i = 0
    while nxt:
        if i % 10 == 0 and consultations:
            df = pd.DataFrame(consultations)
            with pd.ExcelWriter(path_consultations, options={'strings_to_urls': False}) as writer:
                df.to_excel(writer, index=False)
            df.to_excel(path_consultations, index=False)
            print(i, datetime.datetime.now().strftime('%H:%M:%S'))
        resp = requests.get(nxt)
        html = resp.text
        soup = bs(html, 'lxml')
        result_urls = get_result_urls(soup)
        consultations.extend([
            parse_consultation(url, save_html, dir_html) for url in result_urls
            if url not in done
        ])
        nxt = get_next_link(soup)
        i += 1
        time.sleep(0.5)
    df = pd.DataFrame(consultations)
    with pd.ExcelWriter(path_consultations, options={'strings_to_urls': False}) as writer:
        df.to_excel(writer, index=False)
    return df
