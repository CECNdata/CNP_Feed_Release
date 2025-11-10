#!/usr/bin/env python
# coding=utf-8
import pandas as pd
import os
import re
import datetime

## diy option
fill_zero_bit = int(os.getenv("fill_zero_bit", 2))
base_dir   = os.getenv("base_dir", "./CNP-Customs-total-export-RMB")
target_dir = os.getenv("target_dir", "./")
date_range = int(os.getenv("date_range", 24))


# init setup
filter_files=[]
filter_date_part=[]
final_csv=f"{base_dir.split('/')[-1]}.csv"
target_path=os.path.join(target_dir,final_csv)
try:
    os.remove(target_path)
except:pass

# generate date_list for 24 month
def get_last_month(month):
    last_month  = month.replace(day=1)
    last_month -= datetime.timedelta(days=1)
    return(last_month)
today   = datetime.datetime.utcnow()
cn_date = today + datetime.timedelta(hours = 8)
date_list=[cn_date]
for i in range(date_range):
    last_month = get_last_month(date_list[-1])
    date_list.append(last_month)
date_list=date_list[1:]
date_list=[x.strftime("%Y_%-m_%-m") for x in date_list]

# start working
files=os.listdir(base_dir)
files=sorted(files, key=lambda x: x.split(".")[-2], reverse=True) # sort by download time
for file in files:
    date = re.findall("20\d{2}_\d{1,2}_\d{1,2}",file)[0] #year_startMonth_endMonth
    part = re.findall("part\d*",file)[0] 
    date_part = f"{date}_{part}"
    if date_part not in filter_date_part and date in date_list:
        filter_date_part.append(date_part)
        filter_files.append(file)

filter_files=sorted(filter_files, key=lambda x: re.findall("20\d{2}_\d{1,2}_\d{1,2}",x)[0] , reverse=True) # sort by download time
#for i in filter_files:
#    print(i)

for f in filter_files:
    # fill zero digit
    df=pd.read_csv(os.path.join(base_dir,f))
    try:
        if '商品编码' in df.columns:
            df['商品编码']=df['商品编码'].apply(lambda x : ('{:0>'+str(fill_zero_bit)+'d}').format(x))
        elif 'Commodity code' in df.columns:
            df['Commodity code']=df['Commodity code'].apply(lambda x : ('{:0>'+str(fill_zero_bit)+'d}').format(x))
    except:pass

    # add date column
    date = re.findall("20\d{2}_\d{1,2}",f)[0] #year_startMonth_endMonth
    date = date+"_1"
    date = datetime.datetime.strptime(date,"%Y_%m_%d")
    date = datetime.datetime.strftime(date,"%Y-%m-%d")
    
    if '商品编码' in df.columns:
        df["时间"]=date
        df_date=df["时间"]
        df_date=df.pop("时间")
        df.insert(0,'时间',df_date)
        if "数据年月" in df.columns:
            df = df.drop(columns=["数据年月"])

    last_col = df.columns[-1]
    # 去除逗号并转换为数字
    def safe_convert(val):
        try:
            return float(str(val).replace(',', ''))
        except ValueError:
            return val  # 保留原始值

    df[last_col] = df[last_col].apply(safe_convert)

    # write to 1 csv
    if not os.path.exists(target_path):
        df.to_csv(target_path, index=False)
    else:
        df.to_csv(target_path, mode='a', header=False,  index=False)
