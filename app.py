import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# 页面设置
st.set_page_config(page_title="直播数据看板", page_icon="📊", layout="wide")
st.title("📊 直播数据看板")

# 飞书API配置
APP_ID = st.secrets["FEISHU_APP_ID"]
APP_SECRET = st.secrets["FEISHU_APP_SECRET"]
APP_TOKEN = "Cmt7b5aNYaDS6UsboTBcLlVBnBc"
TABLE_ID = "tbl2qLySfJEvfQyj"

@st.cache_data(ttl=300)
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
    return res.json().get("tenant_access_token")

@st.cache_data(ttl=300)
def get_table_data():
    token = get_feishu_token()
    headers = {"Authorization": f"Bearer {token}"}
    records = []
    page_token = None
    while True:
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        res = requests.get(url, headers=headers, params=params).json()
        items = res.get("data", {}).get("items", [])
        for item in items:
            records.append(item["fields"])
        if not res.get("data", {}).get("has_more"):
            break
        page_token = res["data"]["page_token"]
    return pd.DataFrame(records)

# 读取数据
with st.spinner("正在加载数据..."):
    try:
        df = get_table_data()
        # 转换日期
        if "日期" in df.columns:
            df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
    except Exception as e:
        st.error(f"数据加载失败：{e}")
        st.stop()

# 侧边栏筛选
st.sidebar.header("🔍 筛选条件")

# 时间筛选
if "日期" in df.columns:
    min_date = df["日期"].min()
    max_date = df["日期"].max()
    date_range = st.sidebar.date_input("选择日期范围", [min_date, max_date])
    if len(date_range) == 2:
        df = df[(df["日期"] >= pd.Timestamp(date_range[0])) & 
                (df["日期"] <= pd.Timestamp(date_range[1]))]

# 账号筛选
if "账号" in df.columns:
    accounts = ["全部"] + sorted(df["账号"].dropna().unique().tolist())
    selected = st.sidebar.selectbox("选择账号", accounts)
    if selected != "全部":
        df = df[df["账号"] == selected]

# 月份筛选
if "月份" in df.columns:
    months = ["全部"] + sorted(df["月份"].dropna().unique().tolist())
    selected_month = st.sidebar.selectbox("选择月份", months)
    if selected_month != "全部":
        df = df[df["月份"] == selected_month]

st.sidebar.markdown(f"📋 当前数据：**{len(df)}** 条")

# 核心指标
st.subheader("📈 核心指标总览")
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_keizi = pd.to_numeric(df["总客资"], errors="coerce").sum() if "总客资" in df.columns else 0
    st.metric("总客资", f"{int(total_keizi):,}")

with col2:
    total_ad = pd.to_numeric(df["广告客资"], errors="coerce").sum() if "广告客资" in df.columns else 0
    st.metric("广告客资", f"{int(total_ad):,}")

with col3:
    total_fans = pd.to_numeric(df["涨粉量"], errors="coerce").sum() if "涨粉量" in df.columns else 0
    st.metric("总涨粉量", f"{int(total_fans):,}")

with col4:
    total_spend = pd.to_numeric(df["广告投放"], errors="coerce").sum() if "广告投放" in df.columns else 0
    st.metric("广告投放总额", f"¥{total_spend:,.2f}")

st.divider()

# 趋势图
st.subheader("📉 数据趋势")
if "日期" in df.columns and "总客资" in df.columns:
    trend_df = df.groupby("日期").agg(
        总客资=("总客资", lambda x: pd.to_numeric(x, errors="coerce").sum()),
        广告客资=("广告客资", lambda x: pd.to_numeric(x, errors="coerce").sum()),
    ).reset_index()
    fig = px.line(trend_df, x="日期", y=["总客资", "广告客资"], title="客资趋势")
    st.plotly_chart(fig, use_container_width=True)

col_a, col_b = st.columns(2)

with col_a:
    if "日期" in df.columns and "涨粉量" in df.columns:
        fans_df = df.groupby("日期").agg(
            涨粉量=("涨粉量", lambda x: pd.to_numeric(x, errors="coerce").sum())
        ).reset_index()
        fig2 = px.bar(fans_df, x="日期", y="涨粉量", title="每日涨粉量")
        st.plotly_chart(fig2, use_container_width=True)

with col_b:
    if "账号" in df.columns and "总客资" in df.columns:
        acc_df = df.groupby("账号").agg(
            总客资=("总客资", lambda x: pd.to_numeric(x, errors="coerce").sum())
        ).reset_index()
        fig3 = px.pie(acc_df, names="账号", values="总客资", title="各账号客资占比")
        st.plotly_chart(fig3, use_container_width=True)

st.divider()

# 明细表
st.subheader("📋 数据明细")
st.dataframe(df, use_container_width=True)
