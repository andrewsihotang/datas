import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

def login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("Please log in")
        username = st.text_input("Username", key="username")
        password = st.text_input("Password", type="password", key="password")
        if st.button("Login"):
            if (username == st.secrets["LOGIN_USERNAME"] and
                password == st.secrets["LOGIN_PASSWORD"]):
                st.session_state.logged_in = True
            else:
                st.error("Invalid username or password")
        return False
    return True

if login():
    @st.cache_data
    def load_data_from_gsheets(json_keyfile_str, spreadsheet_id, sheet_name):
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds_dict = json.loads(json_keyfile_str)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()
        df['TANGGAL'] = pd.to_datetime(df['TANGGAL'])
        if 'NPSN' in df.columns:
            df['NPSN'] = df['NPSN'].astype(str)
        return df

    json_keyfile_str = st.secrets["GSHEET_SERVICE_ACCOUNT"]
    spreadsheet_id = '1_YeSK2zgoExnC8n6tlmoJFQDVEWZbncdBLx8S5k-ljc'

    # Load data from sheets
    sheet_names = ['Tendik', 'Pendidik', 'Kejuruan']
    dfs = []
    for sheet_name in sheet_names:
        df_sheet = load_data_from_gsheets(json_keyfile_str, spreadsheet_id, sheet_name)
        df_sheet['CATEGORY'] = sheet_name
        dfs.append(df_sheet)
    df = pd.concat(dfs, ignore_index=True)

    st.title('Training Participants Dashboard')

    jenjang_filter = st.multiselect(
        'Select Education Level (JENJANG)',
        options=df['JENJANG'].unique()
    )
    kecamatan_filter = st.multiselect(
        'Select District (KECAMATAN)',
        options=df['KECAMATAN'].unique()
    )
    nama_pelatihan_filter = st.multiselect(
        'Select Training Name (NAMA_PELATIHAN)',
        options=df['NAMA_PELATIHAN'].unique()
    )
    pelatihan_filter = st.multiselect(
        'Select Job Category (CATEGORY)',
        options=df['CATEGORY'].unique()
    )
    date_range = st.date_input(
        'Select Training Date Range (Optional)',
        value=[],
        help="Leave empty to disable date filtering"
    )

    conditions = []
    if jenjang_filter:
        conditions.append(df['JENJANG'].isin(jenjang_filter))
    if kecamatan_filter:
        conditions.append(df['KECAMATAN'].isin(kecamatan_filter))
    if nama_pelatihan_filter:
        conditions.append(df['NAMA_PELATIHAN'].isin(nama_pelatihan_filter))
    if pelatihan_filter:
        conditions.append(df['CATEGORY'].isin(pelatihan_filter))
    if len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        conditions.append((df['TANGGAL'] >= start_date) & (df['TANGGAL'] <= end_date))

    if conditions:
        filter_condition = conditions[0]
        for cond in conditions[1:]:
            filter_condition &= cond
    else:
        filter_condition = pd.Series([True] * len(df))

    filtered_df = df[filter_condition]

    if 'NO' in filtered_df.columns:
        filtered_df = filtered_df.drop(columns=['NO'])

    filtered_df = filtered_df.reset_index(drop=True)
    filtered_df.index = filtered_df.index + 1

    filtered_df['TANGGAL'] = filtered_df['TANGGAL'].dt.strftime('%Y-%m-%d')

    st.write(f'Showing {filtered_df.shape[0]} records')
    st.dataframe(filtered_df)

    st.write('### Summary Metrics')
    st.write('Number of unique participants:', filtered_df['NAMA_PESERTA'].nunique())
    st.write('Number of total participants:', filtered_df['NAMA_PESERTA'].count())
    st.write('Number of schools:', filtered_df['ASAL_SEKOLAH'].nunique())
    st.write('Number of Training Types (NAMA_PELATIHAN):', filtered_df['NAMA_PELATIHAN'].nunique())

    # --- Upload section ---
    st.write("---")
    st.header("Upload new data to update a category sheet")

    upload_category = st.selectbox("Select Category Sheet to Update", sheet_names)

    uploaded_file = st.file_uploader(
        f"Upload CSV or Excel file for '{upload_category}' sheet (must match template columns)",
        type=['csv', 'xlsx']
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                # Read CSV with semicolon separator
                new_data = pd.read_csv(uploaded_file, sep=';')
            else:
                new_data = pd.read_excel(uploaded_file)

            st.write("Preview of uploaded data:")
            st.dataframe(new_data)

            expected_columns = df.columns.drop('CATEGORY').tolist()
            if not all(col in new_data.columns for col in expected_columns):
                st.error(f"Uploaded file is missing some required columns: {expected_columns}")
            else:
                # Convert datetime columns to strings for JSON serialization
                for col in new_data.select_dtypes(include=['datetime64', 'datetimetz']).columns:
                    new_data[col] = new_data[col].dt.strftime('%Y-%m-%d')

                if st.button("Update Google Sheet with uploaded data"):
                    try:
                        scopes = ['https://www.googleapis.com/auth/spreadsheets']
                        creds_dict = json.loads(st.secrets["GSHEET_SERVICE_ACCOUNT"])
                        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                        client = gspread.authorize(creds)

                        sheet = client.open_by_key(spreadsheet_id).worksheet(upload_category)
                        sheet.clear()
                        sheet.update([new_data.columns.values.tolist()] + new_data.values.tolist())

                        st.success(f"Google Sheet '{upload_category}' updated successfully!")

                        # Clear cache so new data is reloaded on next run
                        load_data_from_gsheets.clear()

                    except Exception as e:
                        st.error(f"Failed to update sheet: {e}")

        except Exception as e:
            st.error(f"Failed to read uploaded file: {e}")
