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

def parse_field(val):
    if val is None:
        return None
    if isinstance(val, list):
        parts = []
        for v in val:
            if isinstance(v, dict):
                parts.append(v.get("text", v.get("name", str(v))))
            else:
                parts.append(str(v))
        return ", ".join(parts)
    if isinstance(val, dict):
        return val.get("text", val.get("name", str(val)))
    return val

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
            parsed = {k: parse_field(v) for k, v in fields.items()}
            records.append(parsed)
        if not res.get("data", {}).get("has_more"):
            break
        page_token = res["data"].get("page_token")
    return pd.DataFrame(records)

with st.spinner("正在加载数据..."):
    try:
        df = get_data()
        if df.empty:
            st.warning("暂无数据")
            st.stop()
        # 处理日期
        if "日期" in df.columns:
            df["日期"] = pd.to_datetime(
                df["日期"].apply(lambda x: x/1000 if isinstance(x, (int, float)) else x),
                unit="s", errors="coerce"
            )
        # 数值列
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
    valid = df["日期"].dropna()
    if not valid.empty:
        dr = st.sidebar.date_input("选择日期范围", [valid.min().date(), valid.max().date()])
        if len(dr) == 2:
            df = df[(df["日期"] >= pd.Timestamp(dr[0])) & (df["日期"] <= pd.Timestamp(dr[1]))]

if "账号" in df.columns:
    opts = ["全部"] + sorted(df["账号"].dropna().astype(str).unique().tolist())
    sel = st.sidebar.selectbox("选择账号", opts)
    if sel != "全部":
        df = df[df["账号"].astype(str) == sel]

if "月份" in df.columns:
    mopts = ["全部"] + sorted(df["月份"].dropna().astype(str).unique().tolist())
    sm = st.sidebar.selectbox("选择月份", mopts)
    if sm != "全部":
        df = df[df["月份"].astype(str) == sm]

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
    cols_to_plot = [c for c in ["总客资", "广告客资"] if c in df.columns]
    trend = df.groupby("日期")[cols_to_plot].sum().reset_index()
    st.plotly_chart(px.line(trend, x="日期", y=cols_to_plot, title="客资每日趋势"), use_container_width=True)

ca, cb = st.columns(2)
with ca:
    if "日期" in df.columns and "涨粉量" in df.columns:
        fans = df.groupby("日期")["涨粉量"].sum().reset_index()
        st.plotly_chart(px.bar(fans, x="日期", y="涨粉量", title="每日涨粉量"), use_container_width=True)
with cb:
    if "账号" in df.columns and "总客资" in df.columns:
        acc = df.groupby("账号")["总客资"].sum().reset_index()
        st.plotly_chart(px.pie(acc, names="账号", values="总客资", title="各账号客资占比"), use_container_width=True)

st.divider()
st.subheader("📋 数据明细")
st.dataframe(df, use_container_width=True)
