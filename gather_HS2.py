#!/usr/bin/env python
# coding=utf-8
import pandas as pd
import os
import re
import datetime
import dateutil.relativedelta  # 需安装：pip install python-dateutil
from typing import Optional, Dict, List, Tuple

# ===================== 环境变量配置 =====================
# 商品编码补零位数
try:
    FILL_ZERO_BIT = int(os.getenv("fill_zero_bit", 2))
except (ValueError, TypeError):
    FILL_ZERO_BIT = 2

# 源目录/目标目录
BASE_DIR = os.getenv("base_dir", "./")
TARGET_DIR = os.getenv("target_dir", "./")

# 月份范围（核心：0=所有月份，N=倒推N个月）
try:
    month_range = int(os.getenv("month_range", 0))
except (ValueError, TypeError):
    month_range = 0

# 固定配置
CSV_ENCODING = "utf-8-sig"
FIXED_SUFFIX = "001"

# ========== 工具函数 ==========
def safe_fill_zero(code: any, fill_bit: int) -> str:
    """商品编码补零"""
    try:
        code_str = str(code).strip()
        if code_str.isdigit():
            return code_str.zfill(fill_bit)
        return code_str
    except Exception:
        return code

def safe_convert_numeric(val: any) -> any:
    """数值列清洗"""
    try:
        val_str = str(val).strip().replace(",", "")
        return float(val_str)
    except (ValueError, TypeError):
        return val

def extract_file_info(filename: str) -> tuple[Optional[str], Optional[str], Optional[str], Optional[datetime.datetime]]:
    """
    提取文件关键信息
    返回：(前缀, 年月(YYYYMM), part编号, 时间戳)
    """
    try:
        # 1. 提取前缀（HS2_xxx_xxx_xxx）
        prefix_match = re.search(r"(HS2_[a-zA-Z0-9]+_[a-zA-Z0-9]+_[a-zA-Z0-9]+)", filename)
        if not prefix_match:
            return None, None, None, None
        prefix = prefix_match.group(1)
        
        # 2. 提取年月（YYYY_MM → YYYYMM）
        date_match = re.search(r"20\d{2}_\d{1,2}", filename)
        if not date_match:
            return prefix, None, None, None
        date_str = date_match.group()
        year, month = date_str.split("_")
        month = month.zfill(2)
        yyyymm = f"{year}{month}"
        
        # 3. 提取part编号（part0 → 0）
        part_match = re.search(r"part(\d+)", filename)
        if not part_match:
            return prefix, yyyymm, None, None
        part_num = part_match.group(1)
        
        # 4. 提取时间戳
        timestamp_match = re.search(r"(\d{14})T\+\d", filename)
        if not timestamp_match:
            return prefix, yyyymm, part_num, None
        timestamp_str = timestamp_match.group(1)
        file_timestamp = datetime.datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
        
        return prefix, yyyymm, part_num, file_timestamp
    except Exception as e:
        print(f"⚠️ 解析文件名 {filename} 失败：{e}")
        return None, None, None, None

def get_target_months(month_range: int) -> List[str]:
    """
    根据month_range动态计算目标月份
    - month_range=0 → 返回空列表（表示所有月份）
    - month_range=N → 返回当前月份往前倒推N个月的YYYYMM列表（不含当前月）
    示例：当前2026-03，month_range=2 → 返回 ["202602", "202601"]
    """
    if month_range == 0:
        return []  # 空列表表示不筛选月份
    
    target_months = []
    today = datetime.datetime.now()
    current_month = datetime.datetime(today.year, today.month, 1)
    
    # 倒推N个月（不含当前月）
    for i in range(1, month_range + 1):
        target_month = current_month - dateutil.relativedelta.relativedelta(months=i)
        target_months.append(target_month.strftime("%Y%m"))
    
    print(f"📅 动态计算目标月份：month_range={month_range} → {target_months}")
    return target_months

# ========== 核心分组函数 ==========
def get_latest_part_files(file_list: List[str], target_months: List[str]) -> Dict[str, List[str]]:
    """
    核心逻辑：
    1. 按「前缀+年月+part」分组，取每个part的最新时间戳文件
    2. 按「前缀+年月」汇总所有part的最新文件
    """
    # 步骤1：按「前缀+年月+part」分组，暂存每个part的所有文件和时间戳
    part_groups: Dict[str, List[Tuple[str, datetime.datetime]]] = {}
    for file_path in file_list:
        filename = os.path.basename(file_path)
        prefix, yyyymm, part_num, file_timestamp = extract_file_info(filename)
        
        # 过滤条件1：信息必须完整
        if not prefix or not yyyymm or not part_num or not file_timestamp:
            continue
        
        # 过滤条件2：如果有目标月份，仅保留目标月份的文件
        if target_months and yyyymm not in target_months:
            continue
        
        # 生成part级分组key（如：HS2_PC_RMB_EXP_202602_0）
        part_key = f"{prefix}_{yyyymm}_{part_num}"
        if part_key not in part_groups:
            part_groups[part_key] = []
        part_groups[part_key].append((file_path, file_timestamp))
    
    # 步骤2：取每个part的最新文件，并按「前缀+年月」汇总
    final_groups: Dict[str, List[str]] = {}
    for part_key, file_with_ts in part_groups.items():
        # 提取「前缀+年月」（如：HS2_PC_RMB_EXP_202602）
        prefix_yyyymm = "_".join(part_key.split("_")[:-1])
        # 取该part的最新时间戳文件
        max_ts = max([ts for _, ts in file_with_ts])
        latest_file = [fp for fp, ts in file_with_ts if ts == max_ts][0]
        
        # 汇总到「前缀+年月」分组
        if prefix_yyyymm not in final_groups:
            final_groups[prefix_yyyymm] = []
        final_groups[prefix_yyyymm].append(latest_file)
    
    # 打印分组结果
    for group_key, files in final_groups.items():
        part_count = len(files)
        file_names = [os.path.basename(f) for f in files]
        print(f"✅ 分组 {group_key}：找到 {part_count} 个part的最新文件 → {file_names}")
    
    return final_groups

# ========== 文件合并函数 ==========
def merge_latest_part_files(file_group: List[str], group_key: str, target_dir: str) -> None:
    """合并同一年月下所有part的最新文件"""
    print(f"\n🔨 开始合并：{group_key}（{len(file_group)}个part的最新文件）")
    
    df_list = []
    for idx, file_path in enumerate(file_group):
        filename = os.path.basename(file_path)
        try:
            df = pd.read_csv(file_path, encoding=CSV_ENCODING)
            df_list.append(df)
            print(f"✅ Part{idx} 读取成功：{filename}（行数：{len(df)}）")
        except Exception as e:
            print(f"❌ Part{idx} 读取失败：{filename} - {e}")
            continue
    
    if not df_list:
        print(f"❌ {group_key} 无有效文件，跳过合并")
        return
    
    # 合并所有part的最新文件
    merged_df = pd.concat(df_list, ignore_index=True)
    print(f"✅ 合并完成：总行数 {len(merged_df)}")
    
    # 数据清洗（可选）
    try:
        # 商品编码补零
        if '商品编码' in merged_df.columns:
            merged_df['商品编码'] = merged_df['商品编码'].apply(lambda x: safe_fill_zero(x, FILL_ZERO_BIT))
        elif 'Commodity code' in merged_df.columns:
            merged_df['Commodity code'] = merged_df['Commodity code'].apply(lambda x: safe_fill_zero(x, FILL_ZERO_BIT))
        
        # 添加年月列
        yyyymm = group_key.split("_")[-1]
        merged_df["数据年月"] = yyyymm
    except Exception as e:
        print(f"⚠️ 数据清洗失败：{e}")
    
    # 保存最终文件
    output_file = f"{group_key}_{FIXED_SUFFIX}.csv"
    output_path = os.path.join(target_dir, output_file)
    try:
        merged_df.to_csv(output_path, index=False, encoding=CSV_ENCODING)
        print(f"✅ 保存成功：{output_file}\n")
    except Exception as e:
        print(f"❌ 保存失败：{e}\n")

# ========== 主函数 ==========
def main():
    print("===== HS2文件合并工具（支持month_range动态筛选） =====")
    print(f"📌 配置参数：")
    print(f"   - 源目录：{BASE_DIR}")
    print(f"   - 目标目录：{TARGET_DIR}")
    print(f"   - month_range：{month_range}（0=所有月份，N=倒推N个月）")
    print("======================================================\n")
    
    # 检查源目录
    if not os.path.exists(BASE_DIR):
        print(f"❌ 源目录不存在：{BASE_DIR}")
        return
    
    # 步骤1：递归扫描所有HS2子目录的CSV文件
    csv_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        if "HS2" in os.path.basename(root):
            for file in files:
                if file.endswith(".csv"):
                    csv_files.append(os.path.join(root, file))
    
    if not csv_files:
        print("❌ 未找到任何HS2 CSV文件")
        return
    print(f"✅ 共扫描到 {len(csv_files)} 个CSV文件\n")
    
    # 步骤2：动态计算目标月份
    target_months = get_target_months(month_range)
    
    # 步骤3：获取每个part的最新文件，并汇总
    file_groups = get_latest_part_files(csv_files, target_months)
    if not file_groups:
        print("❌ 无符合条件的文件分组")
        return
    
    # 步骤4：合并每个年月的所有part最新文件
    for group_key, file_list in file_groups.items():
        merge_latest_part_files(file_list, group_key, TARGET_DIR)
    
    print("===== 所有文件处理完成！=====")

if __name__ == "__main__":
    main()
