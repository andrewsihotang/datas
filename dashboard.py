import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import plotly.graph_objects as go
import plotly.express as px

# --- CSS for layout and header logo-row tweaks, NO tall vertical spacing ---
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
/* aggrid small font for mobile */
@media (max-width: 700px) {
    .ag-root-wrapper, .ag-theme-streamlit input { font-size:11px !important; }
    .ag-header-cell-label, .ag-cell { font-size:10px !important; }
}
/* LOGO HEADER ROW FOR LANDING PAGE */
.landing-header {
    width: 100%;
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
    margin-bottom: 16px;
}
.landing-header .header-group {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 10px;
}
.landing-header .header-logo {
    height: 46px;
}
.landing-header .header-text {
    font-size: 1rem;
    font-weight: 500;
    line-height: 1.1;
}
/* Move up the landing content */
.landing-centered-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    margin-top: 0px;
    margin-bottom: 0px;
    padding-top: 10px;
    padding-bottom: 10px;
    min-height: unset !important;
    height: auto !important;
}
.landing-centered-content h1, .landing-centered-content h2 {
    text-align: center;
    margin-bottom: 6px;
    margin-top: 0px;
}
.landing-centered-content button {
    margin-top: 18px;
    width: 120px;
}
</style>
""", unsafe_allow_html=True)

# Logo URLs
DISDIK_LOGO_URL = "https://raw.githubusercontent.com/andrewsihotang/datas/main/disdik_jakarta.png"
P4_LOGO_URL = "https://raw.githubusercontent.com/andrewsihotang/datas/main/p4.png"

if "page" not in st.session_state:
    st.session_state.page = "landing"

def show_landing_page():
    st.markdown(
        f'''
        <div class="landing-header">
            <div class="header-group">
                <img src="{DISDIK_LOGO_URL}" class="header-logo" alt="Dinas Pendidikan" />
                <div class="header-text">Dinas Pendidikan Provinsi DKI Jakarta</div>
            </div>
            <div class="header-group">
                <img src="{P4_LOGO_URL}" class="header-logo" alt="P4" />
                <div class="header-text">P4 Jakarta Utara dan Kepulauan Seribu</div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    st.markdown('<div class="landing-centered-content">', unsafe_allow_html=True)
    st.title("SIPADU")
    st.subheader("Sistem Pangkalan Data Utama P4 Jakarta Utara dan Kepulauan Seribu")
    if st.button("Mulai"):
        st.session_state.page = "main"
    st.markdown('</div>', unsafe_allow_html=True)

def reset_filters(options_dict):
    for key, default in options_dict.items():
        st.session_state[key] = default

def main_app():
    st.markdown("<br>", unsafe_allow_html=True)
    colbtn1, colbtn2, _ = st.columns([1, 1, 8])
    with colbtn1:
        if st.button("Refresh Data"):
            st.cache_data.clear()
    with colbtn2:
        if st.button("Reset Filter"):
            filter_defaults = {
                "jenjang_filter": [],
                "kecamatan_filter": [],
                "nama_pelatihan_filter": [],
                "pelatihan_filter": [],
                "status_sekolah_filter": [],
                "date_range": []
            }
            reset_filters(filter_defaults)
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
        if 'STASUS_SEKOLAH' in df.columns:
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

    # Filters container
    with st.container():
        col1, col2, col3, col4, col5, col6 = st.columns([1,1,1,1,1,1])
        with col1:
            jenjang_filter = st.multiselect(
                'JENJANG', 
                df['JENJANG'].dropna().unique(), 
                key="jenjang_filter", 
                default=st.session_state.get("jenjang_filter", []))
        with col2:
            kecamatan_filter = st.multiselect(
                'KECAMATAN', 
                df['KECAMATAN'].dropna().unique(), 
                key="kecamatan_filter", 
                default=st.session_state.get("kecamatan_filter", []))
        with col3:
            nama_pelatihan_filter = st.multiselect(
                'NAMA PELATIHAN', 
                df['NAMA_PELATIHAN'].dropna().unique(), 
                key="nama_pelatihan_filter", 
                default=st.session_state.get("nama_pelatihan_filter", []))
        with col4:
            pelatihan_filter = st.multiselect(
                'PELATIHAN', 
                df['PELATIHAN'].dropna().unique(), 
                key="pelatihan_filter",
                default=st.session_state.get("pelatihan_filter", []))
        with col5:
            status_options = df['STATUS_SEKOLAH'].dropna().unique() if 'STATUS_SEKOLAH' in df.columns else []
            status_sekolah_filter = st.multiselect(
                'STATUS SEKOLAH', 
                status_options, 
                key="status_sekolah_filter", 
                default=st.session_state.get("status_sekolah_filter", []))
        with col6:
            date_range = st.date_input(
                'TANGGAL', 
                value=st.session_state.get("date_range", []), 
                key="date_range"
            )

    # Filtering logic
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

    cols = list(filtered_df.columns)
    if 'STATUS_SEKOLAH' in cols and 'ASAL_SEKOLAH' in cols:
        cols.remove('STATUS_SEKOLAH')
        asal_idx = cols.index('ASAL_SEKOLAH')
        cols.insert(asal_idx + 1, 'STATUS_SEKOLAH')
        display_df = filtered_df[cols]
    else:
        display_df = filtered_df

    st.write(f'Showing {display_df.shape[0]} records')

    view_mode = st.radio("Table view mode:", ['Full Table View', 'Compact Table View'], horizontal=True)
    if view_mode == 'Compact Table View':
        compact_cols = ['NAMA_PESERTA', 'NAMA_PELATIHAN', 'TANGGAL']
        display_df_view = display_df[compact_cols].copy()
    else:
        display_df_view = display_df.copy()
    
    gb = GridOptionsBuilder.from_dataframe(display_df_view)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc="sum", editable=False)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    grid_options = gb.build()
    AgGrid(
        display_df_view,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=500,
        fit_columns_on_grid_load=True,
        reload_data=True,
    )

    # Summary by Jenjang (pelatihan peserta achievement)
    targets = {
        'DIKMAS': 284,
        'PAUD': 2292,
        'SD': 2556,
        'SMP': 1500,
        'SMA': 801,
        'SMK': 636,
    }
    summary_rows = []
    for jenjang, target in targets.items():
        df_jenjang = filtered_df[
            (filtered_df['JENJANG'] == jenjang) &
            (filtered_df['NPSN'].notna()) &
            (filtered_df['NPSN'].astype(str) != '0')
        ]
        unique_count = df_jenjang['NAMA_PESERTA'].nunique()
        percent = (unique_count / target * 100) if target else 0
        kurang = max(0, target - unique_count) if unique_count < target else 0
        summary_rows.append({
            'Jenjang': jenjang,
            'Target Jumlah Peserta Pelatihan': f"{target:,} Orang",
            'Jumlah Peserta Pelatihan (unique)': f"{unique_count:,} Orang",
            'Persentase': f"{percent:.2f} %",
            'Kurang': f"{kurang:,} Orang"
        })
    df_summary = pd.DataFrame(summary_rows)
    df_summary.index = df_summary.index + 1
    df_summary = df_summary[['Jenjang', 'Target Jumlah Peserta Pelatihan',
                             'Jumlah Peserta Pelatihan (unique)', 'Persentase', 'Kurang']]

    st.write('### Rekap Pencapaian Pelatihan Tendik berdasarkan Jenjang')
    st.dataframe(df_summary)

    st.markdown('---')

    # New: Rekap by Jumlah Sekolah with cutoff note
    sekolah_data = {
        'Jenjang': ['PAUD', 'DIKMAS', 'SD', 'SMP', 'SMA', 'SMK'],
        'Jumlah Sekolah': ['855 sekolah', '149 sekolah', '424 sekolah', '239 sekolah', '111 sekolah', '76 sekolah'],
        'Catatan': ['Data cutoff: 08 September 2025'] * 6
    }
    df_sekolah = pd.DataFrame(sekolah_data)
    df_sekolah.index = df_sekolah.index + 1

    st.write('### Rekap Pencapaian Pelatihan Tendik berdasarkan Jumlah Sekolah')
    st.markdown('*Catatan: Data cutoff per 08 September 2025*')
    st.dataframe(df_sekolah)

# Main logic
if st.session_state.page == "landing":
    show_landing_page()
elif st.session_state.page == "main":
    main_app()
else:
    st.session_state.page = "landing"
    show_landing_page()
