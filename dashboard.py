import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# --- CSS for margins and font size tweak on mobile ---
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
@media (max-width: 700px) {
    .ag-root-wrapper, .ag-theme-streamlit input { font-size:11px !important; }
    .ag-header-cell-label, .ag-cell { font-size:10px !important; }
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

def reset_filters(options_dict):
    for key, default in options_dict.items():
        st.session_state[key] = default

if login():
    st.markdown("<br>", unsafe_allow_html=True)
    colbtn1, colbtn2, _ = st.columns([1, 1, 8])
    with colbtn1:
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()
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
            st.rerun()

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

    # -- Ignore any row with NPSN == '0' and coerce STATUS_SEKOLAH to string and remove "0", nan, blanks --
    df = df[(df['NPSN'].notna()) & (df['NPSN'].astype(str) != "0")]
    if 'STATUS_SEKOLAH' in df.columns:
        # Convert everything to str, then replace problematic values
        df['STATUS_SEKOLAH'] = df['STATUS_SEKOLAH'].astype(str)
        df = df[~df['STATUS_SEKOLAH'].isin(['0', 'nan', '', 'None', 'NaN', 'null', 'Null'])]

    st.title('Data Peserta Pelatihan Tenaga Kependidikan')
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
            # Only show valid string status (never 0 or blank)
            status_options = [x for x in df['STATUS_SEKOLAH'].dropna().unique() if x not in ['0', 'nan', '', 'None', 'NaN', 'null', 'Null']]
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

    # Make sure filtered_df STATUS_SEKOLAH is str and remove invalids for display/table again
    if 'STATUS_SEKOLAH' in filtered_df.columns:
        filtered_df['STATUS_SEKOLAH'] = filtered_df['STATUS_SEKOLAH'].astype(str)
        filtered_df = filtered_df[~filtered_df['STATUS_SEKOLAH'].isin(['0', 'nan', '', 'None', 'NaN', 'null', 'Null'])]

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

    grid_response = AgGrid(
        display_df_view,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=500,
        fit_columns_on_grid_load=True,
        reload_data=True,
    )
    selected = grid_response['selected_rows']
    if selected is not None and len(selected) > 0:
        if isinstance(selected, pd.DataFrame):
            selected_list = selected.to_dict(orient='records')
        else:
            selected_list = selected
        selected_name = selected_list[0].get('NAMA_PESERTA', '')
        st.markdown("### Detail Peserta")
        st.write(f"Semua pelatihan yang diikuti oleh: **{selected_name}**")
        participant_trainings = filtered_df[filtered_df['NAMA_PESERTA'] == selected_name][
            ['NAMA_PELATIHAN', 'TANGGAL', 'ASAL_SEKOLAH', 'NPSN']
        ].drop_duplicates().reset_index(drop=True)
        participant_trainings.index = participant_trainings.index + 1
        st.dataframe(participant_trainings)
        st.write(f"Jumlah pelatihan: {participant_trainings.shape[0]}")

    st.write('### Kesimpulan')
    st.write('Jumlah Peserta (unique):', filtered_df['NAMA_PESERTA'].nunique())
    st.write('Jumlah Total Peserta Keseluruhan:', filtered_df['NAMA_PESERTA'].count())
    st.write('Jumlah Sekolah:', filtered_df['ASAL_SEKOLAH'].nunique())
    st.write('Jumlah Pelatihan:', filtered_df['NAMA_PELATIHAN'].nunique())

    filtered_df['YEAR'] = pd.to_datetime(filtered_df['TANGGAL']).dt.year
    yearly_participants = filtered_df.groupby('YEAR')['NAMA_PESERTA'].nunique().reset_index()

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

    chart_col1, chart_col2 = st.columns([1, 1])
    with chart_col1:
        fig_yearly = go.Figure(data=[go.Bar(
            x=yearly_participants['YEAR'].astype(str),
            y=yearly_participants['NAMA_PESERTA'],
            text=yearly_participants['NAMA_PESERTA'],
            textposition='auto',
            marker_color='#1f77b4'
        )])
        fig_yearly.update_layout(
            title={'text':'Grafik Jumlah Peserta (unique)','x':0.5,'xanchor':'center'},
            xaxis_title='Tahun',
            yaxis_title='Jumlah',
            template='plotly_white',
            height=350,
            width=430
        )
        st.plotly_chart(fig_yearly, use_container_width=False)
    with chart_col2:
        pie_data = df_summary.copy()
        pie_data['UniqueValue'] = (
            pie_data['Jumlah Peserta Pelatihan (unique)'].str.replace(' Orang', '', regex=False).replace('', '0').astype(int)
        )
        fig_pie = px.pie(
            pie_data,
            names='Jenjang',
            values='UniqueValue',
            title='Proporsi Jumlah Peserta (unique) per Jenjang',
            hole=0.3
        )
        fig_pie.update_layout(
            showlegend=True,
            height=350,
            width=430,
            title={'text':'Proporsi Jumlah Peserta (unique) per Jenjang', 'x':0.5, 'xanchor':'center'}
        )
        st.plotly_chart(fig_pie, use_container_width=False)

    st.write("---")
    st.header("Upload Data Terbaru")
    upload_category = st.selectbox("Pilih kategori pelatihan untuk ditambahkan data", sheet_names)
    uploaded_file = st.file_uploader(
        f"Upload file CSV atau Excel untuk pelatihan '{upload_category}' (format sesuai template)",
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
