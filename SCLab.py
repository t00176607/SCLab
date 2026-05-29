import streamlit as st
import pandas as pd

# Set up page config
st.set_page_config(page_title="Lab Asset Dashboard", layout="wide")

# --- GOOGLE SHEETS LIVE CONNECTION LAYER ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1vN4IFkM2xlzA0G8oLV6yWo_sD9unOq_j8dYUP0wQMxg/gviz/tq?tqx=out:csv"
TOKENS_CSV_URL = "https://docs.google.com/spreadsheets/d/1vN4IFkM2xlzA0G8oLV6yWo_sD9unOq_j8dYUP0wQMxg/gviz/tq?tqx=out:csv&sheet=AccessTokens"

@st.cache_data(ttl=60) # Auto-refreshes data every 60 seconds
def load_live_data(url):
    return pd.read_csv(url)

with st.spinner("Validating secure credentials..."):
    df_inventory = load_live_data(SHEET_CSV_URL)
    df_tokens = load_live_data(TOKENS_CSV_URL)

# Fill blank cells cleanly
df_inventory.fillna("Unknown", inplace=True)
df_tokens.fillna("Unknown", inplace=True)

# Standardize column headers (strips spaces and forces lowercase)
df_inventory.columns = df_inventory.columns.str.strip().str.lower()
df_tokens.columns = df_tokens.columns.str.strip().str.lower()


# ==========================================
# --- URL TOKEN VALIDATION LAYER ---
# ==========================================
url_params = st.query_params

if "token" not in url_params:
    st.error("🔒 Access Denied: A valid authorization token is required to view assets.")
    st.stop()

user_token = str(url_params["token"]).strip()
matching_row = df_tokens[df_tokens["secure_token"].astype(str).str.strip() == user_token]

if matching_row.empty:
    st.error("❌ Invalid or Expired Authorization Token.")
    st.stop()

# Pulls 'C124' or 'Chem Vault' out of the token tab's first column
authorized_room = matching_row.iloc[0]["location_tag"]


# ==========================================
# --- APPLICATION RUNTIME (AUTHORIZED) ---
# ==========================================
st.title("🧪 SC Live Lab Asset Management Dashboard")
st.caption(f"Securely authenticated session for Room: **{authorized_room}**")
st.markdown("---")

# Filter the inventory sheet strictly by the room column matching the token's room
filtered_df = df_inventory[df_inventory["room_tag"] == authorized_room]

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
st.subheader(f"📋 Asset Inventory List — Room {authorized_room}")
st.dataframe(filtered_df, use_container_width=True)

# --- DETAILED CONDITION AUDITING CARD ---
st.markdown("---")
st.subheader("🔍 Maintenance & Status Logs")
for idx, row in filtered_df.iterrows():
    with st.expander(f"{row['asset_name']} ({row['manufacturer']} {row['model_serial_number']})"):
        st.write(f"📍 **Specific Placement:** {row['location_tag']}")
        st.write(f"⚙️ **Physical Condition Notes:** {row['physical_condition']}")
        st.write(f"⚙️ **Physical Condition Notes:** {row['physical_condition']}")
