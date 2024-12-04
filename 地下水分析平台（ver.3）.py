import streamlit as st
import pandas as pd
#import matplotlib.pyplot as plt
from io import BytesIO
from streamlit_option_menu import option_menu
import os


# =============================================================================
# 更新日志：增加侧边栏功能，将污染指数计算功能移动到独立的栏目;删除综合分析，现状评价增加报告内容
# =============================================================================

# 设置 Streamlit 界面标题
st.title("地下水环境质量数据快速分析平台")
# 获取当前Python脚本文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 构建与当前Python脚本文件同目录下的图片路径
logo_path = os.path.join(current_dir, '华南所logo-011.jpg')
# 设置侧边栏选项菜单
with st.sidebar:
    st.image(logo_path)
    selected = option_menu(
        menu_title="功能选择",
        options=["检测数据分析", "污染指数计算"],
        icons=["clipboard-data", "calculator"],
        menu_icon="boxes",
        default_index=0,
    )

# 上传地下水检测数据文件
uploaded_file = st.file_uploader("上传地下水检测数据文件", type=["xlsx"])

# 构建与当前Python脚本文件同目录下的图片路径
file_path = os.path.join(current_dir, '地下水质量标准.xlsx')
groundwater_standards = pd.read_excel(file_path)
groundwater_standards['指标'] = groundwater_standards['指标'].str.strip()  #str.replace(r'\(.*\)', '', regex=True)  不用去除括号了

if uploaded_file is not None:
    data_df = pd.read_excel(uploaded_file, sheet_name='Sheet1')
    
    if selected == "检测数据分析":
        # 用户选择对比标准
        standard_type = st.selectbox("选择对比标准", ["I类", "Ⅱ类", "Ⅲ类", "IV类", "V类", "现状评价"], key='selectbox_standard_type_2_uniq')

        # 初始化结果列表
        results = []
        exceedance_data = {}
        pollutant_summary = {}

        if standard_type == "现状评价":
            # 现状评价逻辑
            report_content = []
            for index, row in data_df.iterrows():
                result_row = {'样品编号': row['样品编号']}
                sample_id = row['样品编号']
                evaluation_details = []
                for _, standard in groundwater_standards.iterrows():
                    pollutant = standard['指标']
                    if pollutant in row:
                        concentration = row[pollutant]
                        if concentration == 'ND':
                            concentration = 0
                        class_status = "V"
                        # 从最严格的I依次向下判断是否满足标准
                        for class_type in ["I类", "Ⅱ类", "Ⅲ类", "IV类", "V类"]:
                            try:
                                limit_value = float(standard[class_type])
                                if concentration <= limit_value:
                                    class_status = class_type.replace('类', '')
                                    break
                            except (ValueError, TypeError):
                                continue
                        result_row[pollutant] = class_status
                        evaluation_details.append(f"{pollutant}为{class_status}类")
                results.append(result_row)

                # 生成报告内容
                if evaluation_details:
                    report_content.append(f"样品编号 {sample_id} 中的各项指标：{'，'.join(evaluation_details)}。")

            # 将结果保存到新的 DataFrame
            results_df = pd.DataFrame(results)

            # 显示现状评价结果表格
            st.subheader("现状评价结果")
            st.dataframe(results_df, use_container_width=True)
            st.warning('pH的现状评价数据会出现bug，请自行核对修改')

            # 显示表头并提供复制功能，列名用制表符分隔
            st.text_area("表头可以在下方复制", value="\t".join(results_df.columns), height=50)
                # 生成报告内容
            if evaluation_details:
                report_content.append(f"样品编号 {sample_id} 中的各项指标：{'，'.join(evaluation_details)}。")
                    
        if standard_type in ["I类", "Ⅱ类", "Ⅲ类", "IV类", "V类"]:
            # 过滤出用户选择的标准列
            selected_standard = groundwater_standards[['指标', '单位', standard_type]].copy()
            selected_standard.columns = ['指标', '单位', '限值']
            selected_standard.dropna(subset=['指标', '限值'], inplace=True)

            # 遍历每一行数据进行超标判断
            for index, row in data_df.iterrows():
                result_row = {'样品编号': row['样品编号']}
                sample_id = row['样品编号']
                if sample_id not in exceedance_data:
                    exceedance_data[sample_id] = []
                for _, standard in selected_standard.iterrows():
                    pollutant = standard['指标']
                    limit_value = standard['限值']
                    if pollutant in row:
                        concentration = row[pollutant]
                        try:
                            limit_value = float(limit_value)
                            if concentration > limit_value:
                                exceedance_ratio = concentration / limit_value
                                result_row[pollutant] = f"{concentration} (超标 {exceedance_ratio - 1:.2f} 倍)"
                                exceedance_data[sample_id].append({
                                    '污染物': pollutant,
                                    '超标倍数': exceedance_ratio
                                })
                                if pollutant not in pollutant_summary:
                                    pollutant_summary[pollutant] = {
                                        '超标点位数': 0,
                                        '最大超标倍数': 0
                                    }
                                pollutant_summary[pollutant]['超标点位数'] += 1
                                pollutant_summary[pollutant]['最大超标倍数'] = max(pollutant_summary[pollutant]['最大超标倍数'], exceedance_ratio)
                            else:
                                result_row[pollutant] = f"{concentration} (未超标)"
                        except (ValueError, TypeError):
                            result_row[pollutant] = concentration

                results.append(result_row)

            # 将结果保存到新的 DataFrame
            results_df = pd.DataFrame(results)

            # 显示结果表格
            st.subheader("检测结果")
            st.dataframe(results_df, use_container_width=True)
            st.text_area("表头可以在下方复制", value="\t".join(results_df.columns), height=50)

            # 生成报告内容
            report_content = []
            total_samples = len(data_df)
            # for pollutant, summary in pollutant_summary.items():
            #     exceedance_rate = (summary['超标点位数'] / total_samples) * 100
            #     report_content.append(f"{summary['超标点位数']}个检测点位存在{pollutant}超标情况，超标率达到{exceedance_rate:.2f}% ，最大超标倍数为{summary['最大超标倍数'] - 1:.2f}。")
            # 添加每个点位的超标信息
            for sample_id, pollutants in exceedance_data.items():
                if pollutants:
                    pollutant_list = "、".join([p['污染物'] for p in pollutants])
                    exceedance_details = "，".join([f"{p['污染物']}超标 {p['超标倍数'] - 1:.2f} 倍" for p in pollutants])
                    report_content.append(f"样品编号 {sample_id} 中的 {pollutant_list} 超标，其中{exceedance_details}。")
            for pollutant, summary in pollutant_summary.items():
                exceedance_rate = (summary['超标点位数'] / total_samples) * 100
                report_content.append(f"{summary['超标点位数']}个检测点位存在{pollutant}超标情况，超标率达到{exceedance_rate:.2f}% ，最大超标倍数为{summary['最大超标倍数'] - 1:.2f}。")
        
        st.markdown("### 报告内容")
        if report_content:
            st.text_area("可复制下方报告内容", value="\n".join(report_content), height=300)
        else:
            st.text_area("可复制下方报告内容", value="所有样品均未超标。", height=100)

    elif selected == "污染指数计算":
        # 用户选择对比标准
        standard_type = st.selectbox("选择对比标准", ["I类", "Ⅱ类", "Ⅲ类", "IV类", "V类"], key='selectbox_standard_type_1_uniq')
        
        # 过滤出用户选择的标准列
        selected_standard = groundwater_standards[['指标', '单位', standard_type]].copy()
        selected_standard.columns = ['指标', '单位', '限值']
        
        # 去掉空值（如表格中的空行）
        selected_standard.dropna(subset=['指标', '限值'], inplace=True)
        
        # 获取监测数据
        exceedance_data = {}
        for index, row in data_df.iterrows():
            sample_id = row['样品编号']
            exceedance_data[sample_id] = []
            for _, standard in selected_standard.iterrows():
                pollutant = standard['指标']
                limit_value = standard['限值']
                if pollutant in row:
                    concentration = row[pollutant]
                    try:
                        limit_value = float(limit_value)
                        if concentration > limit_value:
                            exceedance_data[sample_id].append(pollutant)
                    except (ValueError, TypeError):
                        continue

        # 用户输入超标指标的背景值
        # 用户输入超标指标的背景值
        st.markdown("请输入所有超标指标的背景点浓度：")
        background_concentrations = {}
        
        # 提取超标的污染物，并确保顺序与用户上传的数据保持一致
        unique_pollutants_ordered = [col for col in data_df.columns if col in selected_standard['指标'].values and any(col in pollutants for pollutants in exceedance_data.values())]
        
        for pollutant in unique_pollutants_ordered:
            background_concentrations[pollutant] = st.number_input(
                f"{pollutant} 背景点浓度", 
                min_value=0.0, 
                step=0.01,
                key=f"background_concentration_{pollutant}"
            )
        
        # 计算污染指数
        pollution_index_data = []
        for sample_id, pollutants in exceedance_data.items():
            for pollutant in pollutants:
                concentration = data_df.loc[data_df['样品编号'] == sample_id, pollutant].values[0]
                background_concentration = background_concentrations.get(pollutant, 0)
                limit_value = selected_standard.loc[selected_standard['指标'] == pollutant, '限值'].values[0]
                pollution_index = (concentration - background_concentration) / limit_value

                # 确定污染级别
                if pollution_index < 0:
                    pollution_level = "I级，未污染"
                elif 0 < pollution_index <= 0.2:
                    pollution_level = "II级，轻污染"
                elif 0.2 < pollution_index <= 0.6:
                    pollution_level = "III级，中污染"
                elif 0.6 < pollution_index <= 1.0:
                    pollution_level = "IV级，较重污染"
                elif 1.0 < pollution_index <= 1.5:
                    pollution_level = "V级，严重污染"
                else:  # pollution_index >= 1.5
                    pollution_level = "VI级，极重污染"

                pollution_index_data.append([sample_id, pollutant, pollution_index])
        
        pollution_index_df = pd.DataFrame(pollution_index_data, columns=['检测点位', '污染物指标', '污染指数'])
        st.dataframe(pollution_index_df, use_container_width=True)

else:
    st.markdown("请上传地下水检测数据，列名需包括样品编号和各项污染物指标，每行为一个样本。")
