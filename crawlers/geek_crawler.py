from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from requests import Session
import requests
import time
import json
import os
from crawlers.db import RedisClient
import random

# 爬取失败时随机改变headers中的user-agent
USER_AGENT = ['User-Agent:Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
              'User-Agent:Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
              'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
              'User-Agent:Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
              'User-Agent:Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; en) Presto/2.8.131 Version/11.11',
              'User-Agent:Opera/9.80 (Windows NT 6.1; U; en) Presto/2.8.131 Version/11.11',
              'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11',
              'User-Agent: Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Maxthon 2.0)',
              'User-Agent: Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
              'User-Agent: Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SE 2.X MetaSr 1.0; SE 2.X MetaSr 1.0; .NET CLR 2.0.50727; SE 2.X MetaSr 1.0)',
              'User-Agent: Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; 360SE)'
              ]
STEP = 1
# 超时时间
TIMEOUT = 60

DIR = os.getcwd() + '/data_geek/'

headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Content-Length': '65',
            'Content-Type': 'application/json',
            'Host': 'time.geekbang.org',
            'Origin': 'https://time.geekbang.org',
            'Referer': 'https://time.geekbang.org/column/article/94156',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36'
        }
class GeekCrawler():
    def __init__(self, login_url, type, website, username, password=None, way='wx'):
        # chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument('--headless')
        self.browser = webdriver.Chrome()
        self.login_url = login_url
        self.username = username
        self.password = password
        self.session = Session()
        self.redis = RedisClient(type=type, website=website)
        # 获取cookie的途径
        self.way = way

    #通过账号密码登陆获取cookie
    def cookie_pwd(self):
        self.browser.get(self.login_url)

        enter_login_btn = self.browser.find_element_by_css_selector('.userinfo .control .pc')
        enter_login_btn.click()
        login_by_pass_btn = self.browser.find_element_by_css_selector('.card .forget a')
        login_by_pass_btn.click()
        self.browser.refresh()

        username_input = self.browser.find_element_by_css_selector('.nw-phone-container .nw-phone-wrap input')
        pass_input = self.browser.find_element_by_css_selector('.input-wrap input')
        login_btn = self.browser.find_element_by_css_selector('.mybtn')
        username_input.send_keys(self.username)
        pass_input.send_keys(self.password)
        login_btn.click()

        time.sleep(1)
        # self.browser.get(self.login_url)
        self.browser.get(self.login_url)
        cookies = self.browser.get_cookies()
        cookie = {item['name']:item['value'] for item in cookies}
        print('获取到极客cookies', cookie)
        return cookie

    # 通过微信扫码登陆获取cookie
    def cookie_wx(self):
        self.browser.get(self.login_url)
        enter_login_btn = self.browser.find_element_by_css_selector('.userinfo .control .pc')
        enter_login_btn.click()
        wxlogin_btn = self.browser.find_element_by_css_selector('.third-login .weixin')
        wxlogin_btn.click()
        try:
            wait = WebDriverWait(self.browser, 20)
            wxImg = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.wrp_code img')))
            imgUrl = wxImg.get_attribute('src')
            print('登陆图片链接：', imgUrl)
            res = requests.get(imgUrl)
            if res.status_code == 200:
                with open('wxlogin_jike.png', 'wb') as file:
                    file.write(res.content)
        except Exception:
            print('微信登陆图片下载异常')
        login_wait = WebDriverWait(self.browser, 300)
        login_wait.until(EC.title_contains('极客时间'))
        cookies = self.browser.get_cookies()
        cookie = {item['name']: item['value'] for item in cookies}
        print('获取到极客cookies', cookie)
        return cookie

    # 获取cookie
    def get_cookie(self):
        cookie = self.redis.get(self.username)
        if not cookie:
            res = eval("self.{}()".format('cookie_'+self.way))
            # res = self.cookie_wx()
            self.redis.set(self.username, json.dumps(res))
            return res
        print('使用已存在的cookie', cookie)
        return json.loads(cookie)
    
    #获取用户购买的专栏
    def getProducts(self):
        products_url = 'https://time.geekbang.org/serv/v1/my/products/all'
        cookies = self.get_cookie()

        products=[]
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://account.geekbang.org/dashboard/buy',
            'Sec-Fetch-Mode': 'cors',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36'
        }
        try:
            res = self.session.post(products_url, cookies=cookies, headers=headers, timeout=TIMEOUT)
            print('购买的专栏', res.text, res.status_code)
            temp = json.loads(res.text)
            list = temp['data'][0]['list']
            products = [{'title': item['title'], 'cid': item['extra']['column_id']} for item in list]
        except:
            print('获取专栏products失败')
        return products

    def is_article_exists(self, arti):
        subdir = DIR + arti['subdir']
        if not os.path.exists(subdir):
            return False
        filename = subdir + '/'+arti['index']+'.'+arti['article_title']+'.html'
        if not os.path.exists(filename):
            return False
        return True

    #获取某个专栏的文章列表，并对每篇文章使用生成器一一处理
    def get_articles(self, cid, subdir):
        cookie = self.get_cookie()
        articlesUrl = 'https://time.geekbang.org/serv/v1/column/articles'

        data = json.dumps({
            'cid': cid,
            'order': "earliest",
            'prev': 0,
            'sample': 'false',
            'size': 100,
        })
        r = self.session.post(articlesUrl, data=data, headers=headers, cookies=cookie)
        res = json.loads(r.text)
        articles = res['data']['list']
        print('获取文章列表', articles)
        tasks = []
        errorMap={}
        for idx, item in enumerate(articles):
            item['index'] = str(idx).zfill(2)
            item['subdir'] = subdir

        while len(articles):
            # arti = articles.pop(0)
            arti = articles.pop(len(articles)-1)
            data = json.dumps({
                'id': arti['id'],
                'include_neighbors': 'true',
                'is_freelyread': 'true'
            })
            if not self.is_article_exists(arti):
                try:
                    headers['Referer'] = 'https://time.geekbang.org/column/article/' + str(arti['id'])
                    res = self.session.post('https://time.geekbang.org/serv/v1/article', data=data, headers=headers,
                                            cookies=cookie, timeout=TIMEOUT)
                    temp = json.loads(res.text)
                    if res.status_code == 200 and temp['code']==0:
                        content = temp['data']
                        yield {
                            'index': arti['index'],
                            'article_title': content['article_title'],
                            'article_content': content['article_content'],
                        }
                        time.sleep(2)

                    else:
                        raise Exception('响应错误')
                except Exception:
                    print('请求异常', res.status_code, res.content)
                    if (res.status_code == 451):
                        headers['User-Agent'] = random.choice(USER_AGENT)
                        time.sleep(10)
                    articles.insert(0, arti)
                    random.shuffle(articles)
            else:
                print('文件已存在，跳过')

    # async def do_article(self, **kwargs):
    #     conn = aiohttp.TCPConnector(ssl=False)
    #     async with aiohttp.ClientSession(connector=conn, cookies=kwargs['cookies'], headers=kwargs['headers']) as session:
    #         try:
    #             async with session.post('https://time.geekbang.org/serv/v1/article', json=kwargs['data']) as res:
    #                 content = await res.text()
    #                 print('ressssss', content)
    #         except():
    #             print('获取文章出错')

    # def run_async(self):
    #     tasks = self.get_articles()
    #     loop = asyncio.get_event_loop()
    #     for i in range(0, len(tasks), STEP):
    #         tasks_part = tasks[i: i+STEP]
    #         loop.run_until_complete(asyncio.wait(tasks_part))
    #         time.sleep(5)

    # 生成专栏目录
    def gen_category(self, path):
        category_template = '''
<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <title>目录</title>
    </head>
    <body>
        <h1>目录</h1>
        <div>{content}</div>
    </body>
</html>   
        '''
        category_temp = ''
        category = path + '/目录.html'
        files = os.listdir(path)
        print(files)
        sorted_files = sorted(files, key=lambda x: x.split('.')[0])
        print(sorted_files)
        for filename in sorted_files:
            category_temp += '<a href="{href}">{title}</a></br>'.format(href='./' + filename,
                                                                        title=filename)
        with open(category, 'w+') as f:
            f.write(category_template.format(content=category_temp))
            print('目录写入成功')

    # 运行
    def run(self):
        template = '''
<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
    </head>
    <body>
        <h1>{title}</h1>
        <div>{content}</div>
    </body>
</html>
        '''

        if not os.path.exists(DIR):
            os.mkdir(DIR)
        products = self.getProducts()
        for item in products:
            path = DIR+item['title']
            if not os.path.exists(path):
                os.mkdir(path)
            content = self.get_articles(cid=item['cid'], subdir=item['title'])
            for i in content:
                html = template.format(title=i['article_title'], content=i['article_content'])
                filename = path+'/'+i['index']+'.'+i['article_title']+'.html'
                if not os.path.exists(filename):
                    with open(filename, 'w+') as f:
                        f.write(html)
                        print(i['index']+'.'+i['article_title']+'文件写入成功')
                else:
                    print(i['index']+'.'+'.'+i['article_title']+'文件已存在')
            self.gen_category(path)



