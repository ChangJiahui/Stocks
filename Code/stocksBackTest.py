import requests
import random
from bs4 import BeautifulSoup as bs
import time
import os
import csv
import math


start_time = "20140101"
end_time = "20190514"


root_path = "D:\\Workspace\\Python\\Stocks"
stockinfo_file = os.path.join(root_path, "Data", "stock_info.txt")
stockdata_path = os.path.join(root_path, "Data", "stock_data_history")
indexdata_path = os.path.join(root_path, "Data", "index_data_history")
backtestdata_path = os.path.join(root_path, "BackTest")


def read_csvfile(filename):
    with open(filename, 'r') as fp:
        data_list = list(csv.reader(fp))
        return data_list[0], data_list[1:]


def write_csvfile(filename, title, data_list):
    with open(filename, 'w') as fp:
        fp.write(",".join([str(item) for item in title]) + "\n")
        for row_item in data_list:
            fp.write(",".join([str(item) for item in row_item]) + "\n")


def get_htmltext(url):
#    headers = {
#            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36'
#    }
    for ii in range(10):
        time.sleep(random.choice([1,2]))
        try:
            response = requests.get(url)
#            response = requests.get(url, headers=headers)
#            print("Get Successfully: " + url)
            if(response.status_code!=200):
#                time.sleep(60)
                continue
            try:
                html_text = response.content.decode('utf-8-sig')
            except UnicodeDecodeError as e:
                html_text = response.content.decode('gbk')
#                print(e)
#            except NameError as e:
#                print(e)
#                html_text = ""
            return html_text
        except Exception as e:
            print(e)
    return ""


def download_file(url, filename):
    for ii in range(10):
        time.sleep(random.choice([1,2]))
        try:
            response = requests.get(url)
            if(response.status_code!=200):
#                time.sleep(60)
                continue
            with open(filename, 'wb') as fp:
                chunk_size = 100000
                for chunk in response.iter_content(chunk_size):
                    fp.write(chunk)
#            print("Download Successfully: " + url)
            return True
        except Exception as e:
            print(e)
    return False


def detect_163data(url):
    response = get_htmltext(url)
    if(response!=""):
#        print(response)
        soup = bs(response, 'lxml')
        if(end_time == (soup.find('input', {'name': 'date_end_type'}).get('value').replace('-', ''))):
            return True
    return False


def get_163data(stock_code_new, start_time, end_time, filename):
    download_url = "http://quotes.money.163.com/service/chddata.html?code={}&start={}&end={}&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER;TCAP;MCAP".format(stock_code_new, start_time, end_time)
    return download_file(download_url, filename)


def check_stockdata(filename):
    title, stockdata_list = read_csvfile(filename)
    for ii in reversed(range(len(stockdata_list))):
        if((stockdata_list[ii][8]=="None") or (stockdata_list[ii][9]=="None") or (stockdata_list[ii][10]=="None") or (float(stockdata_list[ii][3])==0)):
            stockdata_list.pop(ii)
    for ii in range(1, len(stockdata_list)-1):
        if(float(stockdata_list[ii-1][7])!=float(stockdata_list[ii][3])):
            proportion = float(stockdata_list[ii-1][7])/float(stockdata_list[ii][3])
            for jj in range(ii, len(stockdata_list)):
                for kk in range(3,9):
                    stockdata_list[jj][kk] = round(float(stockdata_list[jj][kk])*proportion, 2)
    if(stockdata_list==[]):
        os.remove(filename)
    elif((float(stockdata_list[0][4])==float(stockdata_list[0][5])) or ("ST" in stockdata_list[0][2])):
        os.remove(filename)
    else:
        write_csvfile(filename, title, stockdata_list)


def get_stockinfo():
#    url = "http://quote.eastmoney.com/stocklist.html"
    url = "http://quote.eastmoney.com/stock_list.html"
    response = get_htmltext(url)
    if(response==""):
        return False
    else:
        soup = bs(response, 'lxml')
        all_ul = soup.find('div', id='quotesearch').find_all('ul')   # 获取两个ul 标签数据
        with open(stockinfo_file, 'w') as fp:
            for ul in all_ul:
                ull_a = ul.find_all('a')
                for a in ull_a:
                    stock_info = a.text
                    stock_name = stock_info[:stock_info.index('(')]
                    stock_code = stock_info[(stock_info.index('(')+1):stock_info.index(')')]
                    if(("ST" in stock_name) or ("B" in stock_name) or (int(stock_code[0]) not in [0, 2, 6, 9]) or (int(stock_code[:3]) in [201, 202, 203, 204])):
                        continue
                    if(int(stock_code[0]) in [0, 2]):
                        stock_code_new = '1' + stock_code
                    else:
                        stock_code_new = '0' + stock_code
                    if(detect_163data('http://quotes.money.163.com/trade/lsjysj_{}.html'.format(stock_code))):
                        fp.write(stock_name+"_"+stock_code_new+"\n")


def get_index_data():
    index_list = ["上证指数_0000001", "深证成指_1399001"]
    isMarketOpen = False
    for stock_info in index_list:
        indexdata_file = os.path.join(indexdata_path,'{}.csv'.format(stock_info))
        stock_code_new = stock_info.split("_")[1]
        if(detect_163data('http://quotes.money.163.com/trade/lsjysj_zhishu_{}.html'.format(stock_code_new[1:]))):
            isMarketOpen = True
            if(get_163data(stock_code_new, start_time, end_time, indexdata_file)):
                check_stockdata(indexdata_file)
            else:
                isMarketOpen = False
        else:
            isMarketOpen = False
    return isMarketOpen


def get_stockdata():
    with open(stockinfo_file, 'r') as fp:
        for stock_info in fp.readlines():
            if stock_info:
#                print(stock_info)
                stock_info = stock_info.split()[0]
                stock_code_new = stock_info.split("_")[1]
                stockdata_file = os.path.join(stockdata_path,'{}.csv'.format(stock_info))
                if(get_163data(stock_code_new, start_time, end_time, stockdata_file)):
                    check_stockdata(stockdata_file)
#                    print("{}-{}\t{}\t数据已经下载完成".format(start_time, end_time, stock_info))


def clear_data():
    filenames = os.listdir(stockdata_path)
    for filename in filenames:
        filepath = os.path.join(stockdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)


def MACD_Model_BackTest():
    backtestfile_path = os.path.join(backtestdata_path, "MACD_Model_BackTest_Result.csv")
    title = ["股票名称", "购买日期", "购买价格", "卖出日期", "卖出价格", "盈利比例"]
    backtestdata_list = []
    for filename in os.listdir(stockdata_path):
#        print(filename)
        stock_info = filename.split(".")[0]
        _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
        dropcounter = 0
        EMA12_list = [0]
        EMA26_list = [0]
        DIFF_list = [0]
        DEA9_list = [0]
        MACD_list = [0]
        isBuy = False
        buy_price = 0
        isBuy = False
        buy_date = ""
        buy_price = 0
        for ii in reversed(range(2, len(stockdata_list)-1)):
#            print(stockdata_list[ii])
            closing_price = float(stockdata_list[ii][3])
            EMA12 = 11/13*EMA12_list[-1] + 2/13*closing_price
            EMA26 = 25/27*EMA26_list[-1] + 2/27*closing_price
            DIFF = EMA12 - EMA26
            DEA9 = 8/10*DEA9_list[-1] + 2/10*DIFF
            MACD = (DIFF-DEA9)*2
            EMA12_list.append(EMA12)
            EMA26_list.append(EMA26)
            DIFF_list.append(DIFF)
            DEA9_list.append(DEA9)
            MACD_list.append(MACD)
            if((MACD_list[-2]<0) and (MACD_list[-1]>MACD_list[-2]) and (DEA9_list[-1]<0)):
                if(math.ceil(MACD_list[-1]/(MACD_list[-2]-MACD_list[-1]))<3):
                    cross_price = (DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
                    parallel_price = (5/8*MACD_list[-1]+DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
                    if(parallel_price>float(stockdata_list[ii-1][5])):
                        buy_date = stockdata_list[ii-1][0]
                        buy_price = parallel_price
                        isBuy = True
            if((MACD_list[-2]>0) and (MACD_list[-1]<MACD_list[-2]) and (DEA9_list[-1]>0) and isBuy):
                if(math.ceil(MACD_list[-1]/(MACD_list[-2]-MACD_list[-1]))<3):
                    cross_price = (DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
                    parallel_price = (5/8*MACD_list[-1]+DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
                    sell_date = stockdata_list[ii-1][0]
                    sell_price = float(stockdata_list[ii-1][6])
                    profit = (sell_price - buy_price) / (buy_price)
                    isBuy = False
                    backtestdata_list.append([stock_info, buy_date, buy_price, sell_date, sell_price, profit])
    write_csvfile(backtestfile_path, title, backtestdata_list)


def vshape_Model_BackTest():
    backtestfile_path = os.path.join(backtestdata_path, "vshape_Model_BackTest_Result.csv")
    title = ["股票名称", "购买日期", "购买价格", "卖出日期", "卖出价格", "盈利比例"]
    backtestdata_list = []
    gaincounter = 0
    losscounter = 0
    waiting_counter = 5
    for filename in os.listdir(stockdata_path):
#        print(filename)
        stock_info = filename.split(".")[0]
        _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
        isBuy = False
        buy_price = 0
        sell_price = 0
        buy_date = ""
        sell_date = ""
        profit_counter = 0
        for ii in reversed(range(5, len(stockdata_list)-3)):
            maxprice = max([float(item[3]) for item in stockdata_list[ii:min(ii+100, len(stockdata_list))]])
            minprice = min([float(item[3]) for item in stockdata_list[ii:min(ii+100, len(stockdata_list))]])
            closingprice = float(stockdata_list[ii][3])
            rebound_range = (closingprice-minprice)/maxprice*100
            if(rebound_range<0.2 and (float(stockdata_list[ii+2][3])<float(stockdata_list[ii+2][6])) and ((float(stockdata_list[ii+1][3])>float(stockdata_list[ii+1][6])))
                and (float(stockdata_list[ii+1][5])<float(stockdata_list[ii+2][3])) and (float(stockdata_list[ii+1][5])>float(stockdata_list[ii+2][5]))
                and (float(stockdata_list[ii+2][9])<-3) and (float(stockdata_list[ii+1][9])>1) and ((float(stockdata_list[ii+1][10])/float(stockdata_list[ii+2][10]))>abs(float(stockdata_list[ii+1][9])/float(stockdata_list[ii+2][9])))):
                buy_price = float(stockdata_list[ii+1][3])*0.99
                if(buy_price>float(stockdata_list[ii][5])):
                    buy_date = stockdata_list[ii][0]
                    if(max([float(stockdata_list[jj][4]) for jj in range(ii-5,ii)])>buy_price*1.03):
                        sell_price = buy_price*1.03
                        profit = 0.03
                        gaincounter += 1
                    else:
                        sell_price = float(stockdata_list[ii-5][3])
                        profit = (sell_price - buy_price) / (buy_price)
                        losscounter += 1
                    profit_counter += profit
                    backtestdata_list.append([stock_info, buy_date, buy_price, sell_date, sell_price, profit])
    write_csvfile(backtestfile_path, title, backtestdata_list)
    print("盈利: " + str(gaincounter))
    print("亏损: " + str(losscounter))
    print("总盈利: " + str(profit_counter))


def shadow_Model_BackTest():
    backtestfile_path = os.path.join(backtestdata_path, "shadow_Model_BackTest_Result.csv")
    title = ["股票名称", "购买日期", "购买价格", "卖出日期", "卖出价格", "盈利比例"]
    backtestdata_list = []
    gaincounter = 0
    losscounter = 0
    waiting_counter = 5
    for filename in os.listdir(stockdata_path):
#        print(filename)
        stock_info = filename.split(".")[0]
        _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
        isBuy = False
        buy_price = 0
        sell_price = 0
        buy_date = ""
        sell_date = ""
        profit_counter = 0
        for ii in reversed(range(5, len(stockdata_list)-3)):
            maxprice = max([float(item[3]) for item in stockdata_list[ii:min(ii+100, len(stockdata_list))]])
            minprice = min([float(item[3]) for item in stockdata_list[ii:min(ii+100, len(stockdata_list))]])
            closingprice = float(stockdata_list[ii][3])
            rebound_range = (closingprice-minprice)/maxprice*100
            shadow_range = (min(float(stockdata_list[ii+1][3]), float(stockdata_list[ii+1][6]))-float(stockdata_list[ii+1][5]))/float(stockdata_list[ii+1][3])*100
            volumn_ratio = float(stockdata_list[ii+1][3])
            if(rebound_range<0.2 and (float(stockdata_list[ii+1][9])<3) and (shadow_range>3)):
                buy_price = float(stockdata_list[ii+1][3])*0.99
                if(buy_price>float(stockdata_list[ii][5])):
                    buy_date = stockdata_list[ii][0]
                    if(max([float(stockdata_list[jj][4]) for jj in range(ii-5,ii)])>buy_price*1.03):
                        sell_price = buy_price*1.03
                        profit = 0.03
                        gaincounter += 1
                    else:
                        sell_price = float(stockdata_list[ii-5][3])
                        profit = (sell_price - buy_price) / (buy_price)
                        losscounter += 1
                    profit_counter += profit
                    backtestdata_list.append([stock_info, buy_date, buy_price, sell_date, sell_price, profit])
    write_csvfile(backtestfile_path, title, backtestdata_list)
    print("盈利: " + str(gaincounter))
    print("亏损: " + str(losscounter))
    print("总盈利: " + str(profit_counter))


if __name__ == "__main__":
    vshape_Model_BackTest()