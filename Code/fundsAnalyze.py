import os
import time
import random
import requests
import urllib
import re
import multiprocessing
import csv
import math


headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36 Core/1.63.6788.400 QQBrowser/10.3.2888.400'}

start_time = "1990-01-01"
end_time = time.strftime('%Y-%m-%d',time.localtime(time.time()))
#end_time = "2019-06-21"

root_path = "D:\\Workspace\\Python\\Stocks"
fundinfo_file = os.path.join(root_path, "Data", "fundinfo.txt")
funddata_path = os.path.join(root_path, "Data", "fund_data")
resultdata_path = os.path.join(root_path, "Result", end_time)
if __name__=="__main__":
    if(not os.path.exists(resultdata_path)):
        os.mkdir(resultdata_path)


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


def write_csvfile(filename, title, data_list):
    with open(filename, 'w') as fp:
        fp.write(",".join([str(item) for item in title]) + "\n")
        for row_item in data_list:
            if(row_item!=[]):
                fp.write(",".join([str(item) for item in row_item]) + "\n")


def get_htmltext(url):
    for ii in range(10):
        time.sleep(random.choice([1,2]))
        try:
            response = requests.get(url, headers=headers)
#            response = requests.get(url)
#            print("Get Successfully: " + url)
            if(response.status_code!=200):
                return ""
            try:
                html_text = response.content.decode('utf8')
            except UnicodeDecodeError as e:
#                print(e)
                html_text = response.content.decode('gbk')
#            except NameError as e:
#                print(e)
#                html_text = ""
            return html_text
        except Exception as e:
            print(e)
    return ""


def get_hexundata(fundinfo):
    fundtype=fundinfo.split('_')[0]
    fundcode=fundinfo.split('_')[1]
    hexundata_url = "http://data.funds.hexun.com/outxml/detail/openfundnetvalue.aspx?fundcode={}&startdate={}&enddate={}".format(fundcode, start_time, end_time)
    hexundata_html = get_htmltext(hexundata_url)
    if(hexundata_html!=""):
        fundcode = re.findall(r'<fundcode>(.*)</fundcode>', hexundata_html)[0]
        fundname = re.findall(r'<fundname>(.*)</fundname>', hexundata_html)[0]
        enddate_list = re.findall(r'<fld_enddate>(.*)</fld_enddate>', hexundata_html)
        unitnetvalue_list = re.findall(r'<fld_unitnetvalue>(.*)</fld_unitnetvalue>', hexundata_html)
        netvalue_list = re.findall(r'<fld_netvalue>(.*)</fld_netvalue>', hexundata_html)
#        newprice_list = re.findall(r'<fld_newprice>(.*)</fld_newprice>', hexundata_html)
#        if(len(enddate_list)==len(unitnetvalue_list)==len(netvalue_list)==len(newprice_list)):
        if(len(enddate_list)==len(unitnetvalue_list)==len(netvalue_list)):
#            title = ['时间', '基金信息', '单位净值', '累计净值', '上证指数']
#            funddata_list = [[fundinfo, enddate_list[ii], unitnetvalue_list[ii], netvalue_list[ii], newprice_list[ii]] for ii in range(len(enddate_list))]
            title = ['时间', '基金信息', '单位净值', '累计净值']
            fundinfo = fundtype+'_'fundcode+'_'+fundname
            funddata_file = os.path.join(funddata_path,'{}.csv'.format(fundinfo))
            funddata_list = [[enddate_list[ii], fundinfo, unitnetvalue_list[ii], netvalue_list[ii]] for ii in range(len(enddate_list))]
            write_csvfile(funddata_file, title, funddata_list)


def get_funddata():
    with open(fundinfo_file, 'r') as fp:
        for fundinfo in fp.readlines():
            get_hexundata(fundinfo.strip())


def get_fundinfo():
# 得到场内交易fund指数基金
#    fund_url = "http://fund.eastmoney.com/ETFN_sj.html"
    fund_url1 = "http://fund.eastmoney.com/cnjy_jzzzl.html"
    fund_html1 = get_htmltext(fund_url1)
    fund_list1 = re.findall(r'<tr bgcolor="#F5FFFF" height=20 id="tr([0-9]{6})">',fund_html1)
    fund_list1 = [("ETF_"+item) for item in fund_list1]
    fund_url2 = "http://fund.eastmoney.com/Data/Fund_JJJZ_Data.aspx?t=1&lx=2&page=1,20000&onlySale=0"
    fund_html2 = get_htmltext(fund_url2)
    fund_list2 = re.findall(r'"([0-9]{6})"', fund_html2)
    fund_list2 = [("Stock_"+item) for item in fund_list2]
    fund_list3 = ["162411", "501018"]
    fund_list3 = [("Self_"+item) for item in fund_list3]
    fundinfo_list = fund_list1 + fund_list2 + fund_list3
    fundinfo_list = list(set(fundinfo_list))
    with open(fundinfo_file, 'w') as fp:
        fp.write("\n".join(fundinfo_list))
    return True


def MACDDIFF_Model_Select():
# MACD 模型 (12,26,9) & 中间量 DIFF 模型
    resultfile_path1 = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFF_Model_Select_Result.csv")
    title1 = ["基金信息", "估算MACD贯穿天数", "MACD下方天数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格",  "MACD平行预测价格", "MACD不变预测价格"]
    title2 = ["基金信息", "估算DIFF贯穿天数", "DIFF下方天数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF平行预测价格", "DIFF不变预测价格"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(funddata_path):
        MACD_result, DIFF_result = MACDDIFF_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def MACDDIFF_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFF_Model_Select_Result.csv")
    title1 = ["基金信息", "估算MACD贯穿天数", "MACD下方天数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格",  "MACD平行预测价格", "MACD不变预测价格"]
    title2 = ["基金信息", "估算DIFF贯穿天数", "DIFF下方天数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF平行预测价格", "DIFF不变预测价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFF_Model_Select_pipeline, os.listdir(funddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def MACDDIFF_Model_Select_pipeline(filename):
    _, funddata_list = read_csvfile(os.path.join(funddata_path, filename))
    fundinfo = filename.split(".")[0]
    EMA12 = 0
    EMA26 = 0
    DIFF_list = [0]
    DEA9_list = [0]
    MACD_list = [0]
    MACD_result = []
    DIFF_result = []
    for ii in reversed(range(min(200, len(funddata_list)))):
        EMA12 = 11/13*EMA12 + 2/13*float(funddata_list[ii][3])
        EMA26 = 25/27*EMA26 + 2/27*float(funddata_list[ii][3])
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
        MACD_range = (float(funddata_list[0][3])-float(funddata_list[MACD_counter-1][3]))/float(funddata_list[MACD_counter-1][3])*100
        MACD_predict = math.ceil(MACD_list[-1]/(MACD_list[-2]-MACD_list[-1]))
        cross_price = (DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
        slope_price = ((5/8*(MACD_list[-1]*2-MACD_list[-2])+DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27))
        parallel_price = (5/8*MACD+DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
        MACD_slope = (MACD_list[-1]-MACD_list[-2])/float(funddata_list[0][3])
        DEA_ratio = DEA9_list[-1]/float(funddata_list[0][3])
        MACD_result = [fundinfo, MACD_predict, MACD_counter, DEA_ratio, MACD_range, MACD_slope, funddata_list[0][3], round(cross_price,2), round(slope_price,2), round(parallel_price,2)]
    if((DIFF_list[-2]<0) and (DIFF_list[-1]>DIFF_list[-2])):
        DIFF_counter = 1
        for ii in reversed(range(len(DIFF_list)-1)):
            if(DIFF_list[ii]<0):
                DIFF_counter+=1
            else:
                break
        DIFF_predict = math.ceil(DIFF_list[-1]/(DIFF_list[-2]-DIFF_list[-1]))
        cross_price = (25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        slope_price = (2*DIFF_list[-1]-DIFF_list[-2]+25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        parallel_price = (DIFF_list[-1]+25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        DIFF_slope = (DIFF_list[-1]-DIFF_list[-2])/float(funddata_list[0][3])
        DEA_ratio = DEA9_list[-1]/float(funddata_list[0][3])
        DIFF_ratio = DIFF_list[-1]/DEA9_list[-1]
        DIFF_result = [fundinfo, DIFF_predict, DIFF_counter, round(DIFF_ratio,2), DEA_ratio, DIFF_slope, funddata_list[0][3], round(cross_price,2), round(slope_price,2), round(parallel_price,2)]
    return MACD_result, DIFF_result


def clear_data():
    for filename in os.listdir(funddata_path):
        filepath = os.path.join(funddata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)


def analyze_funddata():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFF_Model_Select Begin!")
#    MACDDIFF_Model_Select()
    MACDDIFF_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFF_Model_Select Finished!")


def main():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tNet Connect Begin!")
    tunet_connect()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tNet Connect Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Prepare Begin!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Fund Data Begin!")
    clear_data()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Fund Data Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tGenerage Fund Info Begin!")
    get_fundinfo()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tGenerage Fund Info Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tFund Data Download Begin!")
    get_funddata()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tFund Data Download Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Prepare Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Begin!")
    analyze_funddata()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Finished!")


if __name__ =="__main__":
    main()