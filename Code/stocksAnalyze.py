# _file & filename 单个文件路径		_path 文件夹路径
# stockdata_list 1行15列数据  0日期,1股票代码,2名称,3收盘价,4最高价,5最低价,6开盘价,7前收盘,8涨跌额,9涨跌幅,10换手率,11成交量,12成交金额,13总市值,14流通市值


import requests
import random
from bs4 import BeautifulSoup as bs
import time
import os
import csv
import json
import math
import numpy as np

start_time = "20180101"
end_time = time.strftime('%Y%m%d',time.localtime(time.time()))
#end_time = "20190430"

root_path = "D:\\Workspace\\Python\\Stocks"
stockinfo_file = os.path.join(root_path, "Data", "stock_info.txt")
stockdata_path = os.path.join(root_path, "Data", "stock_data")
indexdata_path = os.path.join(root_path, "Data", "index_data")
resultdata_path = os.path.join(root_path, "Result", end_time)
if(not os.path.exists(resultdata_path)):
    os.mkdir(resultdata_path)



def read_csvfile(filename):
    with open(filename, 'r') as fp:
        data_list = list(csv.reader(fp))
        return data_list[0], data_list[1:]


def write_csvfile(filename, title, data_list):
    with open(filename, 'w') as fp:
        fp.write(",".join([str(item) for item in title]) + "\n")
        for row_item in data_list:
            fp.write(",".join([str(item) for item in row_item]) + "\n")


def insert_csvfile(filename, data_list):
    with open(filename, 'a') as fp:
        fp.write(",".join([str(item) for item in data_list]) + "\n")

def get_htmltext(url):
#    headers = {
#            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36'
#    }
    for ii in range(10):
        time.sleep(random.choice([1,2]))
        try:
#            response = requests.get(url, headers=headers)
            response = requests.get(url)
#            print("Get Successfully: " + url)
            if(response.status_code!=200):
                return ""
            break
        except Exception as e:
            print(e)
            continue
#    print(response.text)
    try:
        html_text = response.content.decode('utf8')
    except UnicodeDecodeError as e:
#        print(e)
        html_text = response.content.decode('gbk')
#    except NameError as e:
#        print(e)
#        html_text = ""
    except Exception as e:
        print(e)
        html_text = ""
    return html_text


def download_file(url, filename):
    for ii in range(10):
        time.sleep(random.choice([1,2]))
        try:
            data = requests.get(url)
            break
        except Exception as e:
            print(e)
            continue
    try:
        with open(filename, 'wb') as fp:
            chunk_size = 100000
            for chunk in data.iter_content(chunk_size):
                fp.write(chunk)
#        print("Download Successfully: " + url)
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
            for jj in range(ii, len(stockdata_list)):
                for kk in range(3,9):
                    stockdata_list[jj][kk] = round((float(stockdata_list[jj][kk])*float(stockdata_list[ii-1][7])/float(stockdata_list[ii][3])), 2)
    if(stockdata_list==[]):
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
#        print("开始生成股票列表……")
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
#                print("完成股票列表更新……")


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
#                print("{}-{}\t{}\t数据已经下载完成".format(start_time, end_time, stock_info))
            else:
                isMarketOpen = False
        else:
            isMarketOpen = False
    return isMarketOpen


def get_stockdata():
    with open(stockinfo_file, 'r') as fp:
        for stock_info in fp.readlines():
            if stock_info:
                stock_info = stock_info.split()[0]
                stock_code_new = stock_info.split("_")[1]
                stockdata_file = os.path.join(stockdata_path,'{}.csv'.format(stock_info))
                if(get_163data(stock_code_new, start_time, end_time, stockdata_file)):
                    check_stockdata(stockdata_file)
#                    print("{}-{}\t{}\t数据已经下载完成".format(start_time, end_time, stock_info))


def drop_Model_Select():
    resultfile_path = os.path.join(resultdata_path, "drop_Model_Select_Result.csv")
    title = ["股票名称", "股票总跌幅", "6日超跌(-6)", "12日超跌(-10)", "24日超跌(-16)", "股票跌幅天数", "收盘价连续最低天数", "最低价连续最低天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
        drop_counter = 0
        drop_range = 0
        closing_price = float(stockdata_list[0][3])
        least_price = float(stockdata_list[0][5])
        closing_counter = 0
        least_counter = 0
        for ii in range(len(stockdata_list)):
            if(float(stockdata_list[ii][9])<0):
                drop_counter += 1
                drop_range += float(stockdata_list[ii][9])
            else:
                break
        MA6 = 0
        MA12 = 0
        MA24 = 0
        for ii in reversed(range(len(stockdata_list))):
            MA6 = 2/7*float(stockdata_list[ii][3]) + 5/7*MA6
            MA12 = 2/13*float(stockdata_list[ii][3]) + 11/13*MA12
            MA24 = 2/25*float(stockdata_list[ii][3]) + 23/25*MA24
        MA6_range = (closing_price - MA6) / MA6 * 100
        MA12_range = (closing_price - MA12) / MA12 * 100
        MA24_range = (closing_price - MA24) / MA24 * 100
        for ii in range(1, len(stockdata_list)):
            if(least_price<float(stockdata_list[ii][3])):
                least_counter += 1
            else:
                break
        for ii in range(1, len(stockdata_list)):
            if(closing_price<float(stockdata_list[ii][3])):
                closing_counter += 1
            else:
                break
        if((drop_counter>0) or (least_counter>0)):
            resultdata_list.append([filename, drop_range, MA6_range, MA12_range, MA24_range, drop_counter, closing_counter, least_counter])
    write_csvfile(resultfile_path, title, resultdata_list)


def vshape_Model_Select():
    resultfile_path = os.path.join(resultdata_path, "vshape_Model_Select_Result.csv")
    title = ["股票名称", "股票总跌幅", "股票涨幅", "股票跌幅天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
        rise_range = 0
        drop_range = 0
        drop_counter = 0
        if((float(stockdata_list[0][10])>2*float(stockdata_list[1][10])) and (float(stockdata_list[0][9])>0)):
            rise_range = float(stockdata_list[0][9])
            for ii in range(1, len(stockdata_list)):
                if(float(stockdata_list[ii][9])<0):
                    drop_counter += 1
                    drop_range += float(stockdata_list[ii][9])
                else:
                    break
        if(drop_counter>0):
            resultdata_list.append([filename, drop_range, rise_range, drop_counter])
    write_csvfile(resultfile_path, title, resultdata_list)


def lagging_Model_Select():
    index_list = ["上证指数_0000001", "深证成指_1399001"]
    indexfile_list = [os.path.join(indexdata_path, (item+".csv")) for item in index_list]
    resultfile_path = os.path.join(resultdata_path, "lagging_Model_Select_Result.csv")
    title = ["股票名称", "股票涨跌幅", "指数涨跌幅", "股票总滞后幅", "股票滞后天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        if(filename.split(".")[0].split("_")[1][0]=="0"):
            indexfile = indexfile_list[0]
        else:
            indexfile = indexfile_list[1]
        _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
        _, indexdata_list = read_csvfile(indexfile)
        stock_range = 0
        index_range = 0
        lagging_range = 0
        lagging_counter = 0
        for ii in range(len(stockdata_list)):
            if(float(stockdata_list[ii][9])<float(indexdata_list[ii][9])):
                lagging_counter += 1
                stock_range += float(stockdata_list[ii][9])
                index_range += float(indexdata_list[ii][9])
                lagging_range += float(indexdata_list[ii][9]) - float(stockdata_list[ii][9])
            else:
                break
        if(lagging_counter>0):
            resultdata_list.append([filename, stock_range, index_range, lagging_range, lagging_counter])
    write_csvfile(resultfile_path, title, resultdata_list)


def MACD_Model_Select():
    resultfile_path = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    title = ["股票名称", "估算MACD贯穿天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
        EMA_12 = 0
        EMA_26 = 0
        DIFF_list = [0]
        DEA_9_list = [0]
        MACD_list = [0]
        for ii in reversed(range(len(stockdata_list))):
            EMA_12 = 11/13*EMA_12 + 2/13*float(stockdata_list[ii][3])
            EMA_26 = 25/27*EMA_26 + 2/27*float(stockdata_list[ii][3])
            DIFF = EMA_12 - EMA_26
            DEA_9 = 8/10*DEA_9_list[-1] + 2/10*DIFF
            MACD = (DIFF-DEA_9)*2
            DIFF_list.append(DIFF)
            DEA_9_list.append(DEA_9)
            MACD_list.append((DIFF-DEA_9)*2)
        if((MACD_list[-2]<0) and (MACD_list[-1]>MACD_list[-2]) and (DEA_9_list[-2]<0)):
            resultdata_list.append([filename, math.ceil(MACD_list[-1]/(MACD_list[-2]-MACD_list[-1]))])
    write_csvfile(resultfile_path, title, resultdata_list)


def obv_Model_Select():
    resultfile_path = os.path.join(resultdata_path, "obv_Model_Select_Result.csv")
    title = ["股票名称", "股票1日换手率OBV", "股票6日换手率MAOBV", "股票12日换手率MAOBV", "股票26日换手率MAOBV"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
#        print(filename)
        _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
        OBV = 0
        MAOBV_6 = 0
        MAOBV_12 = 0
        MAOBV_26 = 0
        for ii in reversed(range(len(stockdata_list))):
            if((float(stockdata_list[ii][4])-float(stockdata_list[ii][5]))==0):
                OBV = np.sign(float(stockdata_list[ii][9])) * float(stockdata_list[ii][10])
            else:
                OBV = ((float(stockdata_list[ii][3])-float(stockdata_list[ii][5])-(float(stockdata_list[ii][4])-float(stockdata_list[ii][3])))/
                    (float(stockdata_list[ii][4])-float(stockdata_list[ii][5]))*float(stockdata_list[ii][10]))
            MAOBV_6 = MAOBV_6*5/7 + OBV*2/7
            MAOBV_12 = MAOBV_12*11/13 + OBV*2/13
            MAOBV_26 = MAOBV_26*25/27 + OBV*2/27
        resultdata_list.append([filename, OBV, MAOBV_6, MAOBV_12, MAOBV_26])
    write_csvfile(resultfile_path, title, resultdata_list)


def box_Model_Select():
    resultfile_path = os.path.join(resultdata_path, "box_Model_Select_Result.csv")
    title = ["股票名称", "股票最高点价格", "股票最低点价格", "股票当前价格", "股票下跌幅度", "股票反弹幅度", "股票下跌天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
        closing_price = float(stockdata_list[0][3])
        for paratuple in [(100, 0.6), (60, 0.7), (30, 0.8)]:
            closing_price_list = [float(item[3]) for item in stockdata_list[:(min(len(stockdata_list), paratuple[0]))]]
            max_price = max(closing_price_list)
            max_offset = closing_price_list.index(max_price)
            min_price = min(closing_price_list)
            min_offset = closing_price_list.index(min_price)
            if((min_offset==3) and (min_offset<max_offset) and (min_price<paratuple[1]*max_price)):
                resultdata_list.append([filename, max_price, min_price, stockdata_list[0][3], ((min_price-max_price)/max_price), ((closing_price-min_price)/min_price), (max_offset-min_offset)])
    write_csvfile(resultfile_path, title, resultdata_list)


def AHCom_Model_Select():
    AHdata_path = os.path.join(root_path, "Data", "AH_stock_data")
    AHdataHistory_path = os.path.join(root_path, "Data", "AH_stock_data_history")

    def get_AHdata():
        AH_url = "http://quotes.money.163.com/hs/realtimedata/service/ah.php?host=/hs/realtimedata/service/ah.php&page=0&fields=SCHIDESP,PRICE,SYMBOL,AH,PERCENT,VOLUME&count=500"
        AHhistory_title = ["A股名称", "A股代码", "A股查询代码", "A股价格", "A股涨跌幅", "H股代码", "H股名称", "H股价格", "H股涨跌幅", "H股溢价率(溢价率=(H股价格*0.8545-A股价格)/A股价格*100%)"]
        AHdata_title = ["时间"] + AHhistory_title
        AHdataNew_list = []
        response = get_htmltext(AH_url)
        if(response!=""):
            AHdataNew_list = []
            for AHitem in json.loads(response)["list"]:
                if(("ST" in str(AHitem["AH"]["ASTOCKNAME"])) or (str(AHitem["SYMBOL"]).format(5)=="02922") or (float(AHitem["PRICE"])==0)):
                    continue
                AHdataNew = [str(AHitem["AH"]["ASTOCKNAME"]), str(AHitem["AH"]["A_SYMBOL"]).format(6), str(AHitem["AH"]["ASTOCKCODE"]).format(7),
                    str(AHitem["AH"]["A_PRICE"]), str(AHitem["AH"]["A_PERCENT"]*100), str(AHitem["SYMBOL"]).format(5), str(AHitem["SCHIDESP"]), 
                    str(AHitem["PRICE"]), str(AHitem["PERCENT"]*100), str(AHitem["AH"]["PREMIUMRATE"])]
                AHdataNew_list.append(AHdataNew)
            IsADataChange = True
            IsHDataChange = True
            if(os.path.exists(os.path.join(AHdataHistory_path, "temp.csv"))):
                _, AHdataOld_list = read_csvfile(os.path.join(AHdataHistory_path, "temp.csv"))
                IsADataChange = False
                IsHDataChange = False
                for AHdataNew in AHdataNew_list:
                    for AHdataOld in AHdataOld_list:
                        if(AHdataNew[2]==AHdataOld[2]):
                            if(float(AHdataNew[4])!=float(AHdataOld[4])):
                                IsADataChange = True
                            if(float(AHdataNew[8])!=float(AHdataOld[8])):
                                IsHDataChange = True
                if((AHdataOld_list==[]) and (AHdataNew_list!=[])):
                    IsADataChange = True
                    IsHDataChange = True
                if(not IsADataChange):
                    for ii in range(len(AHdataNew_list)):
                        AHdataNew_list[ii][4] = 0
                if(not IsHDataChange):
                    for ii in range(len(AHdataNew_list)):
                        AHdataNew_list[ii][8] = 0
            if(IsADataChange or IsHDataChange):
                write_csvfile(os.path.join(AHdataHistory_path, "temp.csv"), AHhistory_title, AHdataNew_list)
                write_csvfile(os.path.join(AHdataHistory_path, end_time+".csv"), AHhistory_title, AHdataNew_list)
                for AHdataNew in AHdataNew_list:
                    AHfilename = os.path.join(AHdata_path, (str(AHdataNew[0]) + "_" + str(AHdataNew[2]).format(7) + ".csv"))
                    if(os.path.exists(AHfilename)):
                        insert_csvfile(AHfilename, ([end_time]+AHdataNew))
                    else:
                        write_csvfile(AHfilename, AHdata_title, ([[end_time]+AHdataNew]))
                return True
            else:
                return False

    if(get_AHdata()):
        resultfile_path = os.path.join(resultdata_path, "AHCom_Model_Select.csv")
        title = ["股票名称", "A股涨跌幅", "H股涨跌幅", "A股总滞后幅", "股票滞后天数"]
        resultdata_list = []
        for filename in os.listdir(AHdata_path):
#            print(filename)
            _, AHdata_list = read_csvfile(os.path.join(AHdata_path, filename))
            AStock_range = 0
            HStock_range = 0
            AHCom_range = 0
            AHComCounter = 0
            for ii in range(len(AHdata_list)):
                if(float(AHdata_list[ii][5])<float(AHdata_list[ii][9])):
                    AHComCounter += 1
                    AStock_range += float(AHdata_list[ii][5])
                    HStock_range += float(AHdata_list[ii][9])
                    AHCom_range += float(AHdata_list[ii][9]) - float(AHdata_list[ii][5])
                else:
                    break
            if(AHComCounter>0):
                resultdata_list.append([filename, AStock_range, HStock_range, AHCom_range, AHComCounter])
        write_csvfile(resultfile_path, title, resultdata_list)


def ABCom_Model_Select():
    ABdata_path = os.path.join(root_path, "Data", "AB_stock_data")
    ABdataHistory_path = os.path.join(root_path, "Data", "AB_stock_data_history")

    def get_ABdata():
        AB_url = "http://quotes.money.163.com/hs/realtimedata/service/ab.php?host=/hs/realtimedata/service/ab.php&page=0&query=AB:_exists_;VOLUME:_exists_&fields=NAME,PRICE,SYMBOL,AB,PERCENT,VOLUME,CODE&sort=AB.A_PERCENT&order=desc&count=500&type=query"
        ABhistory_title = ["A股名称", "A股代码", "A股查询代码", "A股价格", "A股涨跌幅", "B股代码", "B股查询代码", "B股名称", "B股价格", "B股涨跌幅", "B/A成交量比", "B股溢价率(溢价率=(H股价格*0.8545-A股价格)/A股价格*100%)"]
        ABdata_title = ["时间"] + ABhistory_title
        ABdataNew_list = []
        response = get_htmltext(AB_url)
        if(response!=""):
            ABdataNew_list = []
            for ABitem in json.loads(response)["list"]:
                if(("ST" in str(ABitem["AB"]["A_NAME"]))):
                    continue
                ABdataNew = [str(ABitem["AB"]["A_NAME"]), str(ABitem["AB"]["A_SYMBOL"]).format(6), str(ABitem["AB"]["A_CODE"]).format(7),
                    str(ABitem["AB"]["A_PRICE"]), str(ABitem["AB"]["A_PERCENT"]*100), str(ABitem["SYMBOL"]).format(6), str(ABitem["CODE"]).format(7),
                    str(ABitem["NAME"]), str(ABitem["PRICE"]), str(ABitem["PERCENT"]*100), str(ABitem["AB"]["VOL_RATIO"]), str(ABitem["AB"]["YJL"])]
                ABdataNew_list.append(ABdataNew)
            IsADataChange = True
            IsBDataChange = True
            if(os.path.exists(os.path.join(ABdataHistory_path, "temp.csv"))):
                _, ABdataOld_list = read_csvfile(os.path.join(ABdataHistory_path, "temp.csv"))
                IsADataChange = False
                IsBDataChange = False
                for ABdataNew in ABdataNew_list:
                    for ABdataOld in ABdataOld_list:
                        if(ABdataNew[2]==ABdataOld[2]):
                            if(float(ABdataNew[4])!=float(ABdataOld[4])):
                                IsADataChange = True
                            if(float(ABdataNew[9])!=float(ABdataOld[9])):
                                IsBDataChange = True
                if((ABdataOld_list==[]) and (ABdataNew_list!=[])):
                    IsADataChange = True
                    IsBDataChange = True
                if(not IsADataChange):
                    for ii in range(len(ABdataNew_list)):
                        ABdataNew_list[ii][4] = 0
                if(not IsHDataChange):
                    for ii in range(len(ABdataNew_list)):
                        ABdataNew_list[ii][9] = 0
            if(IsADataChange or IsBDataChange):
                write_csvfile(os.path.join(ABdataHistory_path, "temp.csv"), ABhistory_title, ABdataNew_list)
                write_csvfile(os.path.join(ABdataHistory_path, end_time+".csv"), ABhistory_title, ABdataNew_list)
                for ABdataNew in ABdataNew_list:
                    ABfilename = os.path.join(ABdata_path, (str(ABdataNew[0]) + "_" + str(ABdataNew[2]).format(7) + ".csv"))
                    if(os.path.exists(ABfilename)):
                        insert_csvfile(ABfilename, ([end_time]+ABdataNew))
                    else:
                        write_csvfile(ABfilename, ABdata_title, ([[end_time]+ABdataNew]))
                return True
            else:
                return False

    if(get_ABdata()):
        resultfile_path = os.path.join(resultdata_path, "ABCom_Model_Select.csv")
        title = ["股票名称", "A股涨跌幅", "B股涨跌幅", "A股总滞后幅", "股票滞后天数"]
        resultdata_list = []
        for filename in os.listdir(ABdata_path):
#            print(filename)
            _, ABdata_list = read_csvfile(os.path.join(ABdata_path, filename))
            AStock_range = 0
            BStock_range = 0
            ABCom_range = 0
            ABComCounter = 0
            for ii in range(len(ABdata_list)):
                if(float(ABdata_list[ii][5])<float(ABdata_list[ii][10])):
                    ABComCounter += 1
                    AStock_range += float(ABdata_list[ii][5])
                    BStock_range += float(ABdata_list[ii][10])
                    ABCom_range += float(ABdata_list[ii][10]) - float(ABdata_list[ii][5])
                else:
                    break
            if(ABComCounter>0):
                resultdata_list.append([filename, AStock_range, BStock_range, ABCom_range, ABComCounter])
        write_csvfile(resultfile_path, title, resultdata_list)


#def test_Model_Select():
#    resultfile_path = os.path.join(resultdata_path, "test_Model_Select_Result.csv")
#    title = ["股票名称", test_item]
#    resultdata_list = []
#    for filename in os.listdir(stockdata_path):
#        _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
#        if(test_num>0):
#            resultdata_list.append([filename, test_item])
#    write_csvfile(resultfile_path, title, resultdata_list)


def clear_data():
    filenames = os.listdir(stockdata_path)
    for filename in filenames:
        filepath = os.path.join(stockdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)


def analyze_stockdata():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tDrop_Model_Select Begin!")
    drop_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tDrop_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tVshape_Model_Select Begin!")
    vshape_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tVshape_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tLagging_Model_Select Begin!")
    lagging_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tLagging_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tobv_Model_Select Begin!")
    obv_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tobv_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACD_Model_Select Begin!")
    MACD_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACD_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tAHCom_Model_Select Begin!")
    AHCom_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tAHCom_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tABCom_Model_Select Begin!")
    ABCom_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tABCom_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tbox_Model_Select Begin!")
    box_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tbox_Model_Select Finished!")


if __name__ == "__main__":
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Prepare Begin!")
    if(get_index_data()):
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Stock Data Begin!")
        clear_data()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Stock Data Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tGenerage Stock Data Begin!")
        get_stockinfo()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tGenerage Stock Data Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Download Begin!")
        get_stockdata()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Download Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Prepare Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Begin!")
    analyze_stockdata()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Finished!")
