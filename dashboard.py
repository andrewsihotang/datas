import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# --- CSS for margins ---
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
        if 'STASUS_SEKOLAH' in df.columns:  # Fix typo if exists
            df.rename(columns={'STASUS_SEKOLAH': 'STATUS_SEKOLAH'}, inplace=True)
        if 'STATUS_SEKOLAH' not in df.columns:
            df['STATUS_SEKOLAH'] = pd.NA
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

    with st.container():
        col1, col2, col3, col4, col5, col6 = st.columns([1,1,1,1,1,1])
        with col1:
            jenjang_filter = st.multiselect('JENJANG', df['JENJANG'].unique())
        with col2:
            kecamatan_filter = st.multiselect('KECAMATAN', df['KECAMATAN'].unique())
        with col3:
            nama_pelatihan_filter = st.multiselect('NAMA PELATIHAN', df['NAMA_PELATIHAN'].unique())
        with col4:
            pelatihan_filter = st.multiselect('PELATIHAN', df['PELATIHAN'].unique())
        with col5:
            status_options = df['STATUS_SEKOLAH'].dropna().unique() if 'STATUS_SEKOLAH' in df.columns else []
            status_sekolah_filter = st.multiselect('STATUS SEKOLAH', status_options)
        with col6:
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
    if status_sekolah_filter:
        conditions.append(df['STATUS_SEKOLAH'].isin(status_sekolah_filter))
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

    # Reorder columns to place STATUS_SEKOLAH right after ASAL_SEKOLAH
    cols = list(filtered_df.columns)
    if 'STATUS_SEKOLAH' in cols and 'ASAL_SEKOLAH' in cols:
        cols.remove('STATUS_SEKOLAH')
        asal_idx = cols.index('ASAL_SEKOLAH')
        cols.insert(asal_idx + 1, 'STATUS_SEKOLAH')
        display_df = filtered_df[cols]
    else:
        display_df = filtered_df

    st.write(f'Showing {display_df.shape[0]} records')
    st.dataframe(display_df, use_container_width=True)

    st.write('### Kesimpulan')
    st.write('Jumlah Peserta (unique):', filtered_df['NAMA_PESERTA'].nunique())
    st.write('Jumlah Total Peserta Keseluruhan:', filtered_df['NAMA_PESERTA'].count())
    st.write('Jumlah Sekolah:', filtered_df['ASAL_SEKOLAH'].nunique())
    st.write('Jumlah Pelatiahan:', filtered_df['NAMA_PELATIHAN'].nunique())

    # --- Upload section ---
    st.write("---")
    st.header("Upload data untuk menambahkan ke sheet kategori")

    upload_category = st.selectbox("Pilih kategori sheet untuk ditambahkan data", sheet_names)

    uploaded_file = st.file_uploader(
        f"Upload file CSV atau Excel untuk sheet '{upload_category}' (format sesuai template)",
        type=['csv', 'xlsx']
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                new_data = pd.read_csv(uploaded_file, sep=';')
            else:
                new_data = pd.read_excel(uploaded_file)

            st.write("Pratinjau data yang diunggah:")
            st.dataframe(new_data)

            expected_columns = df.columns.drop('CATEGORY', errors='ignore').tolist()
            if not all(col in new_data.columns for col in expected_columns):
                st.error(f"File unggahan kehilangan beberapa kolom wajib: {expected_columns}")
            else:
                for col in new_data.select_dtypes(include=['datetime64', 'datetimetz']).columns:
                    new_data[col] = new_data[col].dt.strftime('%Y-%m-%d')

                if st.button("Tambahkan data ke Google Sheet"):
                    try:
                        scopes = ['https://www.googleapis.com/auth/spreadsheets']
                        creds_dict = json.loads(st.secrets["GSHEET_SERVICE_ACCOUNT"])
                        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                        client = gspread.authorize(creds)

                        sheet = client.open_by_key(spreadsheet_id).worksheet(upload_category)

                        existing_data = sheet.get_all_values()

                        if len(existing_data) == 0:
                            combined_data = [new_data.columns.values.tolist()] + new_data.values.tolist()
                        else:
                            existing_rows = existing_data[1:]
                            existing_df = pd.DataFrame(existing_rows, columns=existing_data[0])
                            combined_df = pd.concat([existing_df, new_data], ignore_index=True)
                            combined_data = [combined_df.columns.values.tolist()] + combined_df.values.tolist()

                        sheet.clear()
                        sheet.update(combined_data)

                        st.success(f"Data berhasil ditambahkan ke sheet '{upload_category}'!")

                        load_data_from_gsheets.clear()

                    except Exception as e:
                        st.error(f"Gagal menambahkan data: {e}")

        except Exception as e:
            st.error(f"Gagal membaca file unggahan: {e}")

    # --- Social media footer ---
    st.markdown(
        """
        <hr>
        <div style="text-align: center; margin-top: 20px;">
            <a href="https://www.instagram.com/p4jakut_ks?igsh=c3Mya2dodm5hbHU1" target="_blank" style="margin: 0 20px; display: inline-block; text-decoration: none; color: inherit;">
                <img src="https://raw.githubusercontent.com/andrewsihotang/datas/main/instagrams.png" alt="Instagram" width="32" height="32" />
                <div style="font-size: 0.7rem; margin-top: 4px;">Instagram P4 JUKS</div>
            </a>
            <a href="https://www.tiktok.com/@p4.juks?_t=ZS-8zKsAgWjXJQ&_r=1" target="_blank" style="margin: 0 20px; display: inline-block; text-decoration: none; color: inherit;">
                <img src="https://raw.githubusercontent.com/andrewsihotang/datas/main/tiktok.png" alt="TikTok" width="32" height="32" />
                <div style="font-size: 0.7rem; margin-top: 4px;">TikTok P4 JUKS</div>
            </a>
            <a href="https://youtube.com/@p4jakartautaradankep-seribu?si=BWAVvVyVdYvbj8Xo" target="_blank" style="margin: 0 20px; display: inline-block; text-decoration: none; color: inherit;">
                <img src="https://raw.githubusercontent.com/andrewsihotang/datas/main/youtube.png" alt="YouTube" width="32" height="32" />
                <div style="font-size: 0.7rem; margin-top: 4px;">YouTube P4 JUKS</div>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )
