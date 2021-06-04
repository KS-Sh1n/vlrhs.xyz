import os
import requests
import sqlite3
import telegram
from bs4 import BeautifulSoup
from datetime import datetime
from re import compile
from selenium import webdriver
from .db import _instance_path
from flask import flash

def tuple_to_sitedata_dict(**kwargs):
    """ (**kwargs) -> dictionary

    Receive value from sitedata table, with a corresponding key.

    if there are multiple values in a single sitedata column, split them with a "," and make it a single list.

    >>> tuple_to_sitedata_dict(a = "1", b = "2, 3", c = "asd")
    {"a" : 1, "b" : ["2", "3"], "c" : "asd"}
    """
    for key, value in kwargs.items():
        if type(value) is str and "," in value:
            kwargs[key] = value.split(sep = ",")
    return kwargs
def extract_post_number(href, query):
    """ (str, str) -> int

    Extract post number from site link, with a predetermined query to specify location of post number.

    >>> extract_post_number("https://www.aaaaa.com/?no=123456", "no")
    123456
    """
    href_postnum_list = []
    href_postnum = 0
    # index of query inside of link string
    query_index = href.find(query)
    # if query is "no" and link includes no=123...
    # search_start_index points to 1
    search_start_index = query_index + len(query) + 1

    for i in range(int(search_start_index), len(href)):
        if href[i].isdigit():
            # Temporary reversed list of post number
            href_postnum_list.insert(0, int(href[i]))
        else:
            # Finish searching upon reaching nondigit
            break

    # Return ordered int from reversed list
    for i in range(len(href_postnum_list)):
        href_postnum += (href_postnum_list[i] * 10**i)

    return href_postnum
def update_feed():
    # Telegram Bot Configuration
    bot = telegram.Bot(token = '1822963809:AAEKMWyn9uBHXQ_m6D4yctWLcmC9bpsU8us')
    chat_id = 1327186896

    # Connect to sqlite3 DB
    con = sqlite3.connect(os.path.join(_instance_path, 'data.db'))
    cur = con.cursor()
    URLs = cur.execute("SELECT * FROM sitedata").fetchall()  

    # For debugging purpose
    print("running scraper at {}...".format(datetime.now().strftime("%Y/%m/%d %H:%M:%S")))  

    # To check hoy many new posts has been retrieved
    new_post_index = 0

    # Convert sitadata tuple to dictionary with keys
    for url_tuple in URLs:
        url = tuple_to_sitedata_dict(
            sitename = url_tuple[0],
            main_address = url_tuple[1],
            scrape_address = url_tuple[2],
            sitetype = url_tuple[3],
            link_query = url_tuple[4],
            postnum_query = url_tuple[5],
            title_query = url_tuple[6],
            author_query = url_tuple[7],
            sitecolor = url_tuple[8],
            js_included = url_tuple[9])

        # Latest post number from DB for comparison
        current_latest_postnum = cur.execute(
            "SELECT postnum FROM sitefeed WHERE sitename = ? ORDER BY postnum DESC LIMIT 1", (url["sitename"],)).fetchone()

        # Send HTTP request to the given URL
        # Retrieves the HTML data that server sends
        page = requests.get(url["scrape_address"])

        # Construct BeautifulSoup
        bs = BeautifulSoup(page.content, 'html.parser')

        #To identify feed link
        bs_results = bs.find_all(class_ = url["link_query"])

        # Dive into each page element
        for page in bs_results:
            
            temp_link = page.find('a', href = compile(url["postnum_query"]))

            # Filter out garbage value
            if temp_link is None:
                continue

            page_link = url["main_address"] + temp_link['href']

            page_postnum = extract_post_number(page_link, url["postnum_query"])

            # Control flow before going deep into the link to save time
            if (current_latest_postnum is not None and page_postnum <= current_latest_postnum[0]):
                print('No more new feeds for {0}\n'.format(url["sitename"]))
                break

            if(url["js_included"] == "Yes"): # If a site uses Javascript
                # Using selenium
                browser = webdriver.Edge()

                # Open browser
                browser.get(page_link)
                bs2 = BeautifulSoup(browser.page_source, 'html.parser')

                # After getting page source, close browser
                browser.close()

            else: # No Javascript
                # Send HTTP request to the given URL
                # Retrieves the HTML data that server sends
                link_resp = requests.get(page_link)

                # Construct BeautifulSoup
                bs2 = BeautifulSoup(link_resp.content, 'html.parser')

            # Find title, author in the link
            page_postdate = datetime.now().strftime("%Y/%m/%d %H:%M")
            page_title = bs2.find(class_ = url["title_query"]).text.strip()
            page_author = bs2.find(class_ = url["author_query"]).text.strip()

            print(page_postnum)
            print(page_postdate)
            print(page_title)
            print(page_author)
            print(page_link)

            if None in (page_title, temp_link):
                print('None detected among title, and link')
                continue
                    
            insert_feed_query = (
                "INSERT INTO sitefeed "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            )

            insert_tuple = (
            url["sitename"], url["sitetype"], page_postdate, page_postnum, page_title, page_author, page_link, url["sitecolor"])

            bot_text = '<b>{0}</b>\n  {1}\n\n<b>{2}</b>\n\n <a href = "{3}">Link</a>'.format(
                url["sitename"].upper(), page_author, page_title, page_link)

            # Add new feed to the Table
            cur.execute(insert_feed_query, insert_tuple)
            # Apply changes to DB
            con.commit()

            # Send real-time notification
            bot.send_message(
                chat_id = chat_id, 
                text= bot_text,
                parse_mode = 'HTML')

            new_post_index += 1
            
    # Close session
    cur.close()
    con.close()

    # How many new post has been retrieved
    if (new_post_index == 1):
        print(new_post_index, "new feed discovered in this iteration\n")
    elif (new_post_index > 1):
        print(new_post_index, "new feeds discovered in this iteration\n")
    else:
        print("no new feed discovered in this iteration\n")
def test_feed(url):
    try:
        # Send HTTP request to the given URL
        # Retrieves the HTML data that server sends
        page = requests.get(url["scrape_address"])

        # Construct BeautifulSoup
        bs = BeautifulSoup(page.content, 'html.parser')

        #To identify feed link
        bs_results = bs.find_all(class_ = url["link_query"])

        for page in bs_results:            
            temp_link = page.find('a', href = compile(url["postnum_query"]))

            # Filter out garbage value
            if temp_link is None:
                continue

            page_link = url["main_address"] + temp_link['href']

            page_postnum = extract_post_number(page_link, url["postnum_query"])

            if("js_included" in url.keys()): # If a site uses Javascript
                # Using selenium
                browser = webdriver.Edge()

                # Open browser
                browser.get(page_link)
                bs2 = BeautifulSoup(browser.page_source, 'html.parser')

                # After getting page source, close browser
                browser.close()

            else: # No Javascript
                # Send HTTP request to the given URL
                # Retrieves the HTML data that server sends
                link_resp = requests.get(page_link)

                # Construct BeautifulSoup
                bs2 = BeautifulSoup(link_resp.content, 'html.parser')

            # Find title, author in the link
            page_postdate = datetime.now().strftime("%Y/%m/%d %H:%M")
            page_title = bs2.find(class_ = url["title_query"]).text.strip()
            page_author = bs2.find(class_ = url["author_query"]).text.strip()

            print(page_postnum)
            print(page_postdate)
            print(page_title)
            print(page_author)
            print(page_link)
            return "success"

    except Exception as e:
        return(str(e))