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
import tunet
import urllib
import scipy.stats as scistats
import shutil


tspro = ts.pro_api("119921ff45f95fd77e5d149cd1e64e78572712b3d0a5ce38157f255b")

start_time = "19900101"
end_time = time.strftime('%Y%m%d',time.localtime(time.time()))
#end_time = "20190621"

root_path = "D:\\Workspace\\Python\\Stocks"
stockdata_path = os.path.join(root_path, "Data", "stock_data")
EHBFfile_path = os.path.join(root_path, "Result", "Stocks", "EHBF_Analyze_Result.csv")
resultdata_path = os.path.join(root_path, "Result", "Stocks")
toolsdata_path = os.path.join(root_path, "Result", "Tools")
blockdata_path = os.path.join(root_path, "Data", "block_data")
holderdata_path = os.path.join(root_path, "Data", "holders_data")
gdzjcdata_path = os.path.join(root_path, "Data", "gdzjc_data")

def tunet_connect():
    with open("D:\\Workspace\\Python\\Stocks\\Code\\tunet.config") as fp:
        lines = fp.readlines()
        try:
            print(tunet.net.login(lines[0].strip(), lines[1].strip()))
            print(tunet.net.checklogin())
        except urllib.error.URLError as e:
            print(tunet.auth4.login(lines[0].strip(), lines[1].strip(), net=True))
            print(tunet.auth4.checklogin())
        except Exception as e:
            print(e)


def read_csvfile(filename):
    if(os.path.exists(filename)):
        with open(filename, 'r') as fp:
            data_list = list(csv.reader(fp))
            return data_list[0], data_list[1:]
    else:
        return [], []


def gen_tscode(stockcode):
    code = ""
    if(stockcode[0]=="0"):
        code=stockcode+".SZ"
    elif(stockcode[0]=="6"):
        code=stockcode+".SH"
    return code


def gen_163code(stockcode):
    code = ""
    if(stockcode[0]=="0"):
        code = "1"+stockcode
    elif(stockcode[0]=="6"):
        code = "0"+stockcode
    return code


def write_csvfile(filename, title, data_list):
    with open(filename, 'w') as fp:
        fp.write(",".join([str(item) for item in title]) + "\n")
        for row_item in data_list:
            if(row_item!=[]):
                fp.write(",".join([str(item) for item in row_item]) + "\n")


def insert_csvfile(filename, data_list):
    title, stockdata_list = read_csvfile(filename)
    write_csvfile(filename, title, data_list+stockdata_list)


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
            response = requests.get(url)
#            response = requests.get(url, headers=headers)
#            print("Get Successfully: " + url)
            if(response.status_code!=200):
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
            data = requests.get(url)
            with open(filename, 'wb') as fp:
                chunk_size = 100000
                for chunk in data.iter_content(chunk_size):
                    fp.write(chunk)
#            print("Download Successfully: " + url)
            return True
        except Exception as e:
            print(e)
    return False


def get_jsvar(url, varname):
    response = get_htmltext(url)
    if(response.find(varname)!=-1):
        return execjs.compile(response).eval(varname)
    else:
        return None


def holders_Model_Select():
    resultfile_path = os.path.join(toolsdata_path, "Holders_Analyze_Select.csv")
    title = ["股票名称", "当前股东人数", "当季股东人数降幅",  "股东人数降低季度", "股东人数总降幅", "历史位置", "盈利比例", "历史最大股东人数", "历史最大股东人数日期", "历史最小股东人数", "历史最小股东人数日期"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        stockinfo = filename.split('.')[0]
        stockcode = stockinfo[-6:]
        holders_df = []
        holders_list = []
        for ii in range(3):
            try:
                time.sleep(random.choice([1,2]))
                holders_df = tspro.stk_holdernumber(ts_code=gen_tscode(stockcode), start_date=start_time, end_date=end_time)
                holders_list = holders_df.values.tolist()
                holders_title = ["TS股票代码", "公告日期", "截止日期", "股东户数"]
                write_csvfile(os.path.join(holderdata_path, stockinfo+".csv"), holders_title, holders_list)
                if(len(holders_list)>5):
                    holdernum_list = [item[3] for item in holders_list]
                    modelcounter = 0
                    for ii in range(len(holdernum_list)-1):
                        if(holdernum_list[ii]<holdernum_list[ii+1]):
                            modelcounter += 1
                        else:
                            break
                    if(modelcounter>0):
                        modelrange = (holdernum_list[0]/holdernum_list[modelcounter]-1)*100
                        holderrange = (holdernum_list[0]/holdernum_list[1]-1)*100
                        minholdernum = min(holdernum_list[:-2])
                        minholderdate = holders_list[holdernum_list.index(minholdernum)][2]
                        maxholdernum = max(holdernum_list[:-2])
                        maxholderdate = holders_list[holdernum_list.index(maxholdernum)][2]
                        _, EHBFdata_list = read_csvfile(EHBFfile_path)
                        earnratio = "-1"
                        reboundrange = "-1"
                        for EHBFitem in EHBFdata_list:
                            if(EHBFitem[0]==stockinfo):
                                reboundrange = EHBFitem[2]
                                earnratio = EHBFitem[4]
                        resultdata_list.append([stockinfo, holdernum_list[0], holderrange, modelcounter, modelrange, reboundrange, earnratio, maxholdernum, maxholderdate, minholdernum, minholderdate])
                break
            except Exception as e:
                print(e)
                time.sleep(600)
    write_csvfile(resultfile_path, title, resultdata_list)


def gdzjc_Model_Select():
# 东方财富网增减持数据
    resultfile_path = os.path.join(toolsdata_path, "gdzjc_Model_Select_Result.csv")
    title = ["股票名称", "最新价", "涨跌幅(%)", "股东名称", "增减", "方式", "变动开始日", "变动截止日", "公告日", "变动数量(万股)", "占总股本比例(%)", "占流通股比例(%)",  "持股总数(万股)", "占总股本比例", "持流通股数(万股)", "占流通股比例"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        stockinfo = filename.split('.')[0]
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
                write_csvfile(os.path.join(gdzjcdata_path, stockinfo+".csv"), zjc_title, zjcdata_list)
                if((zjcdata_list[0][4]=="增持") and (zjcdata_list[0][8]>time.strftime('%Y-%m-%d',time.localtime(time.time()-24*3600*366)))):
                    resultdata_list.append(zjcdata_list[0])
    write_csvfile(resultfile_path, title, resultdata_list)


def repurchase_Model_Select():
# 股票回购信息汇总
    resultfile_path = os.path.join(toolsdata_path, "repurchase_Model_Select_Result.csv")
    title = ["股票代码", "公告日期", "截止日期", "进度", "过期日期", "回购数量", "回购金额", "回购最高价", "回购最低价"]
    resultdata_list = []
    for ii in range(3):
        try:
            time.sleep(1)
            repurchase_df = tspro.repurchase(start_date=time.strftime('%Y%m%d',time.localtime(time.time()-24*3600*366)), end_date=end_time)
            for item in repurchase_df.values:
                if(item[0][0] in ["0", "6"]):
                    resultdata_list.append(list(item))
            break
        except Exception as e:
            print(e)
            time.sleep(600)
    write_csvfile(resultfile_path, title, resultdata_list)


def block_Model_Select():
# 大宗交易数据
    resultfile_path = os.path.join(toolsdata_path, "block_Model_Select_Result.csv")
    title = ["股票名称", "交易日期", "交易溢价率", "交易换手率", "当日换手率", "成交金额", "买方营业部", "卖方营业部"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        stockinfo = filename.split('.')[0]
        stockcode = stockinfo[-6:]
        for ii in range(3):
            try:
                time.sleep(1)
                block_title = ["股票名称", "交易日历", "成交价", "成交量(万股)", "成交金额", "买方营业部", "卖方营业部"]
                block_df = tspro.block_trade(ts_code=gen_tscode(stockcode), start_date=time.strftime('%Y%m%d',time.localtime(time.time()-24*3600*366)), end_date=time.strftime('%Y%m%d',time.localtime(time.time()-24*3600)))
                block_list = block_df.values.tolist()
                for ii in reversed(range(len(block_list))):
                    if(block_list[ii][5][:4]==block_list[ii][6][:4]):
                        block_list.pop(ii)
                    else:
                        block_list[ii][0] = stockinfo
                if(block_list!=[]):
                    write_csvfile(os.path.join(blockdata_path, filename), block_title, block_list)
                    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
                    convpre = (float(block_list[0][2])/float(stockdata_list[0][3])-1)*100
                    obv = float(stockdata_list[0][10])*float(block_list[0][3])*10000/float(stockdata_list[0][11])
                    if((convpre>=-5) and ("ST" not in block_list[0][0])):
                        resultdata_list.append([stockinfo, block_list[0][1], convpre, obv, float(stockdata_list[0][10]), block_list[0][4], block_list[0][5], block_list[0][6]])
                break
            except Exception as e:
                print(e)
                time.sleep(600)
    write_csvfile(resultfile_path, title, resultdata_list)




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
        simidegree, _ = scistats.pearsonr(closingprice_list,ref_list)
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
            simidegree, _ = scistats.pearsonr(closingprice_list, ref_list)
            if(simidegree>maxallsimidegree):
                maxallsimidegree = simidegree
                simistockinfo = filename2.split(".")[0]
                allsimidate = stockdata2_list[ii][0]
                allprerange_list = list(reversed([float(item[9]) for item in stockdata2_list[(ii-5):ii]])) 
                allprerange = sum(allprerange_list)
    return [stockinfo, maxselfsimidegree, selfprerange, selfsimidate, maxallsimidegree, allprerange, simistockinfo, allsimidate] + selfprerange_list + allprerange_list


def clear_data():
    if(not os.path.exists(toolsdata_path)):
        os.mkdir(toolsdata_path)
    for filename in os.listdir(toolsdata_path):
        filepath = os.path.join(toolsdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
    if(not os.path.exists(blockdata_path)):
        os.mkdir(blockdata_path)
    for filename in os.listdir(blockdata_path):
        filepath = os.path.join(blockdata_path, filename)
        if(os.path.exists(blockdata_path)):
            os.remove(blockdata_path)
    if(not os.path.exists(holderdata_path)):
        os.mkdir(holderdata_path)
    for filename in os.listdir(holderdata_path):
        filepath = os.path.join(holderdata_path, filename)
        if(os.path.exists(holderdata_path)):
            os.remove(holderdata_path)
    if(not os.path.exists(gdzjcdata_path)):
        os.mkdir(gdzjcdata_path)
    for filename in os.listdir(gdzjcdata_path):
        filepath = os.path.join(gdzjcdata_path, filename)
        if(os.path.exists(gdzjcdata_path)):
            os.remove(gdzjcdata_path)


def summary_result():
    for filename in os.listdir(stockdata_path):
        shutil.copy(os.path.join(stockdata_path, filename), os.path.join(toolsdata_path, filename))
    selectfile_list = os.listdir(toolsdata_path)
    resultfile_path = os.path.join(toolsdata_path, "summary_result.csv")
    title = ["股票名称", "总和"] + [item.split('_')[0] for item in selectfile_list]
    stockinfo_list = []
    with open(stockinfo_file, 'r') as fp:
        stockinfo_list = fp.read().splitlines()
    resultdata_list = []
    for stockinfo in stockinfo_list:
        resultdata_list.append(summary_result_pipeline(stockinfo))
    write_csvfile(resultfile_path, title, resultdata_list)
def summary_result_par():
    for filename in os.listdir(stockdata_path):
        shutil.copy(os.path.join(stockdata_path, filename), os.path.join(toolsdata_path, filename))
    selectfile_list = os.listdir(toolsdata_path)
    resultfile_path = os.path.join(toolsdata_path, "summary_result.csv")
    title = ["股票名称", "总和"] + [item.split('_')[0] for item in selectfile_list]
    stockinfo_list = []
    with open(stockinfo_file, 'r') as fp:
        stockinfo_list = fp.read().splitlines()
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(summary_result_pipeline, stockinfo_list)
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def summary_result_pipeline(stockinfo):
    selectfile_list = os.listdir(toolsdata_path)
    for ii in reversed(range(len(selectfile_list))):
        if(not os.path.exists(os.path.join(toolsdata_path, selectfile_list[ii]))):
            selectfile_list.pop(ii)
    summary_list = []
    for ii in range(len(selectfile_list)):
        _, selectdata_list = read_csvfile(os.path.join(toolsdata_path, selectfile_list[ii]))
        stockinfo_list = [item[0] for item in selectdata_list]
        if(stockinfo in stockinfo_list):
            summary_list.append(1)
        else:
            summary_list.append(0)
    if(sum(summary_list)>0):
        return [stockinfo, sum(summary_list)] + summary_list
    else:
        return []


def analyze_stockdata():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tblock_Model_Select Begin!")
    block_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tblock_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\trepurchase_Model_Select Begin!")
    repurchase_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\trepurchase_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tgdzjc_Model_Select Begin!")
    gdzjc_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tgdzjc_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tholders_Model_Select Begin!")
    holders_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tholders_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tsimilar_Model_Select Begin!")
##    similar_Model_Select()
    similar_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tsimilar_Model_Select Finished!")


def main():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tNet Connect Begin!")
    tunet_connect()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tNet Connect Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Data Begin!")
    clear_data()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Data Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Begin!")
    analyze_stockdata()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tResult Summary Begin!")
#    summary_result()
    summary_result_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tResult Summary Finished!")


if __name__=="__main__":
    main()