#!/usr/bin/python3
from facebook_scraper import get_posts as get_fb_post
from pyquery import PyQuery
from urllib.parse import urljoin
from dotenv import dotenv_values
import asyncio
import requests
import json
import re
from datetime import datetime
import urllib
from os import path
from playwright.async_api import async_playwright
import traceback
import hashlib

config = dotenv_values('/etc/projects/webscrape_noti/.env')
cachePath = '/var/projects/webscrape_noti/cache.json'
cookiePath = '/etc/projects/webscrape_noti/fb-cookie.json'
enoticeCrtFile = '/etc/projects/webscrape_noti/coj.go.th.pem'

def sendMsg(msg):
    if config['NOTIFY_METHOD'] == 'notify':
        notify = Notify() 
        notify.send(msg)
    if config['NOTIFY_METHOD'] == 'telegram':
        ses = requests.Session()
        tgReq = ses.get(
            'https://api.telegram.org/bot{0}/sendMessage?{1}'.format(
                config['TELEGRAM_TOKEN'],
                urllib.parse.urlencode({
                    'chat_id': config['TELEGRAM_CHAT_ID'],
                    'text': msg
                })
            ),
             timeout=30
        )

        print ('sendMsg [{}]| Telegram Code: {}'.format(datetime.now().isoformat(), tgReq.status_code))
        print ('sendMsg [{}]| Response: {}'.format(datetime.now().isoformat(), tgReq.text))

async def getFBPageLatestPost (pageName):
    return sorted([
        {
            "id": post['post_id'],
            "text": post['post_text'],
            "time": post['time'],
            "image": post['image'],
            "post_url": post['post_url']
        }
        for post in get_fb_post(pageName, page_limit=3, cookies=cookiePath)
    ], key=lambda i:int(i['time'].timestamp()) if 'time' in i else 0, reverse=True)[0]

async def getLawRUnews():
    isGetPass = False
    while not isGetPass:
        pageReq = requests.get('http://www.law.ru.ac.th/index.php', timeout=30)
        pq = PyQuery(pageReq.text)
        latestNews = pq('#art-main .art-post:first-child .globalnews .gn_static:first-child')
        newsText = latestNews.find('a:nth-child(2)').text()
        newsLinkRaw = (latestNews.find('a:first-child').attr('href') or '').lstrip('/')
        newsId = re.findall(r'/(\d+)', newsLinkRaw)
        newsLink = f"http://www.law.ru.ac.th/{newsLinkRaw}"
        newsImg = latestNews.find('img').attr('src')
        newsDate = re.search(r'(\, \d{1,2} \w+ \d{4})', latestNews.text())
        return {
            "id": int(newsId[1]) if newsId and len(newsId) >= 2 else None,
            "text": newsText,
            "time": datetime.strptime(newsDate[0].strip(' ,'), '%d %B %Y') if newsDate else None,
            "image": newsImg,
            "post_url": newsLink
        }

async def getENotice():
    getCnt = 0
    while getCnt < 3:
        try:
            pageReq = requests.post(
                'https://enotice.coj.go.th/search', verify=enoticeCrtFile,
                timeout=260,
                headers={
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,th;q=0.7",
                    "cache-control": "max-age=0",
                    "content-type": "application/x-www-form-urlencoded",
                    "sec-ch-ua": "\"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"114\", \"Google Chrome\";v=\"114\"",
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": "\"Windows\"",
                    "sec-fetch-dest": "document",
                    "sec-fetch-mode": "navigate",
                    "sec-fetch-site": "same-origin",
                    "sec-fetch-user": "?1",
                    "sec-gpc": "1",
                    "Referer": "https://enotice.coj.go.th/",
                    "Referrer-Policy": "strict-origin-when-cross-origin"
                },
                data=b'type=all&keyword=%E0%B8%A3%E0%B8%B1%E0%B8%81%E0%B8%A9%E0%B9%8C%E0%B8%81%E0%B8%B3%E0%B9%80%E0%B8%99%E0%B8%B4%E0%B8%94'
            )

            # print('getENotice [DEBUG] | text : %s'%(pageReq.text))
            pq = PyQuery(pageReq.text)

            latestNews = pq('#home .post-item:first-child')
            if len(latestNews) < 1 :
                print ('getENotice [%s] | Query found none'%(datetime.now().isoformat()))
                return {
                    "topic": '----- No COJ E-Notice news ----',
                    "text": '==== No content ====',
                    "time": '',
                    "post_url": 'https://enotice.coj.go.th'
                }
            newsTopic = latestNews.find('h4').text()
            newsText = latestNews.text()
            newsTime = latestNews.find('.row span.text-danger').text()
            newsLink = (latestNews.find('.row div:nth-child(2)>a:first-child').attr('href') or '').lstrip('/')
            print ('getENotice [%s] | Query complete'%(datetime.now().isoformat()))
            return {
                "topic": newsTopic,
                "text": newsText,
                "time": newsTime,
                "post_url": newsLink
            }

        except Exception as e:
            print ('getENotice [%s] | Error raised #%d: %s'%(datetime.now().isoformat(), getCnt, e))
            getCnt += 1
    return None

async def getRatchakitja():
    getCnt = 0
    while getCnt < 3:
        try:
            pageReq = requests.post(
                'https://ratchakitcha.soc.go.th/search-result',
                timeout=60,
                headers={
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,th;q=0.7",
                    "cache-control": "max-age=0",
                    "content-type": "application/x-www-form-urlencoded",
                    "sec-ch-ua": "\"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"114\", \"Google Chrome\";v=\"114\"",
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": "\"Windows\"",
                    "sec-fetch-dest": "document",
                    "sec-fetch-mode": "navigate",
                    "sec-fetch-site": "same-origin",
                    "sec-fetch-user": "?1",
                    "sec-gpc": "1",
                    "upgrade-insecure-requests": "1",
                    "Referer": "https://ratchakitcha.soc.go.th/",
                    "Referrer-Policy": "strict-origin-when-cross-origin"
                },
                data=b'action=search&search-keyword=%E0%B8%A3%E0%B8%B1%E0%B8%81%E0%B8%A9%E0%B9%8C%E0%B8%81%E0%B8%B3%E0%B9%80%E0%B8%99%E0%B8%B4%E0%B8%94&search-field=title&type%5B%5D=%E0%B8%81&type%5B%5D=%E0%B8%82&type%5B%5D=%E0%B8%84&type%5B%5D=%E0%B8%87&type%5B%5D=%E0%B8%87%E0%B8%9E%E0%B8%B4%E0%B9%80%E0%B8%A8%E0%B8%A9'
            )
            pq = PyQuery(pageReq.text)
            # print('getRatchakitja [DEBUG] | text : %s'%(pageReq.text))

            latestNews = pq('#result2 .post-thumbnail-list .post-thumbnail-entry:first-child')
            if len(latestNews) < 1 :
                print ('getRatchakitja [%s] | Query found none'%(datetime.now().isoformat()))
                return {
                    "topic": '----- No Ratchakitja news ----',
                    "text": '==== No content ====',
                    "time": '',
                    "post_url": 'https://ratchakitcha.soc.go.th'
                }
            newsTopic = latestNews.find('.post-thumbnail-content a:first-child').text()
            newsText = newsTopic
            newsTime = latestNews.find('.post-date').text()
            newsLink = (latestNews.find('.post-thumbnail-content>a:first-child').attr('href') or '').lstrip('/')
            print ('getRatchakitja [%s] | Query complete'%(datetime.now().isoformat()))
            return {
                "topic": newsTopic,
                "text": newsText,
                "time": newsTime,
                "post_url": newsLink
            }

        except Exception as e:
            print ('getRatchakitja [%s] | Error raised #%d: %s'%(datetime.now().isoformat(), getCnt, e))
            getCnt += 1
    return None

async def getDolNotice():
    getCnt = 0
    while getCnt < 3:
        try:
            pageReq = requests.get(
                'http://announce.dol.go.th/index.php?searchprovince=&searchoffice=&searchtype=&searchtitle=&searchconcerned=%E0%B8%A3%E0%B8%B1%E0%B8%81%E0%B8%A9%E0%B9%8C%E0%B8%81%E0%B8%B3%E0%B9%80%E0%B8%99%E0%B8%B4%E0%B8%94&searchdocno=&btnSearch=',
                timeout=60,
                headers={
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,th;q=0.7",
                    "sec-gpc": "1"
                }
            )
            pq = PyQuery(pageReq.text)
            # print('getDolNotice [DEBUG] | text : %s'%(pageReq.text))

            latestNews = pq('.container table > tbody > tr:nth-child(2)')
            if len(latestNews) < 1 :
                print ('getDolNotice [%s] | Query found none'%(datetime.now().isoformat()))
                return {
                    "topic": '----- No DOL news ----',
                    "text": '==== No content ====',
                    "time": '',
                    "post_url": 'http://announce.dol.go.th'
                }
            newsTopic = "{} for {}".format(
                latestNews.find('th:nth-child(3)').text(),
                latestNews.find('th:nth-child(4)').text()
            )
            newsText = latestNews.text()
            newsTime = latestNews.find('th:nth-child(6)').text()
            newsLink = (latestNews.find('th:nth-child(9) a').attr('href') or '').lstrip('/')
            print ('getDolNotice [%s] | Query complete'%(datetime.now().isoformat()))
            return {
                "topic": newsTopic,
                "text": newsText,
                "time": newsTime,
                "post_url": urlparse.urljoin("http://announce.dol.go.th/", newsLink) if newsLink else "http://announce.dol.go.th/"
            }

        except Exception as e:
            print ('getDolNotice [%s] | Error raised #%d: %s'%(datetime.now().isoformat(), getCnt, e))
            getCnt += 1
    return None

async def getCojCaseTrack(courtName, isRed, casePrefix, caseNo, caseYear):
    getCnt = 0
    while getCnt < 3:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                await page.goto("https://cios.coj.go.th/tracking")
                print ('getCojCaseTrack [%s] | Filling the form'%(datetime.now().isoformat()))
                # Select Court name.
                await page.locator('.change_coj .filter-option').click()
                await page.locator('#tracking-frm > div:nth-child(1) > div > div > div > input').fill(courtName)
                await page.locator('#tracking-frm > div:nth-child(1) > div > div > div > input').press("Enter")
                # Select case type
                await page.locator(
                    "#tracking-frm input[type=radio][value=case_red]"
                        if isRed
                        else "#tracking-frm input[type=radio][value=case_black]"
                ).click()
                # Select case prefix.
                await page.locator('#tracking-frm > div.row > div:nth-child(1) > div > button').click()
                await page.locator('#tracking-frm > div.row > div:nth-child(1) > div > div > div > input').fill(casePrefix)
                await page.locator('#tracking-frm > div.row > div:nth-child(1) > div > div > ul > li').filter(has_text=re.compile("^{}$".format(casePrefix))).click()
                # Fill case no.
                await page.locator('#tracking-frm input[name="bid"]').fill(caseNo)
                await page.locator('#tracking-frm input[name="byear"]').fill(caseYear)
                # Submit
                await page.locator('#tracking-frm button[type="submit"]').click()
                print ('getCojCaseTrack [%s] | Submitting the form'%(datetime.now().isoformat()))
                # Wait Result
                await page.wait_for_url("**/result.html")
                print ('getCojCaseTrack [%s] | Fetching the result'%(datetime.now().isoformat()))
        
                # Format text
                # :nth-child(n+1):nth-child(-n+3) -> Select first two table
                # @see https://stackoverflow.com/a/28061560
                newsText = ''
                newsTextGeneral = 'ข้อมูลคดีทั่วไป:\n\n'
                for tbl in await page.locator('.page-container .content .row:nth-child(n+1):nth-child(-n+3) table').all():
                    for nthIdx, th in enumerate(await tbl.locator('thead th').all()):
                        td = tbl.locator('tbody td').nth(nthIdx)
                        thText = await th.inner_text()
                        tdText = await td.inner_text()
                        newsTextGeneral += '{}: {}\n'.format(thText, tdText or '-- ไม่มีข้อมูล --')

                newsText += newsTextGeneral
                
                for pnl in await page.locator('.page-container .content .row:nth-child(4) .panel.panel-flat').all():
                    sectionText = await pnl.locator('ul.nav a').inner_text()
                    sectionData = ''
                    
                    for row in await pnl.locator('table tbody tr').all():
                        for nthIdx, th in enumerate(await pnl.locator('table thead th').all()):
                            if not sectionData: sectionData += '\n'

                            # Prevent empty record
                            if await row.locator('td').count() > 1:
                                td = row.locator('td').nth(nthIdx)
                                thText = await th.inner_text()
                                tdText = await td.inner_text()
                                sectionData += '{}: {}\n'.format(thText, tdText or '-- ไม่มีข้อมูล --')

                    newsText += '\n+++++++++++++++++++++++++++++++\n{}:\n\n{}'.format(
                        sectionText,
                        sectionData.strip() or '-- ไม่มีข้อมูล --'
                    )

                # newsText = await page.locator('body > div.page-container > div > div > div.content').inner_text()
                hasher = hashlib.new('sha256')
                hasher.update(newsText.encode())
                newsHash = hasher.hexdigest()
                newsTime = await page.locator('body > div.page-container > div > div > div.content > div:nth-child(5) > div > font').inner_text()
                newsText += '\n+++++++++++++++++++++++++++++++\nอัพเดต:{}\n'.format(newsTime)
                # screenshot = await page.screenshot(full_page=True)
                newsTopic = 'คดี{}ที่ {} {} / {}'.format('แดง' if isRed else 'ดำ', casePrefix, caseNo, caseYear)
                
                await browser.close()
                return {
                    "topic": newsTopic,
                    "text": newsText,
                    "time": newsTime,
                    "post_url": "https://cios.coj.go.th/tracking?{}".format(
                        urllib.parse.urlencode({
                            "_case": newsTopic,
                            "_update": newsHash
                        })
                    ),
                    # "screenshot": screenshot
                }

        except Exception as e:
            print ('getCojCaseTrack [%s] | Error raised #%d: %s'%(datetime.now().isoformat(), getCnt, e))
            getCnt += 1
    return None


async def main ():
    print('main [%s] | Start'%(datetime.now().isoformat()))
    
    try:
        print('main [%s] | Fetching news'%(datetime.now().isoformat()))
        """ loop = asyncio.get_event_loop()
        asyncio.set_event_loop(loop)
        postPages = loop.run_until_complete(asyncio.gather(*(
            # [ getPageLatestPost(pageName) for pageName in [ 'sorworporCOP', 'rulawofficial' ] ] + # , 'ramkhamhaeng.ru'
            [ getENotice(), getRatchakitja(), getDolNotice() ]
            # [ getPageLatestPost('Training.Lawyer') ]
        ))) """
        postPages = await asyncio.gather(*(
            # [ getPageLatestPost(pageName) for pageName in [ 'sorworporCOP', 'rulawofficial' ] ] + # , 'ramkhamhaeng.ru'
            [
                getENotice(),
                getRatchakitja(),
                getDolNotice(),
                getCojCaseTrack('ศาลแขวงธนบุรี', False, 'ผบ', '399', '2566')
            ]
            # [ getPageLatestPost('Training.Lawyer') ]
        ))

        print('main [%s] | Processing'%(datetime.now().isoformat()))
        newDataObj = {
            'COJ E-Notice': postPages[0],
            'Ratchakitja':  postPages[1],
            'DOL E-Notice': postPages[2],
            'COJ Case Track (Bosz)': postPages[3],
        }
        oldDataObj = {}
        if path.exists(cachePath):
            with open(cachePath, 'r') as file:
                oldData = file.read().replace('\n', '')
                oldDataObj = json.loads(oldData)
        
        newMsg = ''
        for pageName, pageInfo in newDataObj.items():
            if pageInfo is None:
                newMsg += f"\n Unable to fetch: {pageName}\n"
            if (
                pageInfo is not None and
                (
                    pageName not in oldDataObj or
                    'post_url' not in oldDataObj[pageName] or
                    oldDataObj[pageName]['post_url'] != pageInfo['post_url']
                )
            ) :
                newMsg += f"New message from {pageName} at {str(pageInfo['time'])}\n\nTopic: {pageInfo['topic']}\nURL: {pageInfo['post_url']}\n\n{pageInfo['text']}\n\n------------------------------------\n\n"

        if newMsg:
            print('main [%s] | New news found, transmiting'%(datetime.now().isoformat()))
            sendMsg(newMsg)
            with open(cachePath, 'w') as file:
                file.write(json.dumps(newDataObj, default=str))
                file.close()
    
    except Exception as e:
        print ('main [%s] | Error raised: %s'%(datetime.now().isoformat(), e))
        traceback.print_exc()
        pass

    print('main [%s] | Complete'%(datetime.now().isoformat()))

if __name__ ==  '__main__':
    print('#root [%s] | Init'%(datetime.now().isoformat()))
    asyncio.run(main())
