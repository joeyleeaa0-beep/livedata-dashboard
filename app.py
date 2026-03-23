import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="直播数据看板", page_icon="📊", layout="wide")
st.title("📊 直播数据看板")

APP_ID = st.secrets["FEISHU_APP_ID"]
APP_SECRET = st.secrets["FEISHU_APP_SECRET"]
APP_TOKEN = "Cmt7b5aNYaDS6UsboTBcLlVBnBc"
TABLE_ID = "tbl76AkkVBxARYt8"

@st.cache_data(ttl=300)
def get_token():
    res = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}
    )
    return res.json().get("tenant_access_token")

@st.cache_data(ttl=300)
def get_data():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    records = []
    page_token = None
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        res = requests.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records",
            headers=headers, params=params
        ).json()
        items = res.get("data", {}).get("items", [])
        for item in items:
            fields = item.get("fields", {})
            records.append(fields)
        if not res.get("data", {}).get("has_more"):
            break
        page_token = res["data"].get("page_token")
    return pd.DataFrame(records)

with st.spinner("正在加载数据..."):
    try:
        df = get_data()
        if df.empty:
            st.warning("暂无数据，请检查飞书表格权限设置")
            st.stop()
        # 处理日期
        if "日期" in df.columns:
            df["日期"] = pd.to_datetime(df["日期"].apply(
                lambda x: x/1000 if isinstance(x, (int, float)) else x
            ), unit="s", errors="coerce")
        # 数值列转换
        num_cols = ["总客资", "广告客资", "自然流客资", "广告投放", "涨粉量", "最高在线人数"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    except Exception as e:
        st.error(f"数据加载失败：{e}")
        st.stop()

# 侧边栏筛选
st.sidebar.header("🔍 筛选条件")
if "日期" in df.columns:
    valid_dates = df["日期"].dropna()
    if not valid_dates.empty:
        date_range = st.sidebar.date_input(
            "选择日期范围",
            [valid_dates.min().date(), valid_dates.max().date()]
        )
        if len(date_range) == 2:
            df = df[
                (df["日期"] >= pd.Timestamp(date_range[0])) &
                (df["日期"] <= pd.Timestamp(date_range[1]))
            ]

if "账号" in df.columns:
    accounts = ["全部"] + sorted(df["账号"].dropna().astype(str).unique().tolist())
    sel = st.sidebar.selectbox("选择账号", accounts)
    if sel != "全部":
        df = df[df["账号"].astype(str) == sel]

if "月份" in df.columns:
    months = ["全部"] + sorted(df["月份"].dropna().astype(str).unique().tolist())
    sel_m = st.sidebar.selectbox("选择月份", months)
    if sel_m != "全部":
        df = df[df["月份"].astype(str) == sel_m]

st.sidebar.markdown(f"📋 当前数据：**{len(df)}** 条")

# 核心指标
st.subheader("📈 核心指标总览")
c1, c2, c3, c4 = st.columns(4)
c1.metric("总客资", f"{int(df['总客资'].sum()):,}" if "总客资" in df.columns else "N/A")
c2.metric("广告客资", f"{int(df['广告客资'].sum()):,}" if "广告客资" in df.columns else "N/A")
c3.metric("总涨粉量", f"{int(df['涨粉量'].sum()):,}" if "涨粉量" in df.columns else "N/A")
c4.metric("广告投放总额", f"¥{df['广告投放'].sum():,.2f}" if "广告投放" in df.columns else "N/A")

st.divider()

# 趋势图
st.subheader("📉 数据趋势")
if "日期" in df.columns and "总客资" in df.columns:
    trend = df.groupby("日期")[["总客资", "广告客资"]].sum().reset_index()
    st.plotly_chart(px.line(trend, x="日期", y=["总客资", "广告客资"], title="客资每日趋势"), use_container_width=True)

c_a, c_b = st.columns(2)
with c_a:
    if "日期" in df.columns and "涨粉量" in df.columns:
        fans = df.groupby("日期")["涨粉量"].sum().reset_index()
        st.plotly_chart(px.bar(fans, x="日期", y="涨粉量", title="每日涨粉量"), use_container_width=True)
with c_b:
    if "账号" in df.columns and "总客资" in df.columns:
        acc = df.groupby("账号")["总客资"].sum().reset_index()
        st.plotly_chart(px.pie(acc, names="账号", values="总客资", title="各账号客资占比"), use_container_width=True)

st.divider()
st.subheader("📋 数据明细")
st.dataframe(df, use_container_width=True)
