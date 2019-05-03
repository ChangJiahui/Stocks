import requests
import random
from bs4 import BeautifulSoup as bs
import time
import os
import csv


root_path = "D:\\Workspace\\Python\\Stocks"
stockdata_path = os.path.join(root_path, "Data", "stock_data_history")
backtestfile_path = os.path.join(root_path, "MACD_Model_BackTest_Result.csv")

def MACD_Model_BackTest():
    filenames = os.listdir(stockdata_path)
    for filename in filenames:
        print(filename)
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
            isBuy = False
            buy_date = ""
            buy_price = 0
            for ii in reversed(range(1, len(stock_data_list)-1)):
                print(stock_data_list[ii])
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
                    buy_date = stock_data_list[ii-1][0]
                    buy_price = float(stock_data_list[ii-1][6])
                    isBuy = True
                if((DIFF_list[-2]>DEA_9_list[-2]) and (DIFF_list[-1]<DEA_9_list[-1]) and isBuy):
                    sell_date = stock_data_list[ii-1][0]
                    sell_price = float(stock_data_list[ii-1][6])
                    profit = (sell_price - buy_price) / (buy_price)
                    isBuy = False
                    with open(backtestfile_path, "a") as fp:
                        fp.write(str(filename) + "," + str(buy_date) + "," + str(buy_price) + "," + str(sell_date) + "," + str(sell_price) + "," + str(profit) + ",\n")


if __name__ == "__main__":
    with open(backtestfile_path, 'w') as fp:
        fp.write("股票名称,购买日期,购买价格,卖出日期,卖出价格,盈利比例\n")
    MACD_Model_BackTest()