import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# --- CSS with small margins ---
st.markdown("""
<style>
[data-testid="stAppViewContainer"] > .main {
    max-width: 100vw;
    padding-left: 20px;
    padding-right: 20px;
}
.block-container {
    max-width: 100vw;
    padding-top: 2rem;
    padding-bottom: 2rem;
    padding-left: 20px;
    padding-right: 20px;
}
.stDataFrameContainer, .css-1q8dd3e.e1fqkh3o4 {
    max-width: 100vw !important;
}
[data-testid="stSidebar"] {
    display: none;
}
</style>
""", unsafe_allow_html=True)

def login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("Data Peserta Pelatihan Tenaga Kependidikan")
        st.subheader("Login Required")
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

    sheet_names = ['Tendik', 'Pendidik', 'Kejuruan']
    dfs = []
    for sheet_name in sheet_names:
        df_sheet = load_data_from_gsheets(json_keyfile_str, spreadsheet_id, sheet_name)
        dfs.append(df_sheet)
    df = pd.concat(dfs, ignore_index=True)

    st.title('Data Peserta Pelatihan Tenaga Kependidikan')

    # Removed the "Filter Data" heading as requested
    with st.container():
        col1, col2, col3, col4, col5 = st.columns([1,1,1,1,1])
        with col1:
            jenjang_filter = st.multiselect('JENJANG', df['JENJANG'].unique())
        with col2:
            kecamatan_filter = st.multiselect('KECAMATAN', df['KECAMATAN'].unique())
        with col3:
            nama_pelatihan_filter = st.multiselect('NAMA PELATIHAN', df['NAMA_PELATIHAN'].unique())
        with col4:
            pelatihan_filter = st.multiselect('PELATIHAN', df['PELATIHAN'].unique())
        with col5:
            date_range = st.date_input('TANGGAL', value=[])

    conditions = []
    if jenjang_filter:
        conditions.append(df['JENJANG'].isin(jenjang_filter))
    if kecamatan_filter:
        conditions.append(df['KECAMATAN'].isin(kecamatan_filter))
    if nama_pelatihan_filter:
        conditions.append(df['NAMA_PELATIHAN'].isin(nama_pelatihan_filter))
    if pelatihan_filter:
        conditions.append(df['PELATIHAN'].isin(pelatihan_filter))
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
    st.dataframe(filtered_df, use_container_width=True)

    # Changed heading and metric labels to Indonesian as requested
    st.write('### Kesimpulan')
    st.write('Jumlah Peserta (unique):', filtered_df['NAMA_PESERTA'].nunique())
    st.write('Jumlah Total Peserta Keseluruhan:', filtered_df['NAMA_PESERTA'].count())
    st.write('Jumlah Sekolah:', filtered_df['ASAL_SEKOLAH'].nunique())
    st.write('Jumlah Pelatiahan:', filtered_df['NAMA_PELATIHAN'].nunique())
