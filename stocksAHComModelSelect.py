import requests
import random
import time
import os
import csv
import json
import shutil


end_time = time.strftime('%Y%m%d',time.localtime(time.time()))

root_path = "D:\\Workspace\\Python\\Stocks"
AHdataHistory_path = os.path.join(root_path, "AH_stock_data_history")
AHdata_path = os.path.join(root_path, "AH_stock_data")
resultdata_path = os.path.join(root_path, "AHCom_model_data")
resultfile_path = os.path.join(root_path, "AHCom_Model_Select_Result.csv")

def get_AHdata():
    AH_url = "http://quotes.money.163.com/hs/realtimedata/service/ah.php?host=/hs/realtimedata/service/ah.php&page=0&fields=SCHIDESP,PRICE,SYMBOL,AH,PERCENT,VOLUME&count=500"
    AHdataNew_list = []
    for AHitem in json.loads(requests.get(AH_url).text)["list"]:
        if(AHitem["PRICE"]==0):
            continue
        if("ST" in str(AHitem["AH"]["ASTOCKNAME"])):
            continue
        if(str(AHitem["SYMBOL"]).format(5)=="02922"):
            continue
        AHdataNew = [str(AHitem["AH"]["ASTOCKNAME"]), str(AHitem["AH"]["A_SYMBOL"]).format(6), str(AHitem["AH"]["ASTOCKCODE"]).format(7),
            str(AHitem["AH"]["A_PRICE"]), str(AHitem["AH"]["A_PERCENT"]*100), str(AHitem["SYMBOL"]).format(5), str(AHitem["SCHIDESP"]), 
            str(AHitem["PRICE"]), str(AHitem["PERCENT"]*100), str(AHitem["AH"]["PREMIUMRATE"])]
        AHdataNew_list.append(AHdataNew)
    IsADataChange = True
    IsHDataChange = True
    if(os.path.exists(os.path.join(AHdataHistory_path, "new.csv"))):
        with open(os.path.join(AHdataHistory_path, "new.csv"), "r") as fp:
            AHdataOld_list = list(csv.reader(fp))[1:]
        IsADataChange = False
        IsHDataChange = False
        for AHdataNew in AHdataNew_list:
            for AHdataOld in AHdataOld_list:
                if(AHdataNew[2]==AHdataOld[2]):
                    if(float(AHdataNew[4])!=float(AHdataOld[4])):
                        IsADataChange = True
                    if(float(AHdataNew[8])!=float(AHdataOld[8])):
                        IsHDataChange = True
        if(not IsADataChange):
            for ii in range(len(AHdataNew_list)):
                AHdataNew_list[ii][4] = 0
        if(not IsHDataChange):
            for ii in range(len(AHdataNew_list)):
                AHdataNew_list[ii][8] = 0
    if(IsADataChange or IsHDataChange):
        with open(os.path.join(AHdataHistory_path, "new.csv"), "w") as fp:
            fp.write("A股名称,A股代码,A股查询代码,A股价格,A股涨跌幅,H股代码,H股名称,H股价格,H股涨跌幅,H股溢价率(溢价率=(H股价格*0.8545-A股价格)/A股价格*100%),\n")
            for AHdataNew in AHdataNew_list:
                fp.write(",".join(AHdataNew)+"\n")
        shutil.copy(os.path.join(AHdataHistory_path, "new.csv"), os.path.join(AHdataHistory_path, end_time+".csv"))
        for AHdataNew in AHdataNew_list[1:]:
            AHfilename = os.path.join(AHdata_path, (str(AHdataNew[0]) + "_" + str(AHdataNew[2]).format(7) + ".csv"))
            if(not os.path.exists(AHfilename)):
                with open(AHfilename, 'w') as fp:
                    fp.write("时间,A股名称,A股代码,A股查询代码,A股价格,A股涨跌幅,H股代码,H股名称,H股价格,H股涨跌幅,H股溢价率(溢价率=(H股价格*0.8545-A股价格)/A股价格*100%),\n")
            with open(AHfilename, 'a') as fp:
                fp.write((",".join([end_time]+AHdataNew))+"\n")


def AHCom_Model_Select():
    filenames = os.listdir(AHdata_path)
    for filename in filenames:
        filepath = os.path.join(AHdata_path, filename)
        with open(filepath, "r") as fp:
            AH_data_list = list(csv.reader(fp))
            AHComCounter = 0
            for ii in range(1, len(AH_data_list)):
                try:
                    if(float(AH_data_list[ii][5])>float(AH_data_list[ii][9])):
                        break
                    else:
                        AHComCounter += 1
                except:
                    break
            if(AHComCounter>0):
                AHComrange = 0
                AStockrange = 0
                HStockrange = 0
                for ii in range(1, AHComCounter+1):
                    AStockrange += float(AH_data_list[ii][5])
                    HStockrange += float(AH_data_list[ii][9])
                    AHComrange += float(AH_data_list[ii][9]) - float(AH_data_list[ii][5])
                resultNumfile_path = os.path.join(resultdata_path,"AHCom_Model_Select_Result"+str(AHComCounter)+".csv")
                if(not os.path.exists(resultNumfile_path)):
                    with open(resultNumfile_path, 'w') as fp:
                        row0 = "股票名称,"
                        for ii in range(1,AHComCounter+1):
                            row0 = row0 + "A股涨跌幅" + str(ii) + "," + "H股涨跌幅" + str(ii) + ","
                        row0 = row0 + "A股总涨跌幅" + "," + "H股总涨跌幅" + "," + "A股总滞后幅" + ","
                        fp.write(row0 + "\n")
                with open(resultNumfile_path, 'a') as fp:
                    datarow=filename+","
                    for ii in range(1, AHComCounter+1):
                        datarow = datarow + AH_data_list[ii][5] + "," + AH_data_list[ii][9] + ","
                    datarow = datarow + str(AStockrange) + "," + str(HStockrange) + "," + str(AHComrange) + ","
                    fp.write(datarow + "\n")
                if(not os.path.exists(resultfile_path)):
                    with open(resultfile_path, 'w') as fp:
                        row0 = "股票名称, 股票滞后天数, A股总涨跌幅, H股总涨跌幅, A股总滞后幅,"
                        fp.write(row0 + "\n")
                with open(resultfile_path, 'a') as fp:
                    datarow = filename+","+str(AHComCounter)+"," + str(AStockrange) + "," + str(HStockrange) + "," +str(AHComrange) + ","
                    fp.write(datarow + "\n")


if __name__ == "__main__":
    filenames = os.listdir(root_path)
    for filename in filenames:
    	if(("AHCom_Model_Select_Result" in filename) and (".csv" in filename)):
            resultfile = os.path.join(root_path,filename)
            if(os.path.exists(resultfile)):
                os.remove(resultfile)
    filenames = os.listdir(resultdata_path)
    for filename in filenames:
        if(("AHCom_Model_Select_Result" in filename) and (".csv" in filename)):
            resultfile = os.path.join(resultdata_path,filename)
            if(os.path.exists(resultfile)):
                os.remove(resultfile)
    get_AHdata()
    AHCom_Model_Select()