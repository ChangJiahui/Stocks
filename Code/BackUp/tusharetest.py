import tushare as ts
import os

root_path = "D:\\Workspace\\Python\\Stocks"
stockinfo_file = os.path.join(root_path, "Data", "stock_info.txt")
basic_file = ""
ts.set_token("119921ff45f95fd77e5d149cd1e64e78572712b3d0a5ce38157f255b")
ts.pro_api()


def write_csvfile(filename, title, data_list):
    with open(filename, 'w') as fp:
        fp.write(",".join([str(item) for item in title]) + "\n")
        for row_item in data_list:
            fp.write(",".join([str(item) for item in row_item]) + "\n")


if __name__ == "__main__":
    df_todays = ts.get_today_all()
    title = ["股票名称", "市净率", "市盈率"]
    data_list = []
    with open(stockinfo_file, 'r') as fp:
        for stock_info in fp.readlines():
            if(stock_info):
                stock_info = stock_info.split()[0]
                stock_code = stock_info.split("_")[1][-6:]
                stock_df = df_todays[df_todays["code"].isin([stock_code])]
                if(stock_df.empty):
                    print("Data Error! " + stock_info)
                else:
                    stock_pe = stock_df["per"].values[0]
                    stock_pb = stock_df["pb"].values[0]
                    data_list.append([stock_info, stock_pb, stock_pe])
    write_csvfile(os.path.join(root_path, "test.csv"), title, data_list)
#    dfvalues = df_todays.values
#    print(dfvalues)
