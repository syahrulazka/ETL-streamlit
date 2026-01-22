import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, String, Date
from datetime import datetime
import io

st.set_page_config(
    page_title="Employee Data Upload",
    layout="wide"
)

@st.cache_resource
def get_db_engine():
    """Create database engine using secrets"""
    try:
        db_config = st.secrets["database"]
        connection_string = (
            f"mysql+mysqlconnector://{db_config['username']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
        return create_engine(connection_string, connect_args={'ssl_disabled': True})
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        return None

@st.cache_data(ttl=300)
def load_existing_keys(_engine):
    """Load existing employee_id and periode combinations as a set for fast lookup"""
    try:
        query = "SELECT employee_id, DATE_FORMAT(LAST_DAY(periode), '%Y-%m-%d') as periode FROM MasterTableNew_v2"
        df = pd.read_sql(query, _engine)
        return set(zip(df['employee_id'].astype(str), df['periode'].astype(str)))
    except Exception as e:
        st.error(f"Error loading existing data: {e}")
        return set()

@st.cache_data(ttl=300)
def load_existing_non_mitra_keys(_engine):
    """Load existing employee_id and period combinations from non_mitra table"""
    try:
        query = "SELECT employee_id, DATE_FORMAT(LAST_DAY(period), '%Y-%m-%d') as period FROM non_mitra"
        df = pd.read_sql(query, _engine)
        return set(zip(df['employee_id'].astype(str), df['period'].astype(str)))
    except Exception as e:
        st.error(f"Error loading existing non_mitra data: {e}")
        return set()

def get_hcm_engine():
    """Create HCM database engine"""
    hcm_config = st.secrets["hcm_database"]
    connection_string = (
        f"mysql+mysqlconnector://{hcm_config['username']}:{hcm_config['password']}"
        f"@{hcm_config['host']}:{hcm_config['port']}/{hcm_config['database']}"
    )
    return create_engine(connection_string, connect_args={'ssl_disabled': True})

@st.cache_data(ttl=600)
def load_fte_history_data():
    """Load FTE history data with resignation details from HCM"""
    try:
        hcm_engine = get_hcm_engine()
        query = """
        SELECT 
            fh.meh_date,
            fh.meh_employee_id,
            CASE 
                WHEN e.ME_END_DATE >= DATE_FORMAT(LAST_DAY(fh.meh_date), '%Y-%m-%d')
                 AND e.ME_END_DATE <= LAST_DAY(fh.meh_date)
                THEN e.ME_END_DATE
                ELSE NULL
            END AS ME_END_DATE,
            rr.mrr_name AS reason_resign_name,
            rrp.mrrp_name AS reason_resign_proint_name,
            rrp.mrrp_category
        FROM mst_fte_history fh
        LEFT JOIN mst_employee e
            ON fh.meh_employee_id = e.ME_EMPLOYEE_ID
        LEFT JOIN mst_employee_resign r
            ON fh.meh_employee_id = r.mer_employee_id
            AND r.mer_eff_date >= DATE_FORMAT(LAST_DAY(fh.meh_date), '%Y-%m-%d')
            AND r.mer_eff_date <= LAST_DAY(fh.meh_date)
        LEFT JOIN mst_reason_resign rr
            ON r.mer_reason_int = rr.mrr_id
        LEFT JOIN mst_reason_resign_proint rrp
            ON r.mer_reason_emp = rrp.mrrp_code
        ORDER BY fh.meh_date
        """
        return pd.read_sql(query, hcm_engine)
    except Exception as e:
        st.error(f"Error loading FTE history data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_hcm_data():
    """Load HCM employee data"""
    try:
        hcm_engine = get_hcm_engine()
        query = "SELECT ME_EMPLOYEE_ID, ME_JOB_LEVEL, ME_SEX, ME_BIRTH_DATE, ME_START_DATE FROM mst_employee"
        return pd.read_sql(query, hcm_engine)
    except Exception as e:
        st.error(f"Error loading HCM data: {e}")
        return pd.DataFrame()

def process_mitra_sheet(file, sheet_name):
    """Process Mitra sheet"""
    try:
        df = pd.read_excel(file, sheet_name=sheet_name)
        df.columns = df.iloc[0]
        df = df[1:]
        
        # Find last BU column and save it
        last_bu = [i for i, c in enumerate(df.columns) if c == 'BU'][-1]
        mitra_bu_last = df.iloc[:, last_bu]
        
        # Select and rename columns
        df = df[['Period', 'Employee ID', 'Full Name', 'Join Date', 'Jenis Karyawan', 
                'Gender', 'Birth Date', 'Job Title', 'Org Code', 'New Location By CC', 
                'Teritory', 'Cost Code']].copy()
        df['BU'] = mitra_bu_last
        df.dropna(axis=0, how='all', inplace=True)
        
        # Map Jenis Karyawan to Status
        mapping = {'K': 'K', 'M': 'MT', 'D': 'DW'}
        df['Status'] = df['Jenis Karyawan'].map(mapping)
        
        # Rename columns
        df.rename(columns={
            'Full Name': 'Employee Name', 
            'Period': 'Periode', 
            'Org Code': 'Organization Code', 
            'Cost Code': 'CC Code',
            'Jenis Karyawan': 'EmpType'
        }, inplace=True)
        
        # Map Status to GroupingEmployeeType
        mapping = {'DW': 'Mitra', 'MT': 'Mitra', 'K': 'Mitra'}
        df['GroupingEmployeeType'] = df['Status'].map(mapping)
        df['Internal/Mitra'] = 'Mitra'
        
        return df
    except Exception as e:
        return None

def process_mitra_n_sheet(file, sheet_name):
    """Process Mitra N sheet"""
    try:
        df = pd.read_excel(file, sheet_name=sheet_name)
        df.dropna(axis=0, how='all', inplace=True)
        df = df[['Periode', 'Employee ID', 'Employee Name', 'Join Date', 'EmpType', 
                'Job Title', 'Organization Code', 'Organization Name', 'Company Code', 
                'BU', 'New Location By CC', 'Teritory', 'CC Code', 'Status']].copy()
        df['Employee ID'] = df['Employee ID'].apply(lambda x: str(int(x)).zfill(11) if pd.notnull(x) else x)
        df['GroupingEmployeeType'] = df['Status'].map({'DW': 'Mitra', 'MT': 'Mitra', 'PKWT': 'Mitra'})
        df['Internal/Mitra'] = 'Mitra'
        return df
    except Exception as e:
        return None

def process_non_mitra_sheet(file, sheet_name):
    """Process Non Mitra sheet"""
    try:
        df = pd.read_excel(file, sheet_name=sheet_name, header=1)
        
        # Rename columns efficiently
        column_mapping = {
            'Period': 'period', 'Employee ID': 'employee_id', 'ID Card': 'id_card',
            'PIN': 'pin', 'Full Name': 'full_name', 'Job Title': 'job_title',
            'Mitra': 'mitra', 'Location Code': 'location_code', 'Location Name': 'location_name',
            'Cost Code': 'cost_code', 'Cost Name': 'cost_name', 'BU Code': 'bu_code',
            'BU': 'bu_1', 'Org Code': 'org_code', 'Dept': 'dept', 'Gender': 'gender',
            'Birth Date': 'birth_date', 'Join Date': 'join_date',
            'Jenis Karyawan': 'jenis_karyawan', 'Basic Salary': 'basic_salary', 'BU.1': 'bu_2',
            'New Location By CC': 'new_location_by_cc', 'Teritory Name': 'territory_name',
            'Section': 'section', 'HO/Non HO': 'ho_non_ho', 'HO/Store': 'ho_store',
            'BU/Supporting': 'bu_supporting'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        df.dropna(axis=0, how='all', inplace=True)
        
        # Convert period to datetime and set to last day of month
        df['period'] = pd.to_datetime(df['period'], format='%b %y', errors='coerce')
        df['period'] = df['period'] + pd.offsets.MonthEnd(0)
        
        # Convert date columns
        date_cols = ['birth_date', 'join_date']
        for col in date_cols:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    except Exception as e:
        return None

def process_excel_file(file, file_type):
    """Process uploaded Excel file based on type"""
    try:
        if file_type == "Internal Employee":
            df = pd.read_excel(file, sheet_name='Data')
            df = df[['Periode', 'Employee ID', 'Employee Name', 'EmpType', 
                    'Job Title', 'Organization Code', 'Organization Name', 'Company Code', 
                    'BU', 'New Location By CC', 'Teritory', 'CC Code', 'Status']].copy()
            df.dropna(axis=0, how='all', inplace=True)
            df['Employee ID'] = df['Employee ID'].apply(lambda x: str(int(x)).zfill(11) if pd.notnull(x) else x)
            df['GroupingEmployeeType'] = df['Status']
            df['Internal/Mitra'] = 'Internal'
            return [df], ['Internal Employee'], ['internal']
            
        else:  # Mitra
            dfs = []
            sheet_names = []
            sheet_types = []
            
            # Try to read Mitra N sheet
            df_mitra_n = process_mitra_n_sheet(file, 'Mitra N')
            if df_mitra_n is not None:
                dfs.append(df_mitra_n)
                sheet_names.append('Mitra N')
                sheet_types.append('mitra')
            
            # Try to read Mitra sheet
            df_mitra = process_mitra_sheet(file, 'Mitra')
            if df_mitra is not None:
                dfs.append(df_mitra)
                sheet_names.append('Mitra')
                sheet_types.append('mitra')
            
            # Try to read Non Mitra sheet
            df_non_mitra = process_non_mitra_sheet(file, 'Non Mitra')
            if df_non_mitra is not None:
                dfs.append(df_non_mitra)
                sheet_names.append('Non Mitra')
                sheet_types.append('non_mitra')
            
            if not dfs:
                st.error("Ensure you upload the correct file! \n\n No valid sheets found in the file.")
                return None, None, None
            
            # Show info about which sheets were found
            found_sheets = []
            if any(s == 'Mitra N' for s in sheet_names):
                found_sheets.append("'Mitra N'")
            if any(s == 'Mitra' for s in sheet_names):
                found_sheets.append("'Mitra'")
            if any(s == 'Non Mitra' for s in sheet_names):
                found_sheets.append("'Non Mitra'")
            
            st.info(f"✓ Found sheet: {', '.join(found_sheets)}")
            
            return dfs, sheet_names, sheet_types
        
    except Exception as e:
        st.error(f"Ensure you upload the correct file! \n\n Error processing file: {e}")
        return None, None

def merge_with_hcm(df):
    """Merge data with HCM database"""
    employee_hcm = load_hcm_data()
    if employee_hcm.empty:
        return df
    
    df_merged = pd.merge(df, employee_hcm, how='left', 
                        left_on='Employee ID', right_on='ME_EMPLOYEE_ID')
    
    df_merged.rename(columns={
        'ME_SEX': 'Gender',
        'ME_BIRTH_DATE': 'Birth Date',
        'ME_JOB_LEVEL': 'Job Level'
    }, inplace=True)
    
    df_merged['Join Date'] = df_merged['ME_START_DATE']
    df_merged.drop(['Organization Name', 'Company Code', 'ME_START_DATE', 'ME_EMPLOYEE_ID'], 
                  axis=1, inplace=True, errors='ignore')
    
    return df_merged

def merge_with_fte_history(df, is_non_mitra=False):
    """Merge employee data with FTE history (meh_date/meh_employee_id with periode/employee_id)"""
    try:
        fte_history = load_fte_history_data()
        if fte_history.empty:
            return df

        # Normalize fte_history keys and dates
        fte_history['meh_employee_id'] = fte_history['meh_employee_id'].astype(str).str.strip()
        fte_history['meh_date'] = pd.to_datetime(fte_history['meh_date'], errors='coerce')

        if is_non_mitra:
            # For non_mitra: join on employee_id and period (month period)
            df['period'] = pd.to_datetime(df['period'], errors='coerce')
            df['employee_id'] = df['employee_id'].astype(str).str.strip()

            df['_merge_period'] = df['period'].dt.to_period('M')
            fte_history['_merge_period'] = fte_history['meh_date'].dt.to_period('M')

            df_merged = pd.merge(
                df, fte_history, how='left',
                left_on=['employee_id', '_merge_period'],
                right_on=['meh_employee_id', '_merge_period']
            )

            df_merged.drop('_merge_period', axis=1, inplace=True)
        else:
            # For internal/mitra: join on Employee ID and Periode (month period)
            df['Periode'] = pd.to_datetime(df['Periode'], format='%b %y', errors='coerce')
            df['Employee ID'] = df['Employee ID'].astype(str).str.strip()

            df['_merge_period'] = df['Periode'].dt.to_period('M')
            fte_history['_merge_period'] = fte_history['meh_date'].dt.to_period('M')

            df_merged = pd.merge(
                df, fte_history, how='left',
                left_on=['Employee ID', '_merge_period'],
                right_on=['meh_employee_id', '_merge_period']
            )

            df_merged.drop('_merge_period', axis=1, inplace=True)

        return df_merged
    except Exception as e:
        st.error(f"Error merging with FTE history: {e}")
        return df

def finalize_data(df, file_type):
    """Finalize data structure with all required columns including FTE history"""
    final_cols = [
        'Periode', 'Employee ID', 'Employee Name', 'Join Date', 'EmpType',
        'Job Title', 'Organization Code', 'BU', 'New Location By CC', 'Teritory',
        'CC Code', 'Status', 'GroupingEmployeeType', 'Internal/Mitra',
        'Gender', 'Birth Date', 'Job Level', 'meh_date', 'meh_employee_id',
        'ME_END_DATE', 'reason_resign_name', 'reason_resign_proint_name', 'mrrp_category'
    ]
    
    for col in final_cols:
        if col not in df.columns:
            df[col] = None
    
    df = df[final_cols].copy()
    
    # Convert dates and set to last day of month
    df['Periode'] = pd.to_datetime(df['Periode'], format='%b %y', errors='coerce')
    df['Periode'] = df['Periode'] + pd.offsets.MonthEnd(0)
    for col in ['Join Date', 'Birth Date', 'meh_date', 'ME_END_DATE']:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Standardize employee types
    df.loc[df['GroupingEmployeeType'] == 'PKWTT', 'GroupingEmployeeType'] = 'Permanent'
    df.loc[df['GroupingEmployeeType'] == 'PKWT', 'GroupingEmployeeType'] = 'Contract'
    
    # For Mitra, set Job Level to None
    if file_type == "Mitra":
        df['Job Level'] = None
    return df

def finalize_non_mitra_data(df):
    """Finalize non_mitra data structure with all required columns"""
    final_cols = [
        'employee_id', 'period', 'id_card', 'pin', 'full_name', 'job_title',
        'mitra', 'location_code', 'location_name', 'cost_code', 'cost_name',
        'bu_code', 'bu_1', 'org_code', 'dept', 'gender', 'birth_date',
        'join_date', 'jenis_karyawan', 'basic_salary', 'bu_2', 'new_location_by_cc',
        'territory_name', 'section', 'ho_non_ho', 'ho_store', 'bu_supporting'
    ]
    
    for col in final_cols:
        if col not in df.columns:
            df[col] = None
    
    df = df[final_cols].copy()
    
    # Convert dates
    for col in ['period', 'join_date', 'birth_date']:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Convert basic_salary to numeric
    df['basic_salary'] = pd.to_numeric(df['basic_salary'], errors='coerce')
    
    return df

def filter_new_records(df, existing_keys, is_non_mitra=False):
    """Filter out duplicate records based on employee_id and periode/period"""
    if is_non_mitra:
        df['_check_key'] = df['employee_id'].astype(str) + '_' + df['period'].dt.to_period('M').dt.to_timestamp(freq='M', how='end').dt.strftime('%Y-%m-%d')
    else:
        df['_check_key'] = df['Employee ID'].astype(str) + '_' + df['Periode'].dt.to_period('M').dt.to_timestamp(freq='M', how='end').dt.strftime('%Y-%m-%d')
    
    new_records = df[~df['_check_key'].isin([str(k[0]) + '_' + str(k[1]) for k in existing_keys])].copy()
    new_records.drop('_check_key', axis=1, inplace=True)
    return new_records

def insert_to_database(df, engine, table_name='MasterTableNew_v2'):
    """Insert data to database"""
    try:
        if table_name == 'non_mitra':
            # Non Mitra specific dtype mapping
            dtype_map = {
                "employee_id": String(50),
                "period": Date(),
                "id_card": String(50),
                "pin": String(50),
                "full_name": String(255),
                "job_title": String(255),
                "mitra": String(255),
                "location_code": String(50),
                "location_name": String(255),
                "cost_code": String(50),
                "cost_name": String(255),
                "bu_code": String(50),
                "bu_1": String(255),
                "org_code": String(50),
                "dept": String(255),
                "gender": String(50),
                "birth_date": Date(),
                "join_date": Date(),
                "jenis_karyawan": String(50),
                "basic_salary": String(50),
                "bu_2": String(255),
                "new_location_by_cc": String(255),
                "territory_name": String(255),
                "section": String(255),
                "ho_non_ho": String(50),
                "ho_store": String(50),
                "bu_supporting": String(255)
            }
            df.to_sql(table_name, con=engine, if_exists='append', 
                     index=False, dtype=dtype_map, chunksize=1000)
        else:
            # MasterTableNew_v2 dtype mapping with FTE history columns
            df_sql = df.rename(columns=lambda x: x.strip().replace(" ", "_").replace("/", "_").replace("-", "_").lower())
            
            dtype_map = {
                "employee_id": String(11), "employee_name": String(255), "emptype": String(50),
                "job_title": String(255), "organization_code": String(50), "bu": String(100),
                "new_location_by_cc": String(255), "teritory": String(255), "cc_code": String(50),
                "status": String(50), "groupingemployeetype": String(100), "internal_mitra": String(50),
                "gender": String(20), "job_level": String(50), "periode": Date(), "join_date": Date(),
                "birth_date": Date(), "meh_date": Date(), "meh_employee_id": String(50),
                "me_end_date": Date(), "reason_resign_name": String(255),
                "reason_resign_proint_name": String(255), "mrrp_category": String(100)
            }
            
            df_sql.to_sql(table_name, con=engine, if_exists='append', 
                         index=False, dtype=dtype_map, chunksize=1000)
        return True
    except Exception as e:
        st.error(f"Error inserting to database: {e}")
        return False

def main():
    st.title("Employee Data Upload System")
    st.markdown("Upload employee data to insert new records into the database.")
    
    # Membuat kolom untuk membatasi lebar tombol agar tidak terlalu besar
    # [1, 4] berarti tombol hanya mengambil 1/5 lebar layar (20%)
    col_btn, col_spacer = st.columns([1, 4])
    
    with col_btn:
        download_template_file_path = "template-employee-data.xlsx"
        try:
            with open(download_template_file_path, "rb") as f:
                st.download_button(
                    label="Download Template",
                    data=f,
                    file_name="template-employee-data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True # Mengikuti lebar kolom [1] saja
                )
        except FileNotFoundError:
            st.error("Template not found")

    st.divider()
    
    engine = get_db_engine()
    if engine is None:
        st.stop()
    
    file_type = st.selectbox(
        "Select Data Type",
        ["Internal Employee", "Mitra"],
        help="Choose the type of employee data you're uploading"
    )
    
    uploaded_file = st.file_uploader(
        "Choose an Excel file",
        type=['xlsx', 'xls'],
        help="Upload the employee data Excel file"
    )
    
    if uploaded_file is not None:
        with st.spinner("Processing file..."):
            result = process_excel_file(uploaded_file, file_type)
            
            if result is not None and result[0] is not None:
                dfs, sheet_names, sheet_types = result
                
                existing_keys = load_existing_keys(engine)
                existing_non_mitra_keys = load_existing_non_mitra_keys(engine)
                
                all_new_records = []
                
                for idx, (df, sheet_name, sheet_type) in enumerate(zip(dfs, sheet_names, sheet_types)):
                    if sheet_type == 'non_mitra':
                        # Process Non Mitra: no FTE history merge needed
                        df = finalize_non_mitra_data(df)
                        new_records = filter_new_records(df, existing_non_mitra_keys, is_non_mitra=True)
                        if len(new_records) > 0:
                            all_new_records.append((new_records, sheet_name, sheet_type))
                    else:
                        # Process Mitra/Mitra N/Internal
                        # Only merge with HCM for Internal Employee and Mitra N
                        if file_type == "Internal Employee" or sheet_name == "Mitra N":
                            df = merge_with_hcm(df)
                        
                        # Merge with FTE history for all mitra/internal
                        df = merge_with_fte_history(df, is_non_mitra=False)
                        
                        df = finalize_data(df, file_type)
                        new_records = filter_new_records(df, existing_keys, is_non_mitra=False)
                        
                        if len(new_records) > 0:
                            all_new_records.append((new_records, sheet_name, sheet_type))
                
                # Display summary
                total_new = sum(len(nr[0]) for nr in all_new_records)
                st.info(f"New Data: {total_new}")
                
                if total_new > 0:
                    # Display each sheet separately
                    for new_records, sheet_name, sheet_type in all_new_records:
                        st.write(f"**{sheet_name}: {len(new_records)} new records**")
                        st.dataframe(new_records, width='stretch', height=400)
                    
                    if st.button("Insert All New Records to Database", type="primary", use_container_width=True):
                        with st.spinner("Inserting data..."):
                            success_count = 0
                            
                            # Group by table type
                            mitra_records = [nr[0] for nr in all_new_records if nr[2] in ['mitra', 'internal']]
                            non_mitra_records = [nr[0] for nr in all_new_records if nr[2] == 'non_mitra']
                            
                            # Insert Mitra/Internal records to MasterTableNew_v2
                            if mitra_records:
                                combined_mitra = pd.concat(mitra_records, ignore_index=True)
                                if insert_to_database(combined_mitra, engine, 'MasterTableNew_v2'):
                                    success_count += len(combined_mitra)
                            
                            # Insert Non Mitra records to non_mitra table
                            if non_mitra_records:
                                combined_non_mitra = pd.concat(non_mitra_records, ignore_index=True)
                                if insert_to_database(combined_non_mitra, engine, 'non_mitra'):
                                    success_count += len(combined_non_mitra)
                            
                            if success_count > 0:
                                st.success(f"Successfully inserted {success_count} records")
                                load_existing_keys.clear()
                                load_existing_non_mitra_keys.clear()
                                st.rerun()
                else:
                    st.success("No new data to insert. All data already exists in database.")

if __name__ == "__main__":
    main()