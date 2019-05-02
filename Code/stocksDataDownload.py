import requests
import random
from bs4 import BeautifulSoup as bs
import time
import os
import csv

start_time = "20190101"
end_time = time.strftime('%Y%m%d',time.localtime(time.time()))
#end_time = "20190430"

root_path = "D:\\Workspace\\Python\\Stocks"
stockinfo_path = os.path.join(root_path, "Data", "stock_info.txt")
stockdata_path = os.path.join(root_path, "Data", "stock_data")
indexdata_path = os.path.join(root_path, "Data", "index_data")


def get_index_data():
    index_list = ["上证指数_0000001", "深证成指_1399001"]
    isMarketOpen = False
    for stock_info in index_list:
        stock_code_new = stock_info.split("_")[1]
        try:
            time.sleep(random.choice([1,2]))
            stock_url = 'http://quotes.money.163.com/trade/lsjysj_zhishu_{}.html'.format(stock_code_new[1:])
            response = requests.get(stock_url).text
            soup = bs(response, 'lxml')
            if (end_time == (soup.find('input', {'name': 'date_end_type'}).get('value').replace('-', ''))):
                isMarketOpen = True
                time.sleep(random.choice([1,2]))
                download_url = "http://quotes.money.163.com/service/chddata.html?code={}&start={}&end={}&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER;TCAP;MCAP".format(stock_code_new, start_time, end_time)
                data = requests.get(download_url)
                with open(os.path.join(indexdata_path,'{}.csv'.format(stock_info)), 'wb') as fp:                                 #保存数据
                    chunk_size = 100000
                    for chunk in data.iter_content(chunk_size):
                        fp.write(chunk)
                    print("{}-{}\t{}\t数据已经下载完成".format(start_time, end_time, stock_info))
                with open(os.path.join(stockdata_path,'{}.csv'.format(stock_info)), 'r+') as fp:                                 #保存数据
                    stock_data_list = list(csv.reader(fp))
                    for ii in reversed(range(1, len(stock_data_list))):
                        if(float(stock_data_list[ii][3])==0):
#                            print(stock_data_list[ii])
                            stock_data_list.pop(ii)
                    fp.seek(0)
                    for ii in range(len(stock_data_list)):
                        fp.write(','.join(stock_data_list[ii])+'\n')
        except Exception as e:
            print(e)
    return isMarketOpen


def get_stock_info():
    url = "http://quote.eastmoney.com/stock_list.html"
    headers = {
            'Referer': 'http://quote.eastmoney.com',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36'
            }
    all_ul = []
    for ii in range(10):
        time.sleep(10)
        try:
            response = requests.get(url, headers=headers).content.decode('gbk')   # 网站编码为 gbk 需要解码
#            response = requests.get(url, headers=headers).content
#            print(response)
        except Exception as e:
            response = requests.get(url, headers=headers).content
#            print(response)
        soup = bs(response, 'lxml')
        try:
            all_ul = soup.find('div', id='quotesearch').find_all('ul')   # 获取两个ul 标签数据
            print("下载股票列表……完成")
            break
        except Exception as e:
            continue
    if(all_ul==[]):
        return
    with open(stockinfo_path, 'w+', encoding='utf-8') as fp:
        for ul in all_ul:
            all_a = ul.find_all('a')            # 获取ul 下的所有的a 标签
            for a in all_a:
                isStock = False
                stock_info = a.text
                stock_name = stock_info[:stock_info.index('(')]
                stock_code = stock_info[(stock_info.index('(')+1):stock_info.index(')')]
                if("ST" in stock_name):
                    continue
                if int(stock_code[0]) in [0, 2, 3, 6, 9]:
                    if int(stock_code[0]) in [6, 9]:
                        stock_code_new = '0' + stock_code
                        fp.write(stock_name + "_" + stock_code_new+"\n")
                    elif int(stock_code[0]) in [0, 2, 3]:
                        if not int(stock_code[:3]) in [201, 202, 203, 204]:
                            stock_code_new = '1' + stock_code
                            fp.write(stock_name + "_" + stock_code_new + "\n")
                        else:
                            continue
                    else:
                        continue
                else:
                    continue


def get_stock_data():
    with open(stockinfo_path, 'r+', encoding='utf-8') as fp:
        for stock_info in fp.readlines():
            if stock_info:
                stock_info = stock_info.split()[0]
                stock_code_new = stock_info.split("_")[1]
                try:
                    time.sleep(random.choice([1,2]))
                    stock_url = 'http://quotes.money.163.com/trade/lsjysj_{}.html'.format(stock_code_new[1:])
                    response = requests.get(stock_url).text
                    soup = bs(response, 'lxml')
                    if (end_time == (soup.find('input', {'name': 'date_end_type'}).get('value').replace('-', ''))):
                        time.sleep(random.choice([1,2]))
                        download_url = "http://quotes.money.163.com/service/chddata.html?code={}&start={}&end={}&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER;TCAP;MCAP".format(stock_code_new, start_time, end_time)
                        data = requests.get(download_url)
                        with open(os.path.join(stockdata_path,'{}.csv'.format(stock_info)), 'wb') as fp:                                 #保存数据
                            chunk_size = 100000
                            for chunk in data.iter_content(chunk_size):
                                fp.write(chunk)
                        with open(os.path.join(stockdata_path,'{}.csv'.format(stock_info)), 'r+') as fp:                                 #保存数据
                            stock_data_list = list(csv.reader(fp))
                            for ii in reversed(range(1, len(stock_data_list))):
                                if(float(stock_data_list[ii][3])==0):
#                                    print(stock_data_list[ii])
                                    stock_data_list.pop(ii)
                            fp.seek(0)
                            for ii in range(len(stock_data_list)):
                                fp.write(','.join(stock_data_list[ii])+'\n')
                except Exception as e:
                    print(e)
            else:
                break


if __name__ == "__main__":
	if(get_index_data()):
		get_stock_info()
		get_stock_data()