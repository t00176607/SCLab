import streamlit as st
import gspread
import pandas as pd

# 1. Grab your freshly saved secrets block
creds_dict = dict(st.secrets["connections"]["gsheets"])

# 2. Fix the string literals for the brand-new key
if "private_key" in creds_dict:
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

# 3. Direct authentication via gspread (Bypassing st.connection completely)
try:
    gc = gspread.service_account_from_dict(creds_dict)
except Exception as e:
    st.error(f"Authentication failed at the cryptography layer: {e}")
    st.stop()

import pandas as pd
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Lab Asset Dashboard", layout="wide")

# ==========================================
# --- SECURE GSHEETS CONNECTION LAYER ---
# ==========================================
# Connect using the secrets configured in your Streamlit Cloud settings
conn = st.connection("gsheets", type=GSheetsConnection)

# Define your master spreadsheet URL explicitly
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1vN4IFkM2xlzA0G8oLV6yWo_sD9unOq_j8dYUP0wQMxg/"

@st.cache_data(ttl=60)
def load_live_data():
    # Pass the SPREADSHEET_URL parameter directly into the connection
    df_inv = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Sheet1")
    df_tok = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="AccessTokens")
    return df_inv, df_tok

with st.spinner("Authenticating live connection..."):
    df_inventory, df_tokens = load_live_data()

# Clean up dataframes
df_inventory.fillna("Unknown", inplace=True)
df_tokens.fillna("Unknown", inplace=True)
df_inventory.columns = df_inventory.columns.str.strip().str.lower()
df_tokens.columns = df_tokens.columns.str.strip().str.lower()


# ==========================================
# --- URL TOKEN VALIDATION LAYER ---
# ==========================================
url_params = st.query_params

if "token" not in url_params:
    st.error("🔒 Access Denied: A valid authorization token is required.")
    st.stop()

user_token = str(url_params["token"]).strip()
matching_row = df_tokens[df_tokens["secure_token"].astype(str).str.strip() == user_token]

if matching_row.empty:
    st.error("❌ Invalid or Expired Authorization Token.")
    st.stop()

authorized_room = matching_row.iloc[0]["location_tag"]


# ==========================================
# --- APP UI & READ/EDIT CONTAINER ---
# ==========================================
st.title("🧪 SC Live Lab Asset Management Dashboard")
st.caption(f"Secure session active for Room: **{authorized_room}**")
st.markdown("---")

# Isolate items for this room only
filtered_df = df_inventory[df_inventory["room_tag"] == authorized_room]

# Metrics
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Total Tracked Assets", value=len(filtered_df))
with col2:
    st.metric(label="Distinct Manufacturers", value=filtered_df["manufacturer"].nunique())

st.markdown("---")
st.subheader(f"📋 Asset Inventory List — Room {authorized_room}")
st.caption("💡 Double-click any cell to edit details directly. Click 'Save Table Changes' below to update the live spreadsheet.")

# Render the interactive spreadsheet editor widget
# 'room_tag' and 'timestamp' are disabled to maintain structural data boundaries
edited_df = st.data_editor(
    filtered_df, 
    use_container_width=True,
    disabled=["room_tag", "timestamp"], 
    key="inventory_editor"
)

# Save Button for Cell Changes
if st.button("💾 Save Table Changes"):
    with st.spinner("Syncing your updates to the live master matrix..."):
        # Pull absolute latest copy from Google Sheets to ensure no cross-room data drops
        df_latest_master, _ = load_live_data()
        df_latest_master.fillna("Unknown", inplace=True)
        df_latest_master.columns = df_latest_master.columns.str.strip().str.lower()
        
        # Pull out rows belonging to OTHER rooms to preserve them
        other_rooms_df = df_latest_master[df_latest_master["room_tag"] != authorized_room]
        
        # Merge untouched room rows with your newly modified room rows
        final_updated_master = pd.concat([other_rooms_df, edited_df], ignore_index=True)
        
        # Force column formatting alignment before push
        final_updated_master = final_updated_master[df_inventory.columns]
        
        # Overwrite the spreadsheet cleanly via secure API execution
        conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Sheet1", data=final_updated_master)
        
        st.success("Table changes successfully synchronized!")
        st.cache_data.clear() # Erase data view cache
        st.rerun()            # Hard reload application UI


# ==========================================
# --- SECURE WRITE-BACK DATA LAYER ---
# ==========================================
st.markdown("---")
with st.expander("➕ Add New Asset to this Room"):
    with st.form("new_asset_form", clear_on_submit=True):
        st.write("Logged assets are automatically tagged to your current authorized space.")
        
        # User input fields
        new_name = st.text_input("Asset Name*")
        new_manuf = st.text_input("Manufacturer*")
        new_serial = st.text_input("Model / Serial Number")
        new_loc = st.text_input("Specific Placement (e.g., Workbench 1, Drawer B)")
        new_cond = st.selectbox("Physical Condition", ["New", "Used", "Fair", "Needs Maintenance"])
        
        submit_button = st.form_submit_button("Save Asset to Live Matrix")
        
        if submit_button:
            if not new_name or not new_manuf:
                st.error("Asset Name and Manufacturer fields are mandatory.")
            else:
                # Format the row to match the spreadsheet structure exactly
                new_row = pd.DataFrame([{
                    "asset_name": new_name,
                    "manufacturer": new_manuf,
                    "model_serial_number": new_serial if new_serial else "Unknown",
                    "physical_condition": new_cond,
                    "room_tag": authorized_room, 
                    "location_tag": new_loc if new_loc else "Unassigned",
                    "timestamp": datetime.now().strftime("%H:%M")
                }])
                
                # Append the row to the existing spreadsheet using the secure API connection
                updated_df = pd.concat([df_inventory, new_row], ignore_index=True)
                
                # Added explicit SPREADSHEET_URL to prevent ValueError crashes
                conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Sheet1", data=updated_df)
                
                st.success(f"Successfully added '{new_name}' to the live master matrix!")
                st.cache_data.clear() 
                st.rerun()


# --- MAINTENANCE LOG EXPANDERS ---
st.markdown("---")
st.subheader("🔍 Maintenance & Status Logs")
# Switched from filtered_df to edited_df so logs update instantly on-screen while typing
for idx, row in edited_df.iterrows():
    with st.expander(f"{row['asset_name']} ({row['manufacturer']} {row['model_serial_number']})"):
        st.write(f"📍 **Specific Placement:** {row['location_tag']}")
        st.write(f"⚙️ **Physical Condition Notes:** {row['physical_condition']}")
