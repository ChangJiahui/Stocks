import requests
import random
from bs4 import BeautifulSoup as bs
import time
import os
import csv

#stock_code_list = []

def get_stock_info():
    """
    通过东方财富网上爬取股票的名称代码
    """
    url = "http://quote.eastmoney.com/stocklist.html"
    headers = {
            'Referer': 'http://quote.eastmoney.com',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36'
            }
    response = requests.get(url, headers=headers).content.decode('gbk')   # 网站编码为gbk 需要解码
    soup = bs(response, 'lxml')
    all_ul = soup.find('div', id='quotesearch').find_all('ul')   # 获取两个ul 标签数据
    with open('stock_info.txt', 'w+', encoding='utf-8') as fp:
        for ul in all_ul:
            all_a = ul.find_all('a')            # 获取ul 下的所有的a 标签
            for a in all_a:
                isStock = False
                stock_info = a.text
                stock_name = stock_info[:stock_info.index('(')]
                stock_code = stock_info[(stock_info.index('(')+1):stock_info.index(')')]
                # 由于东方财富网上获取的代码一部分为基金，无法获取数据，故将基金剔除掉。
                # 沪市股票以6,9开头，深市以0,2,3开头，但是部分基金也是2开头，201/202/203/204这些也是基金
                # 另外获取data的网址股票代码 沪市前加0， 深市前加1
                # 去掉 ST 类型的风险警示特别是可能已经退市的股票
                if("ST" in stock_name):
                    continue
                if int(stock_code[0]) in [0, 2, 3, 6, 9]:
                    if int(stock_code[0]) in [6, 9]:
                        stock_code_new = '0' + stock_code
#                        stock_code_list.append(stock_code_new)
                        fp.write(stock_name + "_" + stock_code_new+"\n")
                    elif int(stock_code[0]) in [0, 2, 3]:
                        if not int(stock_code[:3]) in [201, 202, 203, 204]:
                            stock_code_new = '1' + stock_code
#                            stock_code_list.append(stock_code_new)
                            fp.write(stock_name + "_" + stock_code_new + "\n")
                        else:
                            continue
                    else:
                        continue
                else:
                    continue


def get_stock_data():
#    headers = {
#        'Referer': 'http://quotes.money.163.com/',
#        'transfer-encoding': 'chunked',
#        'content-type': 'application/octet-stream',
#        'connection': 'keep-alive',
#        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36'
#    }
    with open("stock_info.txt", 'r+', encoding='utf-8') as fp:
        for stock_info in fp.readlines():
            if stock_info:
                stock_info = stock_info.split()[0]
#                print(stock_info)
                stock_code_new = stock_info.split("_")[1]
#                print(stock_code_new)
                try:
#                    time.sleep(random.choice([1,2]))
#                    stock_url = 'http://quotes.money.163.com/trade/lsjysj_{}.html'.format(stock_code_new[1:])
#                    response = requests.get(stock_url).text
#                    print(response)
#                    soup = bs(response, 'lxml')
#                    start_time = soup.find('input', {'name': 'date_start_type'}).get('value').replace('-', '')
#                    end_time = soup.find('input', {'name': 'date_end_type'}).get('value').replace('-', '')
                    start_time = "20190301"
                    end_time = "20190314"
                    time.sleep(random.choice([1,2]))
                    download_url = "http://quotes.money.163.com/service/chddata.html?code={}&start={}&end={}&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER;TCAP;MCAP".format(stock_code_new, start_time, end_time)
                    data = requests.get(download_url)
                    with open('stock_data'+os.sep+'{}.csv'.format(stock_info), 'wb') as fp:                                 #保存数据
                        chunk_size = 100000
                        for chunk in data.iter_content(chunk_size):
                            fp.write(chunk)
#                        fp.write(data)
#                    print("{}-{}\t{}\t数据已经下载完成".format(start_time, end_time, stock_info[:-1]))
                except Exception as e:
#                    print(stock_info)
                    print(e)
            else:
                break


def stock_model_select(num):
    with open("select_result"+str(num)+".csv", 'w') as fp:
        row0 = "股票名称,"
        for ii in range(1,num+1):
            row0 = row0 + "股票涨跌幅" + str(ii) + ","
        row0 = row0 + "总涨跌幅" + ","
        fp.write(row0 + "\n")
    datapath = "D:\\workspace\\Python\\Stocks\\stock_data"
    filenames = os.listdir(datapath)
    for filename in filenames:
        filepath = os.path.join(datapath, filename)
        with open(filepath, "r") as fp:
            reader = csv.reader(fp)
            stock_data_list = list(reader)
            if(len(stock_data_list)>(num+1)):
                isSelect = True
                try:
                    for ii in range(1, num+1):
                        if(float(stock_data_list[ii][9])>0):
                            isSelect = False
                            break
                        elif(float(stock_data_list[ii][4])==float(stock_data_list[ii][5])):
                            isSelect = False
                            break
                except:
                    isSelect = False
                if(isSelect):
                    droprange = 0
                    with open("select_result"+str(num) + ".csv", 'a') as fp:
                        datarow=filename+","
                        for ii in range(1, num+1):
                            droprange += float(stock_data_list[ii][9])
                            datarow = datarow + stock_data_list[ii][9] + ","
                        datarow = datarow + str(droprange) + ","
                        fp.write(datarow + "\n")


if __name__ == "__main__":
    get_stock_info()
#    get_stock_data()
#    stock_model_select(6)