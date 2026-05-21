import streamlit as st
import json
import pandas as pd

# Set up page config
st.set_page_config(page_title="South Campus Lab Asset Dashboard", layout="wide")
st.title("🧪 South Campus Lab Asset Management Dashboard")
st.markdown("---")

# Load JSON data
try:
    with open("SC Lab.json", "r") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
except FileNotFoundError:
    st.error("Could not find 'SC Lab.json'. Please ensure it's in the same directory.")
    st.stop()

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
# Clean columns for display
display_df = filtered_df[["asset_name", "manufacturer", "model_serial_number", "physical_condition", "location_tag", "timestamp"]]
st.dataframe(display_df, use_container_width=True)

# --- DETAILED CONDITION AUDITING CARD ---
st.markdown("---")
st.subheader("🔍 Maintenance & Status Logs")
for idx, row in filtered_df.iterrows():
    with st.expander(f"{row['asset_name']} ({row['manufacturer']} {row['model_serial_number']})"):
        st.write(f"📍 **Location:** {row['location_tag']}")
        st.write(f"⏱️ **Video Scan Timestamp:** `{row['timestamp']}`")
        st.write(f"⚙️ **Physical Condition Notes:** {row['physical_condition']}")