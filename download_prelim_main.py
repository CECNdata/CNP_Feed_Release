#!/usr/bin/env python
# coding=utf-8

# http://www.customs.gov.cn/customs/302249/zfxxgk/2799825/302274/302277/4185050/index.html
# download here


#download mapping
files={
    "进出口商品类章总值表" : {
        "filename": "CNP-Customs-prelim-World-<currcy>_<month><year>.html",
    },
    "进口商品类章金额表" : {
        "filename": "CNP-Customs-prelim-import-<currcy>_<month><year>.html",
    },
    "出口商品类章金额表" : {
        "filename": "CNP-Customs-prelim-export-<currcy>_<month><year>.html",
    }
}

import os
import re
from urllib.parse import urlparse

my_proxy_str = os.environ.get("MY_PROXY")
# 一行 if/else 自动解析代理，没设置就 None
proxy_config = (lambda p: {
    "server": f"{p}" if "://" in p else f"http://{p}",  # 保持协议
    **({"username": urlparse(p).username, "password": urlparse(p).password} if urlparse(p).username else {})
} if p else None)(my_proxy_str)


for file in files.keys():
    files[file]["xpath"]=[]
    for currency_index in ["1","2"]:
        files[file]["xpath"].append(f"""((//td[contains(text(),"{file}")])[{currency_index}]/..//a[@href])[last()]""")

##for title in ["进口商品类章金额表","出口商品类章金额表"]:
##    for currency_index in ["1","2"]:
##        xpath.append(f"""((//td[contains(text(),"{title}")])[{currency_index}]/..//a[@href])[last()]""")

from playwright.sync_api import sync_playwright

def save(page,fullTitle,filename):
    date=re.search(r'(?P<year>20\d{2})年(?P<month>\d{1,2})月', fullTitle)
    year=date.group("year")
    month=date.group("month").zfill(2)

    filename=filename.replace("<month>",month)
    filename=filename.replace("<year>",year)

    print(fullTitle)

    if "人民币" in fullTitle:
        filename=filename.replace("<currcy>","RMB")
    elif "美元" in fullTitle:
        filename=filename.replace("<currcy>","USD")
    else:
        raise ValueError("not sure rmb or usd, maybe page is not correct")

    try:os.mkdir("download")
    except:pass

    with open(f"./download/{filename}","w") as f:
        f.write(page.content())

def run(playwright):
    browser = playwright.firefox.launch(
        headless=True,
        proxy=proxy_config  # None 就不使用代理
    )
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 "
                   "Safari/537.36"
    )
    context.set_default_timeout(30000)  
    # 设置导航相关操作超时 20 秒（例如 page.goto、page.wait_for_url）
    context.set_default_navigation_timeout(60000) 
    # context.add_init_script(path="stealth.min.js")
    page = context.new_page()
    
    page.goto("http://www.customs.gov.cn/customs/302249/zfxxgk/2799825/302274/302277/4185050/index.html",wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    page.locator("""xpath=(//div[@class="tjYear"]//a)[1]""").click() ##  click the latest year
    page.wait_for_timeout(5000)

    from urllib.parse import urljoin
    for f in files.keys():
        files[f]["link"]=[]
        for xpath in files[f]["xpath"]:
            l=(page.locator(f"""xpath={xpath}""").get_attribute("href")) 
            l=urljoin("http://www.customs.gov.cn/",l)
            files[f]["link"].append(l)

    print(files)
    for f in files.keys():
        for l in files[f]["link"]:
            page.goto(l,wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            fullTitle = page.locator(f"""xpath=//h2[contains(.,"{f}")]""").inner_text()
            try:
                save(page,fullTitle,files[f]["filename"])
            except Exception as e:
                print(str(e))

    browser.close()


with sync_playwright() as playwright:
    run(playwright)
