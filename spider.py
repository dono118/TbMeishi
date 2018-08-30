import re

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyquery import PyQuery as pq
from selenium.webdriver.chrome.options import Options
import pymongo

from config import *

# browser = webdriver.Chrome()  # 有头chrome
# 无头chrome 设置参数
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
browser = webdriver.Chrome(chrome_options=chrome_options)

wait = WebDriverWait(browser, 10)  # 改写一下，后面会频繁应用

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]


def search():
    """搜索商品信息"""
    print('正在保存第{}页'.format(1))
    try:
        browser.get('https://www.taobao.com')
        # 声明搜索框元素，并且设置等待，presence_of_element_located条件是判断已经加载出来
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#q"))  # 这里的css选择器，右键网页源代码复制可得
        )
        # 声明搜索按钮，等待，element_to_be_clickable判断按钮是可以点击的
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#J_TSearchForm > div.search-button > button'))
        )
        input.send_keys(KEYWORD)  # 输入文字
        submit.click()  # 点击按钮
        # total 为总页数 presence_of_element_located判断total元素已经加载完成
        total = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total'))
        )
        get_products()
        return total.text  # 返回总页数
    except TimeoutException:
        return search()  # 如果发生错误，再次搜索。


def next_page(page_number):
    """下一页 """
    print('正在保存第{}页'.format(page_number))
    try:
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#mainsrp-pager > div > div > div > div.form > input"))
            # 这里的css选择器，右键网页源代码复制可得
        )
        # 等待，判断按钮是可以点击的
        submit = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit'))
        )
        input.clear()  # 清空输入框
        input.send_keys(page_number)  # 输入页码
        submit.click()
        # 判断高亮是否是当前页数，从而判断是否翻页成功
        wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span'),
                str(page_number))
        )
        get_products()
    except TimeoutException:
        next_page(page_number)  # 若失败，在试一次


def get_products():
    """获取商品信息"""
    # 判断items元素加载成功
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-itemlist .items .item'))
    )
    # 解析，先取得网页源代码
    html = browser.page_source
    doc = pq(html)
    items = doc('#mainsrp-itemlist .items .item').items()  # items()返回一个生成器，生成每个item
    for item in items:
        product = {
            'image': item.find('.pic .img').attr('src'),
            'price': item.find('.price').text().replace('\n', ''),
            'deal': item.find('.deal-cnt').text()[:-3],
            'title': item.find('.title').text(),
            'shop': item.find('.shop').text(),
            'location': item.find('.location').text()
        }  # 构造字典，存储商品信息，准备存入数据库
        save_to_mongo(product)


def save_to_mongo(result):
    """保存到数据库"""
    try:
        if db[MONGO_TABLE].insert_one(result):
            print('存储到数据库成功', result)
    except Exception:
        print("存储失败")


def main():
    try:
        total = search()
        total = int(re.compile('(\d+)').search(total).group(1))  # 强制转换为int类型
        for i in range(2, total + 1):
            next_page(i)
    except Exception:
        print('something wrong~!')
    finally:  # 保证浏览器关闭
        browser.close()


if __name__ == '__main__':
    main()
