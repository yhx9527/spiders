from crawlers.geek_crawler import GeekCrawler

def main():
    geeker_wx = GeekCrawler('https://time.geekbang.org/', 'cookie', 'geekbang.org', 'username', way='wx')
    geeker_wx.run()
    # geeker_pwd = GeekCrawler('https://time.geekbang.org/', 'cookie', 'geekbang.org', 'username', 'password', way='pwd')
    # geeker_pwd.run()


if __name__ == '__main__':
    main()