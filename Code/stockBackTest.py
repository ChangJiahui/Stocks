import requests
import random
from bs4 import BeautifulSoup as bs
import time
import os
import csv


root_path = "D:\\Workspace\\Python\\Stocks"
stockdata_path = os.path.join(root_path, "stock_data")
backtestfile_path = os.path.join(root_path, "MACD_Model_BackTest_Result.csv")

def MACD_Model_BackTest():
    filenames = os.listdir(stockdata_path)
    for filename in filenames:
#        print(filename)
        filepath = os.path.join(stockdata_path, filename)
        with open(filepath, "r") as fp:
            reader = csv.reader(fp)
            stock_data_list = list(reader)
            dropcounter = 0
            EMA_12_list = [0]
            EMA_26_list = [0]
            DIFF_list = [0]
            DEA_9_list = [0]
            MACD_list = [0]
            isBuy = False
            buy_price = 0
            for ii in range(len(stock_data_list), 1, -1):
                closing_price = float(stock_data_list[ii][3])
                EMA_12 = 11/13*EMA_12_list[-1] + 2/13*closing_price
                EMA_26 = 25/27*EMA_26_list[-1] + 2/27*closing_price
                DIFF = EMA_12 - EMA_26
                DEA_9 = 8/10*DEA_9_list[-1] + 2/10*DIFF
                MACD = (DIFF-DEA_9)*2
                EMA_12_list.append(EMA_12)
                EMA_26_list.append(EMA_26)
                DIFF_list.append(DIFF)
                DEA_9_list.append(DEA_9)
                MACD_list.append(MACD)
                if((DIFF_list[-2]<DEA_9_list[-2]) and (DIFF_list[-1]>DEA_9_list[-1]) and (DIFF_list[-1]<0) and (DEA_9_list[-1]<0)):
                    for jj in range(ii-1, 2, -1):
                        try:
                            buy_price = float(stock_data_list[jj][6])
                            isBuy = True
                        except:
                            break
                if((DIFF_list[-2]>DEA_9_list[-2]) and (DIFF_list[-1]<DEA_9_list[-1]) and isBuy):
                    isBuy = False
                    try:
                        sell_price = float(stock_data_list[ii+1][6])
                    except:
                        break


if __name__ == "__main__":