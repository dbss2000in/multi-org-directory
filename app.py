import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Multi-Org Secure Directory", page_icon="🏢", layout="wide"
)

# --- 1. MASTER USER CREDENTIALS & ROLE MAPPING ---
MASTER_USERS = {
    "manager_apollo": {
        "password": "securepassword123",
        "org_name": "Apollo Hospital",
        "role": "manager",
    },
    "emp_apollo1": {
        "password": "password123",
        "org_name": "Apollo Hospital",
        "role": "member",
    },
    "principal_xavier": {
        "password": "xavierpassword",
        "org_name": "St. Xavier College",
        "role": "manager",
    },
    "student_xavier1": {
        "password": "password123",
        "org_name": "St. Xavier College",
        "role": "member",
    },
    "manager_rotary": {
        "password": "rotarypassword",
        "org_name": "Rotary Club of Calcutta",
        "role": "manager",
    },
    "member_rotary1": {
        "password": "password123",
        "org_name": "Rotary Club of Calcutta",
        "role": "member",
    },
    "manager_tech": {
        "password": "techpassword",
        "org_name": "TechCorp India Pvt Ltd",
        "role": "manager",
    },
    "member_tech1": {
        "password": "password123",
        "org_name": "TechCorp India Pvt Ltd",
        "role": "member",
    },
    "manager_metro": {
        "password": "metropassword",
        "org_name": "Metro General Hospital",
        "role": "manager",
    },
    "member_metro1": {
        "password": "password123",
        "org_name": "Metro General Hospital",
        "role": "member",
    },
}

# --- 2. SESSION STATE INITIALIZATION ---
if "authenticated" not in st.session_state:
  st.session_state["authenticated"] = False
  st.session_state["username"] = ""
  st.session_state["role"] = ""
  st.session_state["org_name"] = ""


# --- 3. DATABASE FILE LOADER & SAVER ---
def get_db_path():
  if os.path.exists("Master_Multi_Tenant_Directory_5000.xlsx"):
    return "Master_Multi_Tenant_Directory_5000.xlsx", "excel"
  elif os.path.exists("Master_Multi_Tenant_Directory_5000.csv"):
    return "Master_Multi_Tenant_Directory_5000.csv", "csv"
  return None, None


@st.cache_data(ttl=300)
def load_master_data():
  file_path, file_type = get_db_path()
  if not file_path:
    st.error("Database file not found in repository folder.")
    return pd.DataFrame()

  try:
    if file_type == "excel":
      df = pd.read_excel(file_path, engine="openpyxl")
    else:
      df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df.fillna("None")
  except Exception as e:
    st.error(f"Error reading database file: {e}")
    return pd.DataFrame()


# --- 4. AUTHENTICATION / LOGIN VIEW ---
if not st.session_state["authenticated"]:
  st.title("🔐 Secure Multi-Organization Portal Login")
  st.markdown("Please log in using your assigned organizational credentials.")

  with st.form("login_form"):
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")
    submit_button = st.form_submit_button("Login")

    if submit_button:
      clean_user = username_input.strip()
      user_data = MASTER_USERS.get(clean_user)

      if user_data and user_data["password"] == password_input:
        st.session_state["authenticated"] = True
        st.session_state["username"] = clean_user
        st.session_state["role"] = user_data["role"]
        st.session_state["org_name"] = user_data["org_name"]
        st.rerun()
      else:
        st.error(
            "Invalid username or password. Please check your credentials."
        )

# --- 5. AUTHENTICATED USER INTERFACE ---
else:
  df_master = load_master_data()
  user_org = st.session_state["org_name"]

  if not df_master.empty and "Organization" in df_master.columns:
    df_org = df_master[df_master["Organization"].str.strip() == user_org].copy()
  else:
    df_org = pd.DataFrame()

  st.sidebar.title(f"🏢 {user_org}")
  st.sidebar.markdown(f"**Logged in as:** `{st.session_state['username']}`")
  st.sidebar.markdown(f"**Role:** `{st.session_state['role'].capitalize()}`")

  if st.sidebar.button("Log Out"):
    st.session_state["authenticated"] = False
    st.rerun()

  tabs = ["Directory"]
  if st.session_state["role"] == "manager":
    tabs.append("Manager Admin Portal")

  current_tab = st.sidebar.radio("Navigation", tabs)

  # --- DIRECTORY TAB (READ-ONLY) ---
  if current_tab == "Directory":
    st.title(f"📇 {user_org} - Member Directory & SOS")

    search_query = st.sidebar.text_input("Search Directory (Name or Notes)")
    filtered_df = df_org.copy()

    if search_query and not filtered_df.empty:
      filtered_df = filtered_df[
          filtered_df["Full Name"].str.contains(search_query, case=False, na=False)
          | filtered_df["Notes"].str.contains(
              search_query, case=False, na=False
          )
      ]

    st.markdown(f"Showing **{len(filtered_df)}** records for **{user_org}**")

    if filtered_df.empty:
      st.warning("No entries found matching your search.")
    else:
      for _, row in filtered_df.iterrows():
        name = row.get("Full Name", "Member")
        blood = row.get("Blood Group", "N/A")

        with st.expander(f"👤 {name}  |  🩸 Blood Group: {blood}"):
          col1, col2 = st.columns(2)

          with col1:
            st.subheader("📞 Communication Details")

            # 1. Address -> Google Maps Search Link
            raw_address = str(row.get("Address", "None"))
            if raw_address and raw_address != "None":
              maps_url = (
                  f"https://www.google.com/maps/search/?api=1&query={raw_address.replace(' ', '+')}"
              )
              st.markdown(
                  f"**Address:** [{raw_address}]({maps_url}) (Click to view on"
                  " Map)"
              )
            else:
              st.markdown("**Address:** None")

            # 2. Phone Number -> Tel Link
            phone = str(row.get("Phone Number", ""))
            st.markdown(f"**Phone:** [{phone}](tel:{phone})")

            # 3. WhatsApp Links
            wa_digits = "".join(
                filter(str.isdigit, str(row.get("WhatsApp Chat", "")))
            )
            wa_chat_url = f"https://wa.me/{wa_digits}" if wa_digits else "#"
            st.markdown(f"**WhatsApp Chat:** [Open Chat]({wa_chat_url})")

            # 4. Instagram -> Profile Link
            ig_raw = str(row.get("Instagram", "None")).strip()
            if ig_raw and ig_raw != "None":
              ig_handle = ig_raw.lstrip("@")
              ig_url = f"https://instagram.com/{ig_handle}"
              st.markdown(f"**Instagram:** [{ig_raw}]({ig_url})")
            else:
              st.markdown("**Instagram:** None")

            # 5. Facebook -> Profile Link
            fb_raw = str(row.get("Facebook", "None")).strip()
            if fb_raw and fb_raw != "None":
              # Clean URL format if needed
              fb_path = fb_raw.replace("fb.com/", "").replace(
                  "facebook.com/", ""
              )
              fb_url = f"https://facebook.com/{fb_path}"
              st.markdown(f"**Facebook:** [{fb_raw}]({fb_url})")
            else:
              st.markdown("**Facebook:** None")

            # 6. Email -> Mailto Link
            email_raw = str(row.get("Email", "None")).strip()
            if email_raw and email_raw != "None":
              st.markdown(f"**Email:** [{email_raw}](mailto:{email_raw})")
            else:
              st.markdown("**Email:** None")

            # 7. Website Link
            website_raw = str(row.get("Website", "None")).strip()
            if website_raw and website_raw != "None" and not website_raw.startswith("http"):
              website_url = f"https://{website_raw}"
            else:
              website_url = website_raw
            if website_url and website_url != "None":
              st.markdown(f"**Website:** [{website_raw}]({website_url})")
            else:
              st.markdown("**Website:** None")

          with col2:
            st.subheader("🚨 Medical Emergency & SOS")
            st.error(f"""
                        - **Blood Group:** {blood}
                        - **Allergies:** {row.get('Allergies', 'None')}
                        - **Medical Conditions:** {row.get('Medical Conditions', 'None')}
                        - **Medications:** {row.get('Medications', 'None')}
                        """)

            emerg_phone = str(row.get("Emergency Contact Phone", ""))
            st.info(f"""
                        **Emergency Contact:**
                        - **Name:** {row.get('Emergency Contact Name', 'N/A')} ({row.get('Emergency Contact Relationship', '')})
                        - **Phone:** [{emerg_phone}](tel:{emerg_phone})
                        """)

          st.markdown("---")
          st.caption(
              f"Timezone: {row.get('Timezone', 'Asia/Kolkata')} | Notes:"
              f" {row.get('Notes', 'None')}"
          )

  # --- MANAGER ADMIN PORTAL TAB ---
  elif current_tab == "Manager Admin Portal" and st.session_state["role"] == "manager":
    st.title("🛠️ Manager Administrative Portal")
    st.markdown(
        "Add, update, or remove member records. Changes only apply to"
        f" **{user_org}** data."
    )

    edited_org_df = st.data_editor(
        df_org, num_rows="dynamic", use_container_width=True
    )

    if st.button("Save Changes to Master Database"):
      try:
        file_path, file_type = get_db_path()
        edited_org_df["Organization"] = user_org

        df_others = (
            df_master[df_master["Organization"].str.strip() != user_org]
            if not df_master.empty
            else pd.DataFrame()
        )
        df_final_save = pd.concat([df_others, edited_org_df], ignore_index=True)

        if file_type == "excel" or file_path.endswith(".xlsx"):
          df_final_save.to_excel(
              "Master_Multi_Tenant_Directory_5000.xlsx",
              index=False,
              engine="openpyxl",
          )
        else:
          df_final_save.to_csv(
              "Master_Multi_Tenant_Directory_5000.csv", index=False
          )

        st.cache_data.clear()
        st.success(
            "Changes successfully saved! Your organization's records have been"
            " updated."
        )
      except Exception as e:
        st.error(f"Failed to save changes: {e}")
