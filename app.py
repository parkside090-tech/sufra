import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & CACHING
# -----------------------------------------------------------------------------
st.set_page_config(page_title="SufraEats Strategy", page_icon="🍽️", layout="wide")

@st.cache_data
def load_data():
    # Load the cleaned dataset you generated earlier
    try:
        df = pd.read_csv("sufraeats_cleaned_data.csv")
    except FileNotFoundError:
        st.error("Error: 'sufraeats_cleaned_data.csv' not found. Please ensure it is in the same directory as app.py")
        return pd.DataFrame()
    
    # Convert date to datetime object for time-series filtering
    df['date'] = pd.to_datetime(df['date'])
    return df

df = load_data()

if df.empty:
    st.stop()

# -----------------------------------------------------------------------------
# 2. SIDEBAR FILTERS (GLOBAL)
# -----------------------------------------------------------------------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/7541/7541900.png", width=100) # Mock logo
st.sidebar.header("🔍 Slice the Data")

# Date Range Filter
min_date = df['date'].min().date()
max_date = df['date'].min().date()
date_range = st.sidebar.date_input("Select Date Range", 
                                   value=(df['date'].min().date(), df['date'].max().date()),
                                   min_value=df['date'].min().date(),
                                   max_value=df['date'].max().date())

# Multiselect Filters
selected_zones = st.sidebar.multiselect("📍 Zone", options=sorted(df['zone'].dropna().unique()), default=sorted(df['zone'].dropna().unique()))
selected_cuisines = st.sidebar.multiselect("🍜 Cuisine", options=sorted(df['cuisine'].dropna().unique()), default=sorted(df['cuisine'].dropna().unique()))
selected_status = st.sidebar.multiselect("📦 Order Status", options=df['order_status'].unique(), default=df['order_status'].unique())
selected_channel = st.sidebar.multiselect("🛍️ Order Channel", options=df['order_channel'].unique(), default=df['order_channel'].unique())

# Apply Global Filters
if len(date_range) == 2:
    start_date, end_date = date_range
    mask = (
        (df['date'].dt.date >= start_date) & 
        (df['date'].dt.date <= end_date) &
        (df['zone'].isin(selected_zones)) &
        (df['cuisine'].isin(selected_cuisines)) &
        (df['order_status'].isin(selected_status)) &
        (df['order_channel'].isin(selected_channel))
    )
    filtered_df = df.loc[mask]
else:
    filtered_df = df.copy()

# -----------------------------------------------------------------------------
# 3. DASHBOARD HEADER & KPIS
# -----------------------------------------------------------------------------
st.title("🍽️ SufraEats Expansion Dashboard")
st.markdown("""
**Where Should We Grow Next?** *This dashboard evaluates true zone health by moving past "Gross Sales" to measure what SufraEats actually keeps (Realised Revenue) and how customers actually experience the service.*
""")
st.markdown("---")

# Calculate Headline Metrics
total_orders = len(filtered_df)
realised_revenue = filtered_df['sufraeats_net_revenue'].sum()
avg_rating = filtered_df['rating'].mean()
cancellations = len(filtered_df[filtered_df['order_status'] == 'Cancelled'])
cancellation_rate = (cancellations / total_orders * 100) if total_orders > 0 else 0

# Display KPIs in 4 columns
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(label="Total Orders", value=f"{total_orders:,}")
kpi2.metric(label="Realised Revenue", value=f"{realised_revenue:,.0f} AED")
kpi3.metric(label="Average Rating", value=f"{avg_rating:.2f} ⭐")
kpi4.metric(label="Cancellation Rate", value=f"{cancellation_rate:.1f}%")

st.markdown("---")

# -----------------------------------------------------------------------------
# 4. CHARTS & VISUALIZATIONS
# -----------------------------------------------------------------------------

row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.subheader("1. Zone Health: Gross Sales vs. Realised Revenue")
    st.markdown("Identifies zones with high revenue leakage (discounts, refunds, cancellations).")
    
    # Aggregate data for Chart 1
    zone_rev = filtered_df.groupby('zone').agg(
        Gross_Sales=('basket_value', 'sum'),
        Realised_Revenue=('sufraeats_net_revenue', 'sum')
    ).reset_index().melt(id_vars='zone', value_vars=['Gross_Sales', 'Realised_Revenue'], var_name='Metric', value_name='AED')
    
    fig1 = px.bar(zone_rev, x='zone', y='AED', color='Metric', barmode='group',
                  color_discrete_sequence=['#B0BEC5', '#FF4B4B'])
    fig1.update_layout(xaxis_title="Dubai Zone", yaxis_title="Revenue (AED)", legend_title=None)
    st.plotly_chart(fig1, use_container_width=True)

with row1_col2:
    st.subheader("2. Customer Experience: Delivery Time vs Rating")
    st.markdown("Visualizes operational efficiency. Top-performing zones sit in the top-left quadrant.")
    
    # Aggregate data for Chart 2
    cx_df = filtered_df[filtered_df['order_channel'] == 'Delivery'].groupby('zone').agg(
        Avg_Delivery_Time=('delivery_time_min', 'mean'),
        Avg_Rating=('rating', 'mean'),
        Total_Orders=('order_id', 'count')
    ).reset_index()
    
    fig2 = px.scatter(cx_df, x='Avg_Delivery_Time', y='Avg_Rating', size='Total_Orders', color='zone',
                      hover_name='zone', text='zone', size_max=40)
    fig2.update_traces(textposition='top center')
    fig2.update_layout(xaxis_title="Avg Delivery Time (mins)", yaxis_title="Avg Customer Rating")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.subheader("3. Partnership Priority: Cuisine Breakdown")
    st.markdown("Which cuisines are driving the highest realized revenue on the platform?")
    
    # Aggregate data for Chart 3
    cuisine_rev = filtered_df.groupby('cuisine')['sufraeats_net_revenue'].sum().reset_index()
    fig3 = px.pie(cuisine_rev, values='sufraeats_net_revenue', names='cuisine', hole=0.4,
                  color_discrete_sequence=px.colors.sequential.Sunsetdark)
    st.plotly_chart(fig3, use_container_width=True)

with row2_col2:
    st.subheader("4. Time & Seasonality: Hourly Order Demand")
    st.markdown("Tracks when order volumes peak across the day.")
    
    # Local filter for the trend chart
    show_ramadan = st.radio("Overlay Ramadan Effect?", ['All Data', 'Ramadan Only', 'Non-Ramadan Only'], horizontal=True)
    
    # Apply local filter logic
    if show_ramadan == 'Ramadan Only':
        trend_df = filtered_df[filtered_df['is_ramadan'] == True]
    elif show_ramadan == 'Non-Ramadan Only':
        trend_df = filtered_df[filtered_df['is_ramadan'] == False]
    else:
        trend_df = filtered_df
        
    hourly_trend = trend_df.groupby('hour').size().reset_index(name='Order_Count')
    fig4 = px.line(hourly_trend, x='hour', y='Order_Count', markers=True,
                   color_discrete_sequence=['#FF4B4B'])
    fig4.update_layout(xaxis_title="Hour of Day (0-23)", yaxis_title="Total Orders")
    fig4.update_xaxes(dtick=2)
    st.plotly_chart(fig4, use_container_width=True)

# Footer Note
st.caption("Data source: SufraEats Operational Data (2025). Excludes ghost-restaurant entries and handles JLT/Jumeirah Lake Towers standardization.")
