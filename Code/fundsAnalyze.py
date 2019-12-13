import os
import time
import random
import tunet
import requests
import execjs
from bs4 import BeautifulSoup
import urllib
import re
import multiprocessing
import csv
import math
import tushare as ts


tspro = ts.pro_api("119921ff45f95fd77e5d149cd1e64e78572712b3d0a5ce38157f255b")

headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36 Core/1.63.6788.400 QQBrowser/10.3.2888.400'}

start_time = "19900101"
end_time = time.strftime('%Y%m%d',time.localtime(time.time()-24*3600))
#end_time = "20190621"

root_path = "D:\\Workspace\\Python\\Stocks"
fundinfo_file = os.path.join(root_path, "Data", "fundinfo.txt")
funddata_path = os.path.join(root_path, "Data", "fund_data")
resultdata_path = os.path.join(root_path, "Result", "Funds")
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
                html_text = response.content.decode('utf-8-sig')
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


def get_jsvar(url, varname):
    response = get_htmltext(url)
    if(response.find(varname)!=-1):
        return execjs.compile(response).eval(varname)
    else:
        return None


def get_hexundata(fundinfo):
    title = ['时间', '基金信息', '单位净值', '累计净值', "折算净值", "日涨跌幅"]
    fundcode=fundinfo.split('_')[-1]
    hexundata_url = "http://data.funds.hexun.com/outxml/detail/openfundnetvalue.aspx?fundcode={}&startdate={}&enddate={}".format(fundcode, (start_time[0:4]+'-'+start_time[4:6]+'-'+start_time[6:8]), (end_time[0:4]+'-'+end_time[4:6]+'-'+end_time[6:8]))
    fhsp_url = "http://fundf10.eastmoney.com/fhsp_{}.html".format(fundcode)
    hexun_res = get_htmltext(hexundata_url)
    fhsp_res = get_htmltext(fhsp_url)
    if((hexun_res!="") and (fhsp_res!="")):
        funddata_list = []
        hexun_soup = BeautifulSoup(hexun_res, "lxml")
        dataset = hexun_soup.find_all('dataset')[0]
        funddata_file = os.path.join(funddata_path,'{}.csv'.format(fundinfo))
        for item in dataset.find_all('data'):
            enddate = item.find_all('fld_enddate')[0].text
            unitnetvalue = item.find_all('fld_unitnetvalue')[0].text
            netvalue = item.find_all('fld_netvalue')[0].text
            funddata_list.append([enddate, fundinfo, unitnetvalue, netvalue, unitnetvalue, 0])
        fhsp_soup = BeautifulSoup(fhsp_res, 'lxml')
        fh_table = fhsp_soup.find_all('table', attrs={'class':'w782 comm cfxq'})[0]
        divident_list = []
        if(len(fh_table.find_all('td'))>1):
            for fh_tr in fh_table.find_all('tr')[1:]:
                fh_td_list = fh_tr.find_all('td')
                registerdate = fh_td_list[1].text
                dividentdate = fh_td_list[2].text
                divident = float(re.findall(r"每份派现金(\d+\.\d+)元", fh_td_list[3].text)[0])
                divident_list.append([registerdate, dividentdate, divident, "sub"])
        sp_table = fhsp_soup.find_all('table', attrs={'class':'w782 comm fhxq'})[0]
        if(len(sp_table.find_all('td'))>1):
            for sp_tr in sp_table.find_all('tr')[1:]:
                sp_td_list = sp_tr.find_all('td')
                dividentdate = sp_td_list[1].text
                dividenttext = sp_td_list[3].text
                if(dividenttext!="暂未披露"):
                    divident = float(re.findall(r"1:(\d+\.\d+)", dividenttext)[0])
                    divident_list.append([dividentdate, dividentdate, divident, "divided"])
        divident_list.sort(reverse=True, key=lambda item: item[1])
        fundoffset = len(funddata_list)
        for ii in reversed(range(len(divident_list))):
            for jj in reversed(range(1, fundoffset)):
                if(funddata_list[jj-1][0]>=divident_list[ii][1]):
                    fundoffset = jj+1
                    proportion = 1
                    if(divident_list[ii][3]=='sub'):
                        proportion = 1-(float(divident_list[ii][2]))/float(funddata_list[jj][4])
                    else:
                        proportion = 1/float(divident_list[ii][2])
                    for kk in range(jj, len(funddata_list)):
                        funddata_list[kk][4] = float(funddata_list[kk][4]) * proportion
                    break
        for ii in range(len(funddata_list)-1):
            funddata_list[ii][5] = ((float(funddata_list[ii][4])/float(funddata_list[ii+1][4]))-1)*100
        write_csvfile(funddata_file, title, funddata_list)
        check_funddata(funddata_file)


def get_funddata():
    with open(fundinfo_file, 'r') as fp:
        for fundinfo in fp.readlines():
            get_hexundata(fundinfo.strip())


def check_funddata(filename):
    title, funddata_list = read_csvfile(filename)
    for ii in reversed(range(len(funddata_list))):
        if((funddata_list[ii][3]=="") or (funddata_list[ii][3]=="0.0000")):
            funddata_list.pop(ii)
    if(funddata_list==[]):
        os.remove(filename)
    else:
        write_csvfile(filename, title, funddata_list)


def get_fundinfo():
# 得到场内交易fund指数基金
    url = "http://fund.eastmoney.com/js/fundcode_search.js"
    fund_list = get_jsvar(url, 'r')
    fundinfo_list = []
    for ii in range(len(fund_list)):
#    ["债券型", "混合型", "货币型", "理财型", "保本型", "债券指数", "固定收益", "定开债券", "混合-FOF", "其他创新", "股票型", "分级杠杆", "ETF-场内", "QDII", "QDII-指数", "股票指数", "联接基金", "QDII-ETF"]
        if((fund_list[ii][3] in ["股票型", "分级杠杆", "ETF-场内", "QDII", "QDII-指数", "股票指数", "联接基金", "QDII-ETF"]) and ("(后端)" not in fund_list[ii][2]) and fund_list[ii][2][-1]!='C'):
            fundinfo_list.append(fund_list[ii][3]+'_'+fund_list[ii][2].replace('/','-')+'_'+fund_list[ii][0])
    with open(fundinfo_file, 'w') as fp:
        fp.write("\n".join(fundinfo_list))
    return True


def isMarketOpen():
    df = tspro.trade_cal(exchange='', start_date=end_time, end_date=end_time)
    df_list = df.values.tolist()
    if(df_list[0][2]==1):
        return True
    else:
        return False


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
        EMA12 = 11/13*EMA12 + 2/13*float(funddata_list[ii][4])
        EMA26 = 25/27*EMA26 + 2/27*float(funddata_list[ii][4])
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
        MACD_range = (float(funddata_list[0][4])-float(funddata_list[MACD_counter-1][4]))/float(funddata_list[MACD_counter-1][4])*100
        MACD_predict = math.ceil(MACD_list[-1]/(MACD_list[-2]-MACD_list[-1]))
        cross_price = (DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
        slope_price = ((5/8*(MACD_list[-1]*2-MACD_list[-2])+DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27))
        parallel_price = (5/8*MACD+DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
        MACD_slope = (MACD_list[-1]-MACD_list[-2])/float(funddata_list[0][4])
        DEA_ratio = DEA9_list[-1]/float(funddata_list[0][4])
        MACD_result = [fundinfo, MACD_predict, MACD_counter, DEA_ratio, MACD_range, MACD_slope, funddata_list[0][4], round(cross_price,2), round(slope_price,2), round(parallel_price,2)]
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
        DIFF_slope = (DIFF_list[-1]-DIFF_list[-2])/float(funddata_list[0][4])
        DEA_ratio = DEA9_list[-1]/float(funddata_list[0][4])
        DIFF_ratio = DIFF_list[-1]/DEA9_list[-1]
        DIFF_result = [fundinfo, DIFF_predict, DIFF_counter, round(DIFF_ratio,2), DEA_ratio, DIFF_slope, funddata_list[0][4], round(cross_price,2), round(slope_price,2), round(parallel_price,2)]
    return MACD_result, DIFF_result


def clear_data():
    for filename in os.listdir(funddata_path):
        filepath = os.path.join(funddata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
    for filename in os.listdir(resultdata_path):
        filepath = os.path.join(resultdata_path, filename)
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
    if(isMarketOpen()):
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