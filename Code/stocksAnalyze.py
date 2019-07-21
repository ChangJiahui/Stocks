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
import tushare as ts
import numpy as np
import execjs
import xlrd
import multiprocessing


tspro = ts.pro_api("119921ff45f95fd77e5d149cd1e64e78572712b3d0a5ce38157f255b")

start_time = "19900101"
end_time = time.strftime('%Y%m%d',time.localtime(time.time()))
#end_time = "20190621"

root_path = "D:\\Workspace\\Python\\Stocks"
stockinfo_file = os.path.join(root_path, "Data", "stockinfo.txt")
stockdata_path = os.path.join(root_path, "Data", "stock_data")
stockgdzjc_path = os.path.join(root_path, "Data", "stock_gdzjc")
indexdata_path = os.path.join(root_path, "Data", "index_data")
resultdata_path = os.path.join(root_path, "Result", end_time)
if __name__=="__main__":
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
            if(row_item!=[]):
                fp.write(",".join([str(item) for item in row_item]) + "\n")


def insert_csvfile(filename, data_list):
    with open(filename, 'a') as fp:
        fp.write(",".join([str(item) for item in data_list]) + "\n")


def read_xlsfile(filename):
    workbook = xlrd.open_workbook(filename)
    table = workbook.sheet_by_index(0)
    data_list = []
    for row_num in range(1, table.nrows):
        data_list.append(table.row_values(row_num))
    return data_list[0], data_list[1:]


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


def get_jsvar(url, varname):
    for ii in range(10):
        response = get_htmltext(url)
        if(response.find(varname)!=-1):
            return execjs.compile(response).eval(varname)
    return None


def detect_163data(url):
    response = get_htmltext(url)
    if(response!=""):
#        print(response)
        soup = bs(response, 'lxml')
        if(end_time == (soup.find('input', {'name': 'date_end_type'}).get('value').replace('-', ''))):
            return True
    return False


def get_163data(stock163code, start_time, end_time, filename):
    download_url = "http://quotes.money.163.com/service/chddata.html?code={}&start={}&end={}&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER;TCAP;MCAP".format(stock163code, start_time, end_time)
    return download_file(download_url, filename)


def check_stockdata(filename):
    title, stockdata_list = read_csvfile(filename)
    for ii in reversed(range(len(stockdata_list))):
        if((len(stockdata_list[ii])!=15) or (stockdata_list[ii][8]=="None") or (stockdata_list[ii][9]=="None") or (stockdata_list[ii][10]=="None") or (float(stockdata_list[ii][3])==0)):
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
# 得到股票信息字典列表 stock_dict{stocktype,stockname,stockcode, stock163code}
    def get_indexcomponent(stocktype, url, indexcomponent_file):
        download_file(url, indexcomponent_file)
        _, CSIdata_list = read_xlsfile(indexcomponent_file)
        stockdict_list = []
        for CSIitem in CSIdata_list:
            stockdict_list.append({'stocktype':stocktype, 'stockname': CSIitem[5], 'stockcode': CSIitem[4]})
        return stockdict_list
    HS300_url = "http://www.csindex.com.cn/uploads/file/autofile/cons/000300cons.xls"
    HS300_filepath = os.path.join(root_path, "Data", "HS300.xls")
    CSI500_url = "http://www.csindex.com.cn/uploads/file/autofile/cons/000905cons.xls"
    CSI500_filepath = os.path.join(root_path, "Data", "CSI500.xls")
    CSI1000_url = "http://www.csindex.com.cn/uploads/file/autofile/cons/000852cons.xls"
    CSI1000_filepath = os.path.join(root_path, "Data", "CSI1000.xls")
    CSIAll_url = "http://www.csindex.com.cn/uploads/file/autofile/cons/000902cons.xls"
    CSIAll_filepath = os.path.join(root_path, "Data", "CSIAll.xls")
    HS300_list = get_indexcomponent("HS300", HS300_url, HS300_filepath)
    CSI500_list = get_indexcomponent("CSI500", CSI500_url, CSI500_filepath)
    CSI1000_list = get_indexcomponent("CSI1000", CSI1000_url, CSI1000_filepath)
    CSIAll_list = get_indexcomponent("CSIAll", CSIAll_url, CSIAll_filepath)
    with open(stockinfo_file, 'w') as fp:
        for ii in reversed(range(len(CSIAll_list))):
            if("ST" in CSIAll_list[ii]['stockname']):
                CSIAll_list.pop(ii)
                continue
            if(CSIAll_list[ii]['stockcode'][0] in ['0']):
                CSIAll_list[ii]['stock163code'] = '1' + CSIAll_list[ii]['stockcode']
            elif(CSIAll_list[ii]['stockcode'][0] in ['6']):
                CSIAll_list[ii]['stock163code'] = '0' + CSIAll_list[ii]['stockcode']
            else:
                CSIAll_list.pop(ii)
                continue
            for jj in range(len(CSI1000_list)):
                if(CSIAll_list[ii]['stockcode']==CSI1000_list[jj]['stockcode']):
                    CSIAll_list[ii]['stocktype'] = CSI1000_list[jj]['stocktype']
                    CSI1000_list.pop(jj)
                    break
            for jj in range(len(CSI500_list)):
                if(CSIAll_list[ii]['stockcode']==CSI500_list[jj]['stockcode']):
                    CSIAll_list[ii]['stocktype'] = CSI500_list[jj]['stocktype']
                    CSI500_list.pop(jj)
                    break
            for jj in range(len(HS300_list)):
                if(CSIAll_list[ii]['stockcode']==HS300_list[jj]['stockcode']):
                    CSIAll_list[ii]['stocktype'] = HS300_list[jj]['stocktype']
                    HS300_list.pop(jj)
                    break
            stockinfo = CSIAll_list[ii]['stocktype'] + "-" + CSIAll_list[ii]['stockname'] + '_' + CSIAll_list[ii]['stock163code']
            fp.write(stockinfo+"\n")


def get_163indexdata():
    index_list = ["上证指数_0000001", "深证成指_1399001"]
    isMarketOpen = False
    for stockinfo in index_list:
        indexdata_file = os.path.join(indexdata_path,'{}.csv'.format(stockinfo))
        stock163code = stockinfo.split("_")[-1]
        if(detect_163data('http://quotes.money.163.com/trade/lsjysj_zhishu_{}.html'.format(stock163code[1:]))):
            isMarketOpen = True
            if(get_163data(stock163code, start_time, end_time, indexdata_file)):
                check_stockdata(indexdata_file)
            else:
                isMarketOpen = False
        else:
            isMarketOpen = False
    return isMarketOpen


def get_stockdata():
# 获得每只股票163历史数据 & 东方财富网增减持数据
    def get_stockzjc(stockinfo):
        stockcode = stockinfo[-6:]
        zjc_title = ["股票名称", "最新价", "涨跌幅(%)", "股东名称", "增减", "方式", "变动开始日", "变动截止日", "公告日", "变动数量(万股)", "占总股本比例(%)", "占流通股比例(%)",  "持股总数(万股)", "占总股本比例", "持流通股数(万股)", "占流通股比例"]
        zjcdata_list = []
        GZiWEAqK = get_jsvar('http://data.eastmoney.com/DataCenter_V3/gdzjc.ashx?pagesize=1000&page=1&js=var%20GZiWEAqK&param=&sortRule=-1&sortType=BDJZ&tabid=all&code={}'.format(stockcode), 'GZiWEAqK')
        if(GZiWEAqK!=None):
            stockzjc_list = GZiWEAqK['data']
            if(len(stockzjc_list)!=0):
                for stockzjc in stockzjc_list:
                    stockzjcitem = stockzjc.split(',')
                    zjcdata_list.append([stockinfo]+stockzjcitem[2:6]+[stockzjcitem[8]]+stockzjcitem[13:16]+[stockzjcitem[6], stockzjcitem[16], stockzjcitem[7]]+stockzjcitem[9:13])
                write_csvfile(os.path.join(stockgdzjc_path, '{}.csv'.format(stockinfo)), zjc_title, zjcdata_list)
    with open(stockinfo_file, 'r') as fp:
        for stockinfo in fp.readlines():
            stockinfo = stockinfo.strip()
            if(stockinfo):
                stock163code = stockinfo.split("_")[-1]
                stockdata_file = os.path.join(stockdata_path,'{}.csv'.format(stockinfo))
                if(get_163data(stock163code, start_time, end_time, stockdata_file)):
                    check_stockdata(stockdata_file)
                get_stockzjc(stockinfo)


def EHBF_Analyze():
# 横盘天数 & 振幅 & EMA & MAOBV & PE & PB
    resultfile_path = os.path.join(resultdata_path, "EHBF_Analyze_Result.csv")
    title = ["股票名称", "当日涨跌幅", "获利持仓比例", "横盘天数", "平均6日振幅", "6日超跌(-6)", "12日超跌(-10)", "24日超跌(-16)", "30日跌幅", "1日换手率OBV", "6日换手率EMAOBV", "12日换手率EMAOBV", "26日换手率MEAOBV"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(EHBF_Analyze_pipeline(filename))
    try:
        df_todays = tspro.daily_basic(trade_date=end_time, fields='ts_code,pe,pe_ttm,pb,ps,ps_ttm')
        for ii in range(len(resultdata_list)):
            stockcode = resultdata_list[ii][0][-6:]
            stock_df = df_todays[df_todays.ts_code.str.contains(stockcode)]
            if(not stock_df.empty):
                stock_pb = stock_df["pb"].values[0]
                stock_pe = stock_df["pe"].values[0]
                stock_pettm = stock_df["pe_ttm"].values[0]
                stock_ps = stock_df["ps"].values[0]
                stock_psttm = stock_df["ps_ttm"].values[0]
                resultdata_list[ii] = resultdata_list[ii] + [stock_pb, stock_pe, stock_pettm, stock_ps, stock_psttm]
        title = title + ["市净率(pb)", "市盈率(pe)", "pe(TTM)", "市销率(ps)", "ps(TTM)"]
    except Exception as e:
        print(e)
    write_csvfile(resultfile_path, title, resultdata_list)
def EHBF_Analyze_par():
    resultfile_path = os.path.join(resultdata_path, "EHBF_Analyze_Result.csv")
    title = ["股票名称", "当日涨跌幅", "获利持仓比例", "横盘天数", "平均6日振幅", "6日超跌(-6)", "12日超跌(-10)", "24日超跌(-16)", "30日跌幅", "1日换手率OBV", "6日换手率EMAOBV", "12日换手率EMAOBV", "26日换手率MEAOBV"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(EHBF_Analyze_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    try:
        df_todays = tspro.daily_basic(trade_date=end_time, fields='ts_code,pe,pe_ttm,pb,ps,ps_ttm')
        for ii in range(len(resultdata_list)):
            stockcode = resultdata_list[ii][0][-6:]
            stock_df = df_todays[df_todays.ts_code.str.contains(stockcode)]
            if(not stock_df.empty):
                stock_pb = stock_df["pb"].values[0]
                stock_pe = stock_df["pe"].values[0]
                stock_pettm = stock_df["pe_ttm"].values[0]
                stock_ps = stock_df["ps"].values[0]
                stock_psttm = stock_df["ps_ttm"].values[0]
                resultdata_list[ii] = resultdata_list[ii] + [stock_pb, stock_pe, stock_pettm, stock_ps, stock_psttm]
        title = title + ["市净率(pb)", "市盈率(pe)", "pe(TTM)", "市销率(ps)", "ps(TTM)"]
    except Exception as e:
        print(e)
    write_csvfile(resultfile_path, title, resultdata_list)
def EHBF_Analyze_pipeline(filename):
    def EMA_Analyze(stockdata_list):
        closingprice = float(stockdata_list[0][3])
        EMA6 = 0
        EMA12 = 0
        EMA24 = 0
        for ii in reversed(range(min(100, len(stockdata_list)))):
            EMA6 = 2/7*float(stockdata_list[ii][3]) + 5/7*EMA6
            EMA12 = 2/13*float(stockdata_list[ii][3]) + 11/13*EMA12
            EMA24 = 2/25*float(stockdata_list[ii][3]) + 23/25*EMA24
        EMA6_range = (closingprice - EMA6) / EMA6 * 100
        EMA12_range = (closingprice - EMA12) / EMA12 * 100
        EMA24_range = (closingprice - EMA24) / EMA24 * 100
        return EMA6_range, EMA12_range, EMA24_range

    def EMAOBV_Analyze(stockdata_list):
        EMAOBV6 = 0
        EMAOBV12 = 0
        EMAOBV26 = 0
        for ii in reversed(range(min(100, len(stockdata_list)))):
            if((float(stockdata_list[ii][4])-float(stockdata_list[ii][5]))==0):
                OBV = np.sign(float(stockdata_list[ii][9])) * float(stockdata_list[ii][10])
            else:
                OBV = ((float(stockdata_list[ii][3])-float(stockdata_list[ii][5])-(float(stockdata_list[ii][4])-float(stockdata_list[ii][3])))/
                    (float(stockdata_list[ii][4])-float(stockdata_list[ii][5]))*float(stockdata_list[ii][10]))
            EMAOBV6 = EMAOBV6*5/7 + OBV*2/7
            EMAOBV12 = EMAOBV12*11/13 + OBV*2/13
            EMAOBV26 = EMAOBV26*25/27 + OBV*2/27
        return OBV, EMAOBV6, EMAOBV12, EMAOBV26

    def earnratio_Analyze(stockdata_list):
        obv_dict = {}
        closingprice = float(stockdata_list[0][3])
        upperprice = max([float(item[4]) for item in stockdata_list])
        lowerprice = min([float(item[5]) for item in stockdata_list])
        for price in [item/100 for item in range(round(lowerprice*100), round((upperprice+0.01)*100))]:
            obv_dict[price] = 0
        for ii in range(len(stockdata_list)):
            maxprice = float(stockdata_list[ii][4])
            minprice = float(stockdata_list[ii][5])
            obv = float(stockdata_list[ii][10])
            aveobv = obv/((maxprice+0.01-minprice)*100)
            for price in [item/100 for item in range(round(minprice*100), round((maxprice+0.01)*100))]:
                obv_dict[price] += aveobv
        earnobv = 0
        for price in [item/100 for item in range(round(lowerprice*100), round(closingprice*100))]:
            earnobv += obv_dict[price]
        earnratio = earnobv/sum(obv_dict.values())
        return earnratio
    
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    stablecounter = 0
    for ii in range(1, len(stockdata_list)):
        if(-0.05<=((float(stockdata_list[ii][3])-closingprice)/closingprice)<=0.05):
            stablecounter += 1
        else:
            break
    EMA6_range, EMA12_range, EMA24_range = EMA_Analyze(stockdata_list)
    OBV, EMAOBV6, EMAOBV12, EMAOBV26 = EMAOBV_Analyze(stockdata_list)
    earnratio = earnratio_Analyze(stockdata_list[:500])
    drop30_range = sum([float(item[9]) for item in stockdata_list[:min(30, len(stockdata_list))]])
    amplitude6 = np.mean([((float(item[4])-float(item[5]))/float(item[7])*100) for item in stockdata_list[:min(6, len(stockdata_list))]])
    return [stockinfo, stockdata_list[0][9], earnratio, stablecounter, amplitude6, EMA6_range, EMA12_range, EMA24_range, drop30_range, OBV, EMAOBV6, EMAOBV12, EMAOBV26]


def drop_Model_Select():
# 连续多日跌幅模型
    resultfile_path = os.path.join(resultdata_path, "drop_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续跌幅天数", "日累计总跌幅", "收盘价连续最低天数", "最低价连续最低天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(drop_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def drop_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "drop_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续跌幅天数", "日累计总跌幅", "收盘价连续最低天数", "最低价连续最低天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(drop_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def drop_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    dropcounter = 0
    droprange = 0
    for ii in range(len(stockdata_list)):
        if(float(stockdata_list[ii][9])<0):
            dropcounter += 1
            droprange += float(stockdata_list[ii][9])
        else:
            break
    closingprice = float(stockdata_list[0][3])
    leastprice = float(stockdata_list[0][5])
    closingcounter = 0
    leastcounter = 0
    for ii in range(1, len(stockdata_list)):
        if(leastprice<float(stockdata_list[ii][3])):
            leastcounter += 1
        else:
            break
    for ii in range(1, len(stockdata_list)):
        if(closingprice<float(stockdata_list[ii][3])):
            closingcounter += 1
        else:
            break
    if(dropcounter>0):
        return [stockinfo, stockdata_list[0][9], dropcounter, droprange, closingcounter, leastcounter]
    else:
        return []


def vshape_Model_Select():
# 放量上涨模型
    resultfile_path = os.path.join(resultdata_path, "vshape_Model_Select_Result.csv")
    title = ["股票名称", "百日位置(%)", "相对放量倍数", "前一日跌幅", "后一日涨幅", "前一日开盘价", "前一日收盘价", "前一日最高价", "前一日最低价", "当日开盘价", "当日收盘价", "当日最高价", "当日最低价", "前一日换手率", "后一日换手率"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(vshape_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def vshape_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "vshape_Model_Select_Result.csv")
    title = ["股票名称", "百日位置(%)", "相对放量倍数", "前一日跌幅", "后一日涨幅", "前一日开盘价", "前一日收盘价", "前一日最高价", "前一日最低价", "当日开盘价", "当日收盘价", "当日最高价", "当日最低价", "前一日换手率", "后一日换手率"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(vshape_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def vshape_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    if((float(stockdata_list[1][3])<float(stockdata_list[1][6])) and ((float(stockdata_list[0][3])>float(stockdata_list[0][6])))
        and (float(stockdata_list[0][5])<float(stockdata_list[1][3])) and (float(stockdata_list[1][9])<-3) and (float(stockdata_list[0][9])>1)
        and ((float(stockdata_list[0][10])/float(stockdata_list[1][10]))>abs(float(stockdata_list[0][9])/float(stockdata_list[1][9])))):
        maxprice = max([float(item[3]) for item in stockdata_list[:100]])
        minprice = min([float(item[3]) for item in stockdata_list[:100]])
        closingprice = float(stockdata_list[0][3])
        rebound_range = (closingprice-minprice)/(maxprice-minprice)*100
        volumn_ratio = (float(stockdata_list[0][10])/float(stockdata_list[1][10]))/abs(float(stockdata_list[0][9])/float(stockdata_list[1][9]))
        return [stockinfo, rebound_range, volumn_ratio, stockdata_list[1][9], stockdata_list[0][9], stockdata_list[1][6], stockdata_list[1][3], stockdata_list[1][4], stockdata_list[1][5], stockdata_list[0][6], stockdata_list[0][3], stockdata_list[0][4], stockdata_list[0][5], stockdata_list[1][10], stockdata_list[0][10]]
    else:
        return []


def shadow_Model_Select():
# 收下影线金针探底模型
    resultfile_path = os.path.join(resultdata_path, "shadow_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "开盘涨跌幅", "柱线幅度", "下影线幅度", "收盘价", "开盘价", "最高价", "最低价", "百日位置(%)", "换手率量比"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(shadow_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def shadow_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "shadow_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "开盘涨跌幅", "柱线幅度", "下影线幅度", "收盘价", "开盘价", "最高价", "最低价", "百日位置(%)", "换手率量比"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(shadow_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def shadow_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    maxprice = max([float(item[3]) for item in stockdata_list[:100]])
    minprice = min([float(item[3]) for item in stockdata_list[:100]])
    closingprice = float(stockdata_list[0][3])
    rebound_range = (closingprice-minprice)/(maxprice-minprice)*100
    open_range = (float(stockdata_list[0][6])-float(stockdata_list[0][7]))/float(stockdata_list[0][7])*100
    shadow_range = (min(float(stockdata_list[0][3]), float(stockdata_list[0][6]))-float(stockdata_list[0][5]))/float(stockdata_list[0][7])*100
    cylinder_range = (float(stockdata_list[0][3]) - float(stockdata_list[0][6]))/float(stockdata_list[0][7])*100
    if((float(stockdata_list[0][9])<3) and (shadow_range>3) and (float(stockdata_list[0][5])<min([float(item[3]) for item in stockdata_list[:30]]))):
        return [stockinfo, stockdata_list[0][9], round(open_range,2), round(cylinder_range,2), round(shadow_range,2), stockdata_list[0][3], stockdata_list[0][6], stockdata_list[0][4], stockdata_list[0][5], round(rebound_range, 2), round(float(stockdata_list[0][10])/float(stockdata_list[1][10]),2)]
    else:
        return []


def box_Model_Select():
# 箱体模型
    resultfile_path = os.path.join(resultdata_path, "box_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "股票下跌幅度", "股票反弹幅度", "反弹比例", "股票最高点价格", "股票最低点价格", "股票当前价格", "股票下跌天数", "股票反弹天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(box_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def box_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "box_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "股票下跌幅度", "股票反弹幅度", "反弹比例", "股票最高点价格", "股票最低点价格", "股票当前价格", "股票下跌天数", "股票反弹天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(box_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def box_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    for paratuple in [(400, 0.4), (300, 0.45), (200, 0.5), (100, 0.6), (60, 0.7), (30, 0.8)]:
        closingprice_list = [float(item[3]) for item in stockdata_list[:(min(len(stockdata_list), paratuple[0]))]]
        maxprice = max(closingprice_list)
        max_offset = closingprice_list.index(maxprice)
        minprice = min(closingprice_list)
        min_offset = closingprice_list.index(minprice)
        if((min_offset>2) and (min_offset<max_offset) and (minprice<paratuple[1]*maxprice)):
            fail_range = (minprice-maxprice)/maxprice*100
            rebound_range = (closingprice-minprice)/maxprice*100
            return [stockinfo, stockdata_list[0][9], fail_range, rebound_range, abs(rebound_range/fail_range), maxprice, minprice, stockdata_list[0][3], (max_offset-min_offset), min_offset]
        else:
            return []


def volumn_Model_Select():
# 放量模型
    resultfile_path = os.path.join(resultdata_path, "volumn_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "放量倍数", "5日总涨跌幅", "10日总涨跌幅", "30日总涨跌幅", "当前价格", "百日最高价", "百日最低价"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(volumn_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def volumn_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "volumn_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "放量倍数", "5日总涨跌幅", "10日总涨跌幅", "30日总涨跌幅", "当前价格", "百日最高价", "百日最低价"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(volumn_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def volumn_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    volumn_ratio = float(stockdata_list[0][10])/float(stockdata_list[1][10])
    if(volumn_ratio>2):
        drop5_range = sum([float(item[9]) for item in stockdata_list[:min(5, len(stockdata_list))]])
        drop10_range = sum([float(item[9]) for item in stockdata_list[:min(10, len(stockdata_list))]])
        drop30_range = sum([float(item[9]) for item in stockdata_list[:min(30, len(stockdata_list))]])
        max100_price = max([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        min100_price = min([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        return [stockinfo, stockdata_list[0][9], volumn_ratio, drop5_range, drop10_range, drop30_range, stockdata_list[0][3], max100_price, min100_price]
    else:
        return []


def trend_Model_Select():
# K线图 日线 贯穿 5日线 	可拓展为 N1日线 贯穿 N2日线
    resultfile_path = os.path.join(resultdata_path, "trend_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "日线上穿5日线预测天数", "5日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "trend_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "日线上穿5日线预测天数", "5日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trend_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    MA1_list = []
    MA5_list = []
    DIFF_list = []
    if(len(stockdata_list)<130):
        return []
    for ii in range(100):
        MA1_list.append(float(stockdata_list[ii][3]))
        MA5_list.append(np.mean([float(item[3]) for item in stockdata_list[ii:ii+5]]))
        DIFF_list.append(MA1_list[ii] - MA5_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1]) and (float(stockdata_list[0][3])>MA5_list[0])):
        trend_counter = 1
        for ii in range(1, len(DIFF_list)):
            if(DIFF_list[ii]<0):
                trend_counter += 1
            else:
                break
        trend_range = (float(stockdata_list[0][3])-float(stockdata_list[trend_counter][3]))/float(stockdata_list[trend_counter][3])*100
        trend_predict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        cross_price = round(sum([float(item[3]) for item in stockdata_list[:4]])/4, 2)
        parallel_price = round((5*DIFF_list[-1]/4+cross_price), 2)
        return [stockinfo, stockdata_list[0][9], trend_predict, trend_counter, trend_range, stockdata_list[0][3], cross_price, parallel_price]
    else:
        return []


def trend5_Model_Select():
# K线图 5日线 贯穿 10日线 	可拓展为 N1日线 贯穿 N2日线
    resultfile_path = os.path.join(resultdata_path, "trend5_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "5日线上穿10日线预测天数", "10日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend5_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "trend5_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "5日线上穿10日线预测天数", "10日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend5_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trend5_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    MA5_list = []
    MA10_list = []
    DIFF_list = []
    if(len(stockdata_list)<130):
        return []
    for ii in range(100):
        MA5_list.append(np.mean([float(item[3]) for item in stockdata_list[ii:ii+5]]))
        MA10_list.append(np.mean([float(item[3]) for item in stockdata_list[ii:ii+10]]))
        DIFF_list.append(MA5_list[ii] - MA10_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1]) and (float(stockdata_list[0][3])>MA10_list[0])):
        trend_counter = 1
        for ii in range(1, len(DIFF_list)):
            if(DIFF_list[ii]<0):
                trend_counter += 1
            else:
                break
        trend_range = (float(stockdata_list[0][3])-float(stockdata_list[trend_counter][3]))/float(stockdata_list[trend_counter][3])*100
        trend_predict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        cross_price = round(sum([float(item[3]) for item in stockdata_list[:9]])-2*sum([float(item[3]) for item in stockdata_list[:4]]), 2)
        parallel_price = round((10*DIFF_list[-1]+cross_price), 2)
        return [stockinfo, stockdata_list[0][9], trend_predict, trend_counter, trend_range, stockdata_list[0][3], cross_price, parallel_price]
    else:
        return []


def trend10_Model_Select():
# K线图 10日线 贯穿 30日线 	可拓展为 N1日线 贯穿 N2日线
    resultfile_path = os.path.join(resultdata_path, "trend10_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "10日线上穿30日线预测天数", "30日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend10_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "trend10_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "10日线上穿30日线预测天数", "30日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend10_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trend10_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    MA10_list = []
    MA30_list = []
    DIFF_list = []
    if(len(stockdata_list)<130):
        return []
    for ii in range(100):
        MA10_list.append(np.mean([float(item[3]) for item in stockdata_list[ii:ii+10]]))
        MA30_list.append(np.mean([float(item[3]) for item in stockdata_list[ii:ii+30]]))
        DIFF_list.append(MA10_list[ii] - MA30_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1]) and (float(stockdata_list[0][3])>MA30_list[0])):
        trend_counter = 1
        for ii in range(1, len(DIFF_list)):
            if(DIFF_list[ii]<0):
                trend_counter += 1
            else:
                break
        trend_range = (float(stockdata_list[0][3])-float(stockdata_list[trend_counter][3]))/float(stockdata_list[trend_counter][3])*100
        trend_predict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        cross_price = round((sum([float(item[3]) for item in stockdata_list[:29]])-3*sum([float(item[3]) for item in stockdata_list[:9]]))/2, 2)
        parallel_price = round((15*DIFF_list[-1]+cross_price), 2)
        return [stockinfo, stockdata_list[0][9], trend_predict, trend_counter, trend_range, stockdata_list[0][3], cross_price, parallel_price]
    else:
        return []


def KDJ_Model_Select():
# KDJ 模型
    resultfile_path = os.path.join(resultdata_path, "KDJ_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "预测金叉天数", "KDJ下方天数", "上穿前总跌幅", "当前价格", "预测交叉价格", "KDJ斜率", "K值", "D值", "J值", "RSV"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(KDJ_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJ_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "KDJ_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "预测金叉天数", "KDJ下方天数", "上穿前总跌幅", "当前价格", "预测交叉价格", "KDJ斜率", "K值", "D值", "J值", "RSV"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(KDJ_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJ_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    K_list = [50]
    D_list = [50]
    J_list = [50]
    KDJ_list = [0]
    RSV = 0
    C9 = 0
    L9 = 0
    H9 = 0
    for ii in reversed(range(min(100, len(stockdata_list)-9))):
        C9 = float(stockdata_list[ii][3])
        L9 = min([float(stockdata_list[jj][5]) for jj in range(ii,ii+9)])
        H9 = max([float(stockdata_list[jj][4]) for jj in range(ii,ii+9)])
        if(H9==L9):
            RSV = 50
        else:
            RSV = (C9-L9)/(H9-L9)*100
        K = 2/3*K_list[-1]+1/3*RSV
        D = 2/3*D_list[-1]+1/3*K
        J = 3*K-2*D
        K_list.append(K)
        D_list.append(D)
        J_list.append(J)
        KDJ_list.append(K-D)
    if((KDJ_list[-2]<0) and (KDJ_list[-1]>KDJ_list[-2])):
        KDJ_counter = 1
        for ii in reversed(range(len(KDJ_list)-1)):
            if(KDJ_list[ii]<0):
                KDJ_counter += 1
            else:
                break
        KDJ_range = (float(stockdata_list[0][3])-float(stockdata_list[KDJ_counter-1][3]))/float(stockdata_list[KDJ_counter-1][3])*100
        KDJ_predict = math.ceil(KDJ_list[-1]/(KDJ_list[-2]-KDJ_list[-1]))
        K_price = round((H9-L9)*K_list[-1]/100+L9, 2)
        KDJ_slope = ((K_list[-1]-D_list[-1])-(K_list[-2]-D_list[-2]))/((K_list[-1]+D_list[-1])/2)
        return [stockinfo, stockdata_list[0][9], KDJ_predict, KDJ_counter, KDJ_range, stockdata_list[0][3], K_price, KDJ_slope, K_list[-1], D_list[-1], J_list[-1], RSV]
    else:
        return []


def MACDDIFF_Model_Select():
# MACD 模型 (12,26,9) & 中间量 DIFF 模型
    resultfile_path1 = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFF_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格", "MACD不变预测价格"]
    title2 = ["股票名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF不变预测价格"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        MACD_result, DIFF_result = MACDDIFF_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def MACDDIFF_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格", "MACD不变预测价格"]
    resultfile_path2 = os.path.join(resultdata_path, "DIFF_Model_Select_Result.csv")
    title2 = ["股票名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF不变预测价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFF_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def MACDDIFF_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    EMA12 = 0
    EMA26 = 0
    DIFF_list = [0]
    DEA9_list = [0]
    MACD_list = [0]
    MACD_result = []
    DIFF_result = []
    for ii in reversed(range(min(100, len(stockdata_list)))):
        EMA12 = 11/13*EMA12 + 2/13*float(stockdata_list[ii][3])
        EMA26 = 25/27*EMA26 + 2/27*float(stockdata_list[ii][3])
        DIFF = EMA12 - EMA26
        DEA9 = 8/10*DEA9_list[-1] + 2/10*DIFF
        MACD = (DIFF-DEA9)*2
        DIFF_list.append(DIFF)
        DEA9_list.append(DEA9)
        MACD_list.append(MACD)
    if((MACD_list[-2]<0) and (MACD_list[-1]>MACD_list[-2]) and (DEA9_list[-2]<0)):
        MACD_counter = 1
        for ii in reversed(range(len(MACD_list)-1)):
            if((MACD_list[ii]<0) or (DIFF_list[ii]<0)):
                MACD_counter+=1
            else:
                break
        MACD_range = (float(stockdata_list[0][3])-float(stockdata_list[MACD_counter-1][3]))/float(stockdata_list[MACD_counter-1][3])*100
        MACD_predict = math.ceil(MACD_list[-1]/(MACD_list[-2]-MACD_list[-1]))
        cross_price = (DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
        parallel_price = (5/8*MACD+DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
        MACD_slope = (MACD_list[-1]-MACD_list[-2])/float(stockdata_list[0][3])
        DEA_ratio = DEA9_list[-1]/float(stockdata_list[0][3])
        MACD_result = [stockinfo, stockdata_list[0][9], MACD_predict, MACD_counter, DEA_ratio, MACD_range, MACD_slope, stockdata_list[0][3], round(cross_price,2), round(parallel_price,2)]
    if((DIFF_list[-2]<0) and (DIFF_list[-1]>DIFF_list[-2])):
        DIFF_counter = 1
        for ii in reversed(range(len(DIFF_list)-1)):
            if(DIFF_list[ii]<0):
                DIFF_counter+=1
            else:
                break
        DIFF_predict = math.ceil(DIFF_list[-1]/(DIFF_list[-2]-DIFF_list[-1]))
        cross_price = (25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        parallel_price = (DIFF_list[-1]+25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        DIFF_slope = (DIFF_list[-1]-DIFF_list[-2])/float(stockdata_list[0][3])
        DEA_ratio = DEA9_list[-1]/float(stockdata_list[0][3])
        DIFF_ratio = DIFF_list[-1]/DEA9_list[-1]
        DIFF_result = [stockinfo, stockdata_list[0][9], DIFF_predict, DIFF_counter, round(DIFF_ratio,2), DEA_ratio, DIFF_slope, stockdata_list[0][3], round(cross_price, 2), round(parallel_price, 2)]
    return MACD_result, DIFF_result


def obv_Model_Select():
# OBV模型+多空净额比率法修正+MACD 模型 & DIFF 模型
    resultfile_path1 = os.path.join(resultdata_path, "obv_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算obvMACD贯穿天数", "obvMACD下方天数", "上穿前总跌幅", "5日obv", "10日obv", "30日obv"]
    resultfile_path2 = os.path.join(resultdata_path, "obvDIFF_Model_Select_Result.csv")
    title2 = ["股票名称", "当日涨跌幅", "估算obvMACD贯穿天数", "obvMACD下方天数", "上穿前总跌幅", "5日obv", "10日obv", "30日obv"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        OBVMACD_result, OBVDIFF_result = obv_Model_Select_pipeline(filename)
        resultdata_list1.append(OBVMACD_result)
        resultdata_list2.append(OBVDIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def obv_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "obvMACD_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算obvMACD贯穿天数", "obvMACD下方天数", "上穿前总跌幅", "5日obv", "10日obv", "30日obv"]
    resultfile_path2 = os.path.join(resultdata_path, "obvDIFF_Model_Select_Result.csv")
    title2 = ["股票名称", "当日涨跌幅", "估算obvMACD贯穿天数", "obvMACD下方天数", "上穿前总跌幅", "5日obv", "10日obv", "30日obv"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(obv_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def obv_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    OBVEMA12 = 0
    OBVEMA26 = 0
    OBV_list = [0]
    OBVDIFF_list = [0]
    OBVDEA9_list = [0]
    OBVMACD_list = [0]
    OBVMACD_result = []
    OBVDIFF_result = []
    for ii in reversed(range(min(100, len(stockdata_list)))):
        if((float(stockdata_list[ii][4])-float(stockdata_list[ii][5]))==0):
            OBV = np.sign(float(stockdata_list[ii][9])) * float(stockdata_list[ii][10])
        else:
            OBV = ((float(stockdata_list[ii][3])-float(stockdata_list[ii][5])-(float(stockdata_list[ii][4])-float(stockdata_list[ii][3])))/
                (float(stockdata_list[ii][4])-float(stockdata_list[ii][5]))*float(stockdata_list[ii][10]))
        OBVEMA12 = 11/13*OBVEMA12 + 2/13*OBV
        OBVEMA26 = 25/27*OBVEMA26 + 2/27*OBV
        OBVDIFF = OBVEMA12 - OBVEMA26
        OBVDEA9 = 8/10*OBVDEA9_list[-1] + 2/10*OBVDIFF
        OBVMACD = (OBVDIFF-OBVDEA9)*2
        OBV_list.append(OBV)
        OBVDIFF_list.append(OBVDIFF)
        OBVDEA9_list.append(OBVDEA9)
        OBVMACD_list.append((OBVDIFF-OBVDEA9)*2)
    if((OBVMACD_list[-2]<0) and (OBVMACD_list[-1]>OBVMACD_list[-2]) and (OBVDEA9_list[-2]<0)):
        OBVMACD_counter = 1
        for ii in reversed(range(len(OBVMACD_list)-1)):
            if((OBVMACD_list[ii]<0) or (OBVDIFF_list[ii]<0)):
                OBVMACD_counter+=1
            else:
                break
        OBVMACD_range = (float(stockdata_list[0][3])-float(stockdata_list[OBVMACD_counter-1][3]))/float(stockdata_list[OBVMACD_counter-1][3])*100
        OBVMACD_predict = math.ceil(OBVMACD_list[-1]/(OBVMACD_list[-2]-OBVMACD_list[-1]))
        OBV5 = sum(OBV_list[-5:])
        OBV10 = sum(OBV_list[-10:])
        OBV30 = sum(OBV_list[-30:])
        OBVMACD_result = [stockinfo, stockdata_list[0][9], OBVMACD_predict, OBVMACD_counter, OBVMACD_range, OBV5, OBV10, OBV30]
    if((OBVDIFF_list[-2]<0) and (OBVDIFF_list[-1]>OBVDIFF_list[-2])):
        OBVDIFF_counter = 1
        for ii in reversed(range(len(OBVDIFF_list)-1)):
            if(OBVDIFF_list[ii]<0):
                OBVDIFF_counter+=1
            else:
                break
        OBVDIFF_range = (float(stockdata_list[0][3])-float(stockdata_list[OBVDIFF_counter-1][3]))/float(stockdata_list[OBVDIFF_counter-1][3])*100
        OBVDIFF_predict = math.ceil(OBVDIFF_list[-1]/(OBVDIFF_list[-2]-OBVDIFF_list[-1]))
        OBVDIFF_result = [stockinfo, stockdata_list[0][9], OBVDIFF_predict, OBVDIFF_counter, OBVDIFF_range, sum(OBV_list[-5:]), sum(OBV_list[-10:]), sum(OBV_list[-30:])]
    return OBVMACD_result, OBVDIFF_result


def similar_Model_Select():
# K 线相似度比较
    resultfile_path = os.path.join(resultdata_path, "similar_Model_Select_Result.csv")
    title = ["股票名称", "当前股票最大相似度", "当前未来五日涨跌幅", "当前相似日期", "所有股票最大相似度", "所有未来五日涨跌幅", "相似股票名称", "相似日期", "当前未来1日预测", "当前未来2日预测", "当前未来3日预测", "当前未来4日预测", "当前未来5日预测", "所有未来1日预测", "所有未来2日预测", "所有未来3日预测", "所有未来4日预测", "所有未来5日预测"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(similar_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def similar_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "similar_Model_Select_Result.csv")
    title = ["股票名称", "当前股票最大相似度", "当前未来五日涨跌幅", "当前相似日期", "所有股票最大相似度", "所有未来五日涨跌幅", "相似股票名称", "相似日期", "当前未来1日预测", "当前未来2日预测", "当前未来3日预测", "当前未来4日预测", "当前未来5日预测", "所有未来1日预测", "所有未来2日预测", "所有未来3日预测", "所有未来4日预测", "所有未来5日预测"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(similar_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def similar_Model_Select_pipeline(filename):
    def pearson_r(a, b):
        if(len(a)==len(b)):
            dims = len(a)
            denominator = (sum([ii**2 for ii in a])-sum(a)**2/dims)*(sum([ii**2 for ii in b])-sum(b)**2/dims)
#            denominator = (sum(np.multiply(np.array(a),np.array(a)))-sum(a)**2/dims)*(sum(np.multiply(np.array(b),np.array(b)))-sum(b)**2/dims)
            if(denominator<=0):
                return 0
            else:
                return (sum([a[ii]*b[ii] for ii in range(dims)])-sum(a)*sum(b)/dims)/math.sqrt(denominator)
#                return (sum(np.multiply(np.array(a),np.array(b)))-sum(a)*sum(b)/dims)/math.sqrt(denominator)
        else:
            return 0
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    selfsimidate = ""
    if(len(stockdata_list)<100):
        return []
    ref_list = [float(item[3]) for item in stockdata_list[:30]]
    maxselfsimidegree = 0
    selfprerange = 0
    selfprerange_list = [0, 0, 0, 0, 0]
    for ii in range(75, min(125, len(stockdata_list)-30)):
        closingprice_list = [float(item[3]) for item in stockdata_list[ii:(ii+30)]]
        simidegree = pearson_r(closingprice_list,ref_list)
        if(simidegree>maxselfsimidegree):
            maxselfsimidegree = simidegree
            selfsimidate = stockdata_list[ii][0]
            selfprerange_list = list(reversed([float(item[9]) for item in stockdata_list[(ii-5):ii]]))
            selfprerange = sum(selfprerange_list)
    maxallsimidegree = 0
    allprerange = 0
    allprerange_list = [0, 0, 0, 0, 0]
    allsimidate = ""
    simistockinfo = ""
    filename2_list = os.listdir(stockdata_path)
    filename2_list.remove(filename)
    for filename2 in filename2_list:
        if(filename2.split('-')[0]!=filename.split('-')[0]):
            continue
        _, stockdata2_list = read_csvfile(os.path.join(stockdata_path, filename2))
        if(len(stockdata2_list)<100):
            continue
        for ii in range(5, 10):
            closingprice_list = [float(item[3]) for item in stockdata2_list[ii:(ii+30)]]
            simidegree = pearson_r(closingprice_list, ref_list)
            if(simidegree>maxallsimidegree):
                maxallsimidegree = simidegree
                simistockinfo = filename2.split(".")[0]
                allsimidate = stockdata2_list[ii][0]
                allprerange_list = list(reversed([float(item[9]) for item in stockdata2_list[(ii-5):ii]])) 
                allprerange = sum(allprerange_list)
    return [stockinfo, maxselfsimidegree, selfprerange, selfsimidate, maxallsimidegree, allprerange, simistockinfo, allsimidate] + selfprerange_list + allprerange_list


def lagging_Model_Select():
# 与指数 相比滞后幅度
    index_list = ["上证指数_0000001", "深证成指_1399001"]
    indexfile_list = [os.path.join(indexdata_path, (item+".csv")) for item in index_list]
    resultfile_path = os.path.join(resultdata_path, "lagging_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "股票总涨跌幅", "指数总涨跌幅", "股票总滞后幅", "股票滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "100日总滞后幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(lagging_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def lagging_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "lagging_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "股票总涨跌幅", "指数总涨跌幅", "股票总滞后幅", "股票滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(lagging_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def lagging_Model_Select_pipeline(filename):
    index_list = ["上证指数_0000001", "深证成指_1399001"]
    indexfile_list = [os.path.join(indexdata_path, (item+".csv")) for item in index_list]
    stockinfo = filename.split(".")[0]
    if(stockinfo.split("_")[-1][0]=="0"):
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
    lagging30_range = 0
    lagging30_counter = 0
    for ii in range(min(30, len(stockdata_list))):
        if(float(indexdata_list[ii][9])>float(stockdata_list[ii][9])):
             lagging30_counter += 1
        lagging30_range += float(indexdata_list[ii][9]) - float(stockdata_list[ii][9])
    lagging60_range = 0
    lagging60_counter = 0
    for ii in range(min(60, len(stockdata_list))):
        if(float(indexdata_list[ii][9])>float(stockdata_list[ii][9])):
             lagging60_counter += 1
        lagging60_range += float(indexdata_list[ii][9]) - float(stockdata_list[ii][9])
    lagging100_range = 0
    lagging100_counter = 0
    for ii in range(min(100, len(stockdata_list))):
        if(float(indexdata_list[ii][9])>float(stockdata_list[ii][9])):
             lagging100_counter += 1
        lagging100_range += float(indexdata_list[ii][9]) - float(stockdata_list[ii][9])
    return [stockinfo, stockdata_list[0][9], stock_range, index_range, lagging_range, lagging_counter, lagging30_range, lagging30_counter, lagging60_range, lagging60_counter, lagging100_range, lagging100_counter]
    

def AHCom_Model_Select():
# A股&H股 相比滞后幅度
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
        resultfile_path = os.path.join(resultdata_path, "AHCom_Model_Select_Result.csv")
        title = ["股票名称", "H股名称", "股票滞后天数", "当日A股涨跌幅", "A股连续涨跌幅", "H股连续涨跌幅", "A股连续滞后幅", "30日总滞后幅"]
        resultdata_list = []
        for filename in os.listdir(AHdata_path):
            _, AHdata_list = read_csvfile(os.path.join(AHdata_path, filename))
            stockinfo = filename.split(".")[0]
            stockHinfo = (str(AHdata_list[-1][7])+"_"+str(AHdata_list[-1][6]).format(5))
            AStock_range = 0
            HStock_range = 0
            AHCom_range = 0
            AHComCounter = 0
            for ii in reversed(range(len(AHdata_list))):
                if(float(AHdata_list[ii][5])<float(AHdata_list[ii][9])):
                    AHComCounter += 1
                    AStock_range += float(AHdata_list[ii][5])
                    HStock_range += float(AHdata_list[ii][9])
                    AHCom_range += float(AHdata_list[ii][9]) - float(AHdata_list[ii][5])
                else:
                    break
            AHCom30_range = 0
            for ii in reversed(range(min(30, len(AHdata_list)))):
                AHCom30_range += float(AHdata_list[ii][9]) - float(AHdata_list[ii][5])
            resultdata_list.append([stockinfo, stockHinfo, AHComCounter, AHdata_list[-1][5], AStock_range, HStock_range, AHCom_range, AHCom30_range])
        write_csvfile(resultfile_path, title, resultdata_list)


def ABCom_Model_Select():
# A股&B股 相比滞后幅度
    ABdata_path = os.path.join(root_path, "Data", "AB_stock_data")
    ABdataHistory_path = os.path.join(root_path, "Data", "AB_stock_data_history")
    def get_ABdata():
        AB_url = "http://quotes.money.163.com/hs/realtimedata/service/ab.php?host=/hs/realtimedata/service/ab.php&page=0&query=AB:_exists_;VOLUME:_exists_&fields=NAME,PRICE,SYMBOL,AB,PERCENT,VOLUME,CODE&sort=AB.A_PERCENT&order=desc&count=500&type=query"
        ABhistory_title = ["A股名称", "A股代码", "A股查询代码", "A股价格", "A股涨跌幅", "B股代码", "B股查询代码", "B股名称", "B股价格", "B股涨跌幅", "B/A成交量比", "B股溢价率(溢价率=(B股价格*0.8545-A股价格)/A股价格*100%)"]
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
                if(not IsBDataChange):
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
        resultfile_path = os.path.join(resultdata_path, "ABCom_Model_Select_Result.csv")
        title = ["股票名称", "B股名称", "股票滞后天数", "当日A股涨跌幅", "A股连续涨跌幅", "B股连续涨跌幅", "A股连续滞后幅", "30日总滞后幅"]
        resultdata_list = []
        for filename in os.listdir(ABdata_path):
            _, ABdata_list = read_csvfile(os.path.join(ABdata_path, filename))
            stockinfo = filename.split(".")[0]
            stockBinfo = (str(ABdata_list[-1][8])+"_"+str(ABdata_list[-1][7]).format(6))
            AStock_range = 0
            BStock_range = 0
            ABCom_range = 0
            ABComCounter = 0
            for ii in reversed(range(len(ABdata_list))):
                if(float(ABdata_list[ii][5])<float(ABdata_list[ii][10])):
                    ABComCounter += 1
                    AStock_range += float(ABdata_list[ii][5])
                    BStock_range += float(ABdata_list[ii][10])
                    ABCom_range += float(ABdata_list[ii][10]) - float(ABdata_list[ii][5])
                else:
                    break
            ABCom30_range = 0
            for ii in reversed(range(min(30, len(ABdata_list)))):
                ABCom30_range += float(ABdata_list[ii][10]) - float(ABdata_list[ii][5])
            resultdata_list.append([stockinfo, stockBinfo, ABComCounter, ABdata_list[-1][5], AStock_range, BStock_range, ABCom_range, ABCom30_range])
        write_csvfile(resultfile_path, title, resultdata_list)


def margin_Model_Select():
# 融资融券标的
    margin_url = "http://stock.jrj.com.cn/action/rzrq/getTransDetailByTime.jspa?vname=detailData&day=1&havingType=1,2&page=1&psize=10000&sort=buy_sell_balance"
    marginData_list = []
    detailData = get_jsvar(margin_url, 'detailData')
    if(detailData!=None):
        marginData_list = detailData['data']
    if(len(marginData_list)==0):
        return
    resultfile_path = os.path.join(resultdata_path, "margin_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "融资买入比", "融资净买入比", "融券卖出比", "融券净卖出比"]
    resultdata_list = []
    for marginData in marginData_list:
        stockcode = marginData[0]
        stock_name = marginData[1]
        stockinfo = stock_name+"_"+stockcode
        rzye = float(marginData[2])
        zltszb = float(marginData[3])
        rzmre = float(marginData[4])
        zcjeb = float(marginData[5])
        rzche = float(marginData[6])
        rqyl = float(marginData[7])
        rqmcl = float(marginData[8])
        rqchl = float(marginData[9])
        rzrqye = float(marginData[10])
        rzrqce = float(marginData[11])
        rqylltb = float(marginData[13])
        if(rzye==0):
            rzmrb = 0
            rzjmrb = 0
        else:
            rzmrb = rzmre/rzye
            rzjmrb = (rzmre-rzche)/rzye
        if(rqyl==0):
            rqmcb = 0
            rqjmcb = 0
        else:
            rqmcb = rqmcl/rqyl
            rqjmcb = (rqmcl-rqchl)/rqyl
        pct_chg = 0
        filenames = os.listdir(stockdata_path)
        for filename in filenames:
            if(stockcode==filename.split(".")[0][-6:]):
                _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
                pct_chg = float(stockdata_list[0][9])
                break
        resultdata_list.append([stockinfo, pct_chg, rzmrb, rzjmrb, rqmcb, rqjmcb])
    write_csvfile(resultfile_path, title, resultdata_list)


def gdzjc_Model_Select():
# 股东增减持股票信息汇总
    resultfile_path = os.path.join(resultdata_path, "gdzjc_Model_Select_Result.csv")
    title = ["股票名称", "最新价", "涨跌幅(%)", "股东名称", "增减", "方式", "变动开始日", "变动截止日", "公告日", "变动数量(万股)", "占总股本比例(%)", "占流通股比例(%)",  "持股总数(万股)", "占总股本比例", "持流通股数(万股)", "占流通股比例"]
    resultdata_list = []
    for filename in os.listdir(stockgdzjc_path):
        _, stockzjcdata_list = read_csvfile(os.path.join(stockgdzjc_path, filename))
        stockinfo = filename.split(".")[0]
        if(len(stockzjcdata_list)>0):
            resultdata_list.append(stockzjcdata_list[0])
    write_csvfile(resultfile_path, title, resultdata_list)


def repurchase_Model_Select():
# 股票回购信息汇总
    resultfile_path = os.path.join(resultdata_path, "repurchase_Model_Select_Result.csv")
    title = ["股票代码", "公告日期", "截止日期", "进度", "过期日期", "回购数量", "回购金额", "回购最高价", "回购最低价"]
    resultdata_list = []
    df_repurchase = tspro.repurchase(ann_date="")
    for item in df_repurchase.values:
        if(item[0][:3]!="300"):
            resultdata_list.append(list(item))
    write_csvfile(resultfile_path, title, resultdata_list)

def get_MonthData(stockdata_list):
    monthstr = ""
    monthoffset_list = []
    for ii in range(len(stockdata_list)):
        if(stockdata_list[ii][0].split("-")[1]!=monthstr):
            monthstr = stockdata_list[ii][0].split("-")[1]
            monthoffset_list.append(ii)
    monthclosingprice_list = [float(stockdata_list[offset][3]) for offset in monthoffset_list]
    monthoffset_list.append(len(stockdata_list))
    monthmaxprice_list = [max([float(stockdata_list[jj][4]) for jj in range(monthoffset_list[ii],monthoffset_list[ii+1])]) for ii in range(len(monthoffset_list)-1)]
    monthminprice_list = [min([float(stockdata_list[jj][5]) for jj in range(monthoffset_list[ii],monthoffset_list[ii+1])]) for ii in range(len(monthoffset_list)-1)]
    return monthclosingprice_list, monthmaxprice_list, monthminprice_list


def dropMonth_Model_Select():
# 月连续跌幅
    resultfile_path = os.path.join(resultdata_path, "dropMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "连续跌幅月数", "月累计总跌幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(dropMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def dropMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "dropMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "连续跌幅月数", "月累计总跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(dropMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def dropMonth_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
    monthdropcounter = 0
    for ii in range(1, len(monthclosingprice_list)-1):
        if(monthclosingprice_list[ii]<=monthclosingprice_list[ii+1]):
            monthdropcounter += 1
        else:
            break
    if(monthdropcounter>0):
        monthdroprange = (monthclosingprice_list[1]-monthclosingprice_list[monthdropcounter+1])/monthclosingprice_list[monthdropcounter+1]*100
        return [stockinfo, month_range, monthdropcounter, monthdroprange]
    else:
        return []


def KDJMonth_Model_Select():
# 月 KDJ 模型
    resultfile_path = os.path.join(resultdata_path, "KDJMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "预测金叉月数", "KDJ下方月数", "上穿前总跌幅", "当前价格", "预测交叉价格", "KDJ斜率", "K值", "D值", "J值", "RSV"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(KDJMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "KDJMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "预测金叉月数", "KDJ下方月数", "上穿前总跌幅", "当前价格", "预测交叉价格", "KDJ斜率", "K值", "D值", "J值", "RSV"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(KDJMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJMonth_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    if(len(monthclosingprice_list)<12):
        return []
    K_list = [50]
    D_list = [50]
    J_list = [50]
    KDJ_list = [0]
    RSV = 0
    C9 = 0
    L9 = 0
    H9 = 0
    for ii in reversed(range(min(100, len(monthclosingprice_list)-9))):
        C9 = monthclosingprice_list[ii]
        H9 = max([monthmaxprice_list[jj] for jj in range(ii,ii+9)])
        L9 = min([monthminprice_list[jj] for jj in range(ii,ii+9)])
        RSV = (C9-L9)/(H9-L9)*100
        K = 2/3*K_list[-1]+1/3*RSV
        D = 2/3*D_list[-1]+1/3*K
        J = 3*K-2*D
        K_list.append(K)
        D_list.append(D)
        J_list.append(J)
        KDJ_list.append(K-D)
    if((KDJ_list[-2]<0) and (KDJ_list[-1]>KDJ_list[-2])):
        KDJ_counter = 1
        for ii in reversed(range(len(KDJ_list)-1)):
            if(KDJ_list[ii]<0):
                KDJ_counter += 1
            else:
                break
        KDJ_range = (monthclosingprice_list[0]-monthclosingprice_list[KDJ_counter-1])/monthclosingprice_list[KDJ_counter-1]*100
        KDJ_predict = round(KDJ_list[-1]/(KDJ_list[-2]-KDJ_list[-1]), 2)
        K_price = round((H9-L9)*K_list[-1]/100+L9, 2)
        KDJ_slope = ((K_list[-1]-D_list[-1])-(K_list[-2]-D_list[-2]))/((K_list[-1]+D_list[-1])/2)
        month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
        return [stockinfo, month_range, KDJ_predict, KDJ_counter, KDJ_range, monthclosingprice_list[0], K_price, KDJ_slope, K_list[-1], D_list[-1], J_list[-1], RSV]
    else:
        return []


def MACDDIFFMonth_Model_Select():
# MACD 模型 (12,26,9)
    resultfile_path1 = os.path.join(resultdata_path, "MACDMonth_Model_Select_Result.csv")
    title1 = ["股票名称", "当月涨跌幅", "估算MACD贯穿月数", "MACD下方月数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格", "MACD不变预测价格"]
    resultfile_path2 = os.path.join(resultdata_path, "DIFFMonth_Model_Select_Result.csv")
    title2 = ["股票名称", "当月涨跌幅", "估算DIFF贯穿月数", "DIFF下方月数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF不变预测价格"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        MACD_result, DIFF_result = MACDDIFFMonth_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def MACDDIFFMonth_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "MACDMonth_Model_Select_Result.csv")
    title1 = ["股票名称", "当月涨跌幅", "估算MACD贯穿月数", "MACD下方月数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格", "MACD不变预测价格"]
    resultfile_path2 = os.path.join(resultdata_path, "DIFFMonth_Model_Select_Result.csv")
    title2 = ["股票名称", "当月涨跌幅", "估算DIFF贯穿月数", "DIFF下方月数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF不变预测价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFFMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def MACDDIFFMonth_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    if(len(monthclosingprice_list)<12):
        return [], []
    EMA12 = 0
    EMA26 = 0
    DIFF_list = [0]
    DEA9_list = [0]
    MACD_list = [0]
    MACD_result = []
    DIFF_result = []
    for ii in reversed(range(min(100, len(monthclosingprice_list)))):
        EMA12 = 11/13*EMA12 + 2/13*monthclosingprice_list[ii]
        EMA26 = 25/27*EMA26 + 2/27*monthclosingprice_list[ii]
        DIFF = EMA12 - EMA26
        DEA9 = 8/10*DEA9_list[-1] + 2/10*DIFF
        MACD = (DIFF-DEA9)*2
        DIFF_list.append(DIFF)
        DEA9_list.append(DEA9)
        MACD_list.append(MACD)
    if((MACD_list[-2]<0) and (MACD_list[-1]>MACD_list[-2])):
        MACD_counter = 1
        for ii in reversed(range(len(MACD_list)-1)):
            if((MACD_list[ii]<0) or (DIFF_list[ii]<0)):
                MACD_counter+=1
            else:
                break
        MACD_range = (monthclosingprice_list[0]-monthclosingprice_list[MACD_counter-1])/monthclosingprice_list[MACD_counter-1]*100
        MACD_predict = round(MACD_list[-1]/(MACD_list[-2]-MACD_list[-1]), 2)
        cross_price = round((DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27), 2)
        parallel_price = round((5/8*MACD+DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27), 2)
        MACD_slope = (MACD_list[-1]-MACD_list[-2])/monthclosingprice_list[0]
        month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
        DEA_ratio = DEA9_list[-1]/monthclosingprice_list[0]
        MACD_result = [stockinfo, month_range, MACD_predict, MACD_counter, DEA_ratio, MACD_range, MACD_slope, monthclosingprice_list[0], cross_price, parallel_price]
    if((DIFF_list[-2]<0) and (DIFF_list[-1]>DIFF_list[-2])):
        DIFF_counter = 1
        for ii in reversed(range(len(DIFF_list)-1)):
            if(DIFF_list[ii]<0):
                DIFF_counter+=1
            else:
                break
        DIFF_predict = DIFF_list[-1]/(DIFF_list[-2]-DIFF_list[-1])
        cross_price = (25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        parallel_price = (DIFF_list[-1]+25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        DIFF_slope = (DIFF_list[-1]-DIFF_list[-2])/monthclosingprice_list[0]
        DEA_ratio = DEA9_list[-1]/monthclosingprice_list[0]
        DIFF_ratio = DIFF_list[-1]/DEA9_list[-1]
        DIFF_result = [stockinfo, monthclosingprice_list[0], round(DIFF_predict,2), DIFF_counter, round(DIFF_ratio,2), DEA_ratio, DIFF_slope, monthclosingprice_list[0], round(cross_price,2), round(parallel_price,2)]
    return MACD_result, DIFF_result


def trendMonth_Model_Select():
# K线图 月线 贯穿 5月线  可拓展为 N1月线 贯穿 N2月线
    resultfile_path = os.path.join(resultdata_path, "trendMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "月线上穿5月线预测月数", "5月线下方天数", "股票上穿前总跌幅", "当前价格", "月线交叉价格", "月线平行价格"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trendMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trendMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "trendMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "月线上穿5月线预测月数", "5月线下方天数", "股票上穿前总跌幅", "当前价格", "月线交叉价格", "月线平行价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trendMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trendMonth_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    MA1_list = []
    MA5_list = []
    DIFF_list = []
    if(len(monthclosingprice_list)<10):
        return []
    for ii in range(min(100, len(monthclosingprice_list)-(5-1))):
        MA1_list.append(monthclosingprice_list[ii])
        MA5_list.append(np.mean(monthclosingprice_list[ii:ii+5]))
        DIFF_list.append(MA1_list[ii] - MA5_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        trend_counter = 1
        for ii in range(1, len(DIFF_list)):
            if(DIFF_list[ii]<0):
                trend_counter += 1
            else:
                break
        trend_range = (monthclosingprice_list[0]-monthclosingprice_list[trend_counter])/monthclosingprice_list[trend_counter]*100
        trend_predict = round(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]), 2)
        cross_price = round(sum(monthclosingprice_list[:4])/4, 2)
        parallel_price = round((DIFF_list[0]*5/4+cross_price), 2)
        month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
        return [stockinfo, month_range, trend_predict, trend_counter, trend_range, monthclosingprice_list[0], cross_price, parallel_price]
    else:
        return []


def trendMonth5_Model_Select():
# K线图 5月线 贯穿 10月线  可拓展为 N1月线 贯穿 N2月线
    resultfile_path = os.path.join(resultdata_path, "trendMonth5_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "5月线上穿10月线预测月数", "10月线下方天数", "股票上穿前总跌幅", "当前价格", "月线交叉价格", "月线平行价格"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trendMonth5_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trendMonth5_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "trendMonth5_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "5月线上穿10月线预测月数", "10月线下方天数", "股票上穿前总跌幅", "当前价格", "月线交叉价格", "月线平行价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trendMonth5_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trendMonth5_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    MA5_list = []
    MA10_list = []
    DIFF_list = []
    if(len(monthclosingprice_list)<12):
        return []
    for ii in range(min(100, len(monthclosingprice_list)-(10-1))):
        MA5_list.append(np.mean(monthclosingprice_list[ii:ii+5]))
        MA10_list.append(np.mean(monthclosingprice_list[ii:ii+10]))
        DIFF_list.append(MA5_list[ii] - MA10_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1]) and (monthclosingprice_list[0]>MA10_list[0])):
        trend_counter = 1
        for ii in range(1, len(DIFF_list)):
            if(DIFF_list[ii]<0):
                trend_counter += 1
            else:
                break
        trend_range = (monthclosingprice_list[0]-monthclosingprice_list[trend_counter])/monthclosingprice_list[trend_counter]*100
        trend_predict = round(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]), 2)
        cross_price = sum(monthclosingprice_list[:9])-2*sum(monthclosingprice_list[:4])
        parallel_price = 10*DIFF_list[0]+cross_price
        month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
        return [stockinfo, month_range, trend_predict, trend_counter, trend_range, monthclosingprice_list[0], cross_price, parallel_price]
    else:
        return []


#def test_Model_Select_v1():
#    resultfile_path = os.path.join(resultdata_path, "test_Model_Select_Result.csv")
#    title = ["股票名称", test_item]
#    resultdata_list = []
#    for filename in os.listdir(stockdata_path):
#        _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
#        stockinfo = filename.split(".")[0]
#        if(test_num>0):
#            resultdata_list.append([stockinfo, test_item])
#    write_csvfile(resultfile_path, title, resultdata_list)

#def test_Model_Select():
#    resultfile_path = os.path.join(resultdata_path, "test_Model_Select_Result.csv")
#    title = ["股票名称", test_item]
#    resultdata_list = []
#    for filename in os.listdir(stockdata_path):
#        resultdata_list.append(test_Model_Select_pipeline(filename))
#    write_csvfile(resultfile_path, title, resultdata_list)
#def test_Model_Select():
#    resultfile_path = os.path.join(resultdata_path, "test_Model_Select_Result.csv")
#    title = ["股票名称", test_item]
#    pool = multiprocessing.Pool(4)
#    resultdata_list = pool.map(test_Model_Select_pipeline, os.listdir(stockdata_path))
#    pool.close()
#    pool.join()
#    write_csvfile(resultfile_path, title, resultdata_list)
#def test_Model_Select_pipeline(filename):
#    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
#    stockinfo = filename.split(".")[0]
#    if(test_num>0):
#        return [stockinfo, test_item]
#    else:
#        return []


def clear_data():
    for filename in os.listdir(stockdata_path):
        filepath = os.path.join(stockdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
    for filename in os.listdir(stockgdzjc_path):
        filepath = os.path.join(stockgdzjc_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)


def analyze_stockdata():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tdrop_Model_Select Begin!")
#    drop_Model_Select()
    drop_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tdrop_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tbox_Model_Select Begin!")
#    box_Model_Select()
    box_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tbox_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tVolumn_Model_Select Begin!")
#    volumn_Model_Select()
    volumn_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tVolumn_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend_Model_Select Begin!")
#    trend_Model_Select()
    trend_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend5_Model_Select Begin!")
#    trend5_Model_Select()
    trend5_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend5_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend10_Model_Select Begin!")
#    trend10_Model_Select()
    trend10_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend5_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFF_Model_Select Begin!")
#    MACDDIFF_Model_Select()
    MACDDIFF_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFF_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJ_Model_Select Begin!")
#    KDJ_Model_Select()
    KDJ_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJ_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tobv_Model_Select Begin!")
#    obv_Model_Select()
    obv_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tobv_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tLagging_Model_Select Begin!")
#    lagging_Model_Select()
    lagging_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tLagging_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tAHCom_Model_Select Begin!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tdropMonth_Model_Select Begin!")
#    dropMonth_Model_Select()
    dropMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tdropMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvshape_Model_Select Begin!")    
#    vshape_Model_Select()
    vshape_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvshape_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tshadow_Model_Select Begin!")    
#    shadow_Model_Select()
    shadow_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tshadow_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJMonth_Model_Select Begin!")    
#    KDJMonth_Model_Select()
    KDJMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFFMonth_Model_Select Begin!")
#    MACDDIFFMonth_Model_Select()
    MACDDIFFMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFFMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrendMonth_Model_Select Begin!")
#    trendMonth_Model_Select()
    trendMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrendMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrendMonth5_Model_Select Begin!")
#    trendMonth5_Model_Select()
    trendMonth5_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrendMonth5_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tEHBF_Analyze Begin!")
#    EHBF_Analyze()
    EHBF_Analyze_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tEHBF_Analyze Finished!")
    AHCom_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tAHCom_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tABCom_Model_Select Begin!")
    ABCom_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tABCom_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tmargin_Model_Select Begin!")
    margin_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tmargin_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tgdzjc_Model_Select Begin!")
    gdzjc_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tgdzjc_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\trepurchase_Model_Select Begin!")
    repurchase_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\trepurchase_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tsimilar_Model_Select Begin!")
#    similar_Model_Select()
    similar_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tsimilar_Model_Select Finished!")


def summary_result():
    resultfile_path = os.path.join(resultdata_path, "summary_result.csv")
    summaryfile_list = ["trend_Model_Select_Result.csv", "trend5_Model_Select_Result.csv", "trend10_Model_Select_Result.csv", "MACD_Model_Select_Result.csv", "DIFF_Model_Select_Result.csv", "KDJ_Model_Select_Result.csv",
     "trendMonth_Model_Select_Result.csv", "trendMonth5_Model_Select_Result.csv", "MACDMonth_Model_Select_Result.csv", "DIFFMonth_Model_Select_Result.csv", "KDJMonth_Model_Select_Result.csv"]
    for ii in reversed(range(len(summaryfile_list))):
        if(not os.path.exists(os.path.join(resultdata_path, summaryfile_list[ii]))):
            summaryfile_list.pop(ii)
    title = ["股票名称", "总和"] + [item.split("_")[0] for item in summaryfile_list]
    resultdata_list = []
    for ii in range(len(summaryfile_list)):
        _, stockdata_list = read_csvfile(os.path.join(resultdata_path, summaryfile_list[ii]))
        stockname_list = [item[0] for item in stockdata_list]
        summaryname_list = [item[0] for item in resultdata_list]
        for stockname in stockname_list:
            if(stockname not in summaryname_list):
                resultdata_list.append([stockname] + [0]*(len(title)-1))
                resultdata_list[-1][ii+2] = 1
            else:
                for jj in range(len(resultdata_list)):
                    if(resultdata_list[jj][0]==stockname):
                        resultdata_list[jj][ii+2] = 1
                        break
    for ii in range(len(resultdata_list)):
        resultdata_list[ii][1] = sum(resultdata_list[ii][2:])
    write_csvfile(resultfile_path, title, resultdata_list)


def main():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Prepare Begin!")
    if(get_163indexdata()):
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Stock Data Begin!")
        clear_data()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Stock Data Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tGenerage Stock Info Begin!")
        get_stockinfo()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tGenerage Stock Info Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Download Begin!")
        get_stockdata()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Download Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Prepare Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Begin!")
    analyze_stockdata()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tsummary_result Begin!")
    summary_result()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tsummary_result Finished!")




if __name__=="__main__":
    main()