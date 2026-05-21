import streamlit as st
import pandas as pd

# Set up page config
st.set_page_config(page_title="Lab Asset Dashboard", layout="wide")
st.title("🧪 Live Lab Asset Management Dashboard")
st.markdown("---")

# --- GOOGLE SHEETS LIVE CONNECTION LAYER ---
# Your exact Google Sheet URL formatted for raw CSV transmission
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1vN4IFkM2xlzA0G8oLV6yWo_sD9unOq_j8dYUP0wQMxg/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=60) # Refreshes data automatically every 60 seconds
def load_live_data(url):
    # Pulls the live rows directly from the Google Sheets backend
    return pd.read_csv(url)

with st.spinner("Fetching latest asset matrix from live database..."):
    df = load_live_data(SHEET_CSV_URL)

# Fill any blank spreadsheet cells gracefully
df.fillna("Unknown", inplace=True)

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Options")
all_locations = ["All"] + list(df["location_tag"].unique())
selected_location = st.sidebar.selectbox("Select Physical Location", all_locations)

# Apply filter to dataframe
if selected_location != "All":
    filtered_df = df[df["location_tag"] == selected_location]
else:
    filtered_df = df

# --- KEY PERFORMANCE METRICS ---
total_assets = len(filtered_df)
unique_manufacturers = filtered_df["manufacturer"].nunique()

col1, col2 = st.columns(2)
with col1:
    st.metric(label="Total Tracked Assets", value=total_assets)
with col2:
    st.metric(label="Distinct Manufacturers", value=unique_manufacturers)

st.markdown("---")

# --- MAIN DATA DISPLAY ---
st.subheader("📋 Asset Inventory List")
st.dataframe(filtered_df, use_container_width=True)

# --- DETAILED CONDITION AUDITING CARD ---
st.markdown("---")
st.subheader("🔍 Maintenance & Status Logs")
for idx, row in filtered_df.iterrows():
    with st.expander(f"{row['asset_name']} ({row['manufacturer']} {row['model_serial_number']})"):
        st.write(f"📍 **Location:** {row['location_tag']}")
        st.write(f"⚙️ **Physical Condition Notes:** {row['physical_condition']}")
