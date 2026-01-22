# Employee Data Upload System

A Streamlit-based web application for uploading and managing employee data into multiple database tables. The system supports internal employees, mitra (contractor/partner) employees, and non-mitra employees with automated data validation, merging with HCM systems, and FTE history tracking.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Database Structure](#database-structure)
- [Data Processing Flow](#data-processing-flow)
- [Column Mappings](#column-mappings)
- [Architecture](#architecture)

## Features

- **Multiple Employee Types**: Support for Internal Employee, Mitra, Mitra N, and Non-Mitra data
- **Data Validation**: Automatic detection and prevention of duplicate records
- **HCM Integration**: Merges employee data with HCM database for enriched information
- **FTE History Tracking**: Integrates FTE history and resignation details from HCM (for Internal/Mitra employees)
- **Period Standardization**: Automatically converts all periods to the last day of the month for consistency
- **Batch Processing**: Handles multiple sheets and thousands of records with chunk insertion
- **Real-time Feedback**: Shows preview of new records before database insertion
- **Caching**: Uses Streamlit caching for improved performance on repeated queries

## Requirements

- Python 3.7+
- Streamlit
- Pandas
- SQLAlchemy
- MySQL Connector
- python-dateutil

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd insertNewDataEmployee
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The application requires database credentials stored in Streamlit secrets. Create a `.streamlit/secrets.toml` file:

```toml
[database]
host = "your_database_host"
port = 3306
database = "your_database_name"
username = "your_username"
password = "your_password"

[hcm_database]
host = "your_hcm_host"
port = 3306
database = "your_hcm_database"
username = "your_hcm_username"
password = "your_hcm_password"
```

## Usage

1. Start the application:
```bash
streamlit run app.py
```

2. Open your browser and navigate to `http://ipaddress:8501`

3. Select the data type (Internal Employee or Mitra)

4. Upload an Excel file containing:
   - For **Internal Employee**: A "Data" sheet
   - For **Mitra**: "Mitra N", "Mitra", and/or "Non Mitra" sheets

5. Review the preview of new records

6. Click "Insert All New Records to Database" to save

## Database Structure

### MasterTableNew_v2 Table (Internal/Mitra Employees)

| Column | Type | Description |
|--------|------|-------------|
| employee_id | VARCHAR(11) | Employee identifier |
| periode | DATE | Period (last day of month) |
| employee_name | VARCHAR(255) | Full name |
| join_date | DATE | Join date |
| emptype | VARCHAR(50) | Employee type |
| job_title | VARCHAR(255) | Job title |
| organization_code | VARCHAR(50) | Organization code |
| bu | VARCHAR(100) | Business unit |
| new_location_by_cc | VARCHAR(255) | Location |
| teritory | VARCHAR(255) | Territory |
| cc_code | VARCHAR(50) | Cost center code |
| status | VARCHAR(50) | Employee status |
| groupingemployeetype | VARCHAR(100) | Grouping type |
| internal_mitra | VARCHAR(50) | Internal or Mitra |
| gender | VARCHAR(20) | Gender |
| birth_date | DATE | Birth date |
| job_level | VARCHAR(50) | Job level |
| meh_date | DATE | FTE history date |
| meh_employee_id | VARCHAR(50) | FTE history employee ID |
| me_end_date | DATE | End date |
| reason_resign_name | VARCHAR(255) | Resignation reason |
| reason_resign_proint_name | VARCHAR(255) | Resignation point |
| mrrp_category | VARCHAR(100) | Resignation category |

### non_mitra Table

| Column | Type | Description |
|--------|------|-------------|
| employee_id | VARCHAR(50) | Employee identifier |
| period | DATE | Period (last day of month) |
| id_card | VARCHAR(50) | ID card number |
| pin | VARCHAR(50) | PIN |
| full_name | VARCHAR(255) | Full name |
| job_title | VARCHAR(255) | Job title |
| mitra | VARCHAR(255) | Mitra name |
| location_code | VARCHAR(50) | Location code |
| location_name | VARCHAR(255) | Location name |
| cost_code | VARCHAR(50) | Cost code |
| cost_name | VARCHAR(255) | Cost name |
| bu_code | VARCHAR(50) | Business unit code |
| bu_1 | VARCHAR(255) | Business unit 1 |
| org_code | VARCHAR(50) | Organization code |
| dept | VARCHAR(255) | Department |
| gender | VARCHAR(50) | Gender |
| birth_date | DATE | Birth date |
| join_date | DATE | Join date |
| jenis_karyawan | VARCHAR(50) | Employee type |
| basic_salary | VARCHAR(50) | Basic salary |
| bu_2 | VARCHAR(255) | Business unit 2 |
| new_location_by_cc | VARCHAR(255) | New location |
| territory_name | VARCHAR(255) | Territory name |
| section | VARCHAR(255) | Section |
| ho_non_ho | VARCHAR(50) | HO/Non-HO |
| ho_store | VARCHAR(50) | HO/Store |
| bu_supporting | VARCHAR(255) | Supporting BU |

## Data Processing Flow

### Internal Employee Flow
1. Read "Data" sheet from Excel
2. Normalize employee IDs (11 digits with leading zeros)
3. Merge with HCM data (Job Level, Gender, Birth Date, Start Date)
4. Merge with FTE history data
5. Finalize data structure
6. Filter new records (based on employee_id + period)
7. Display preview
8. Insert to `MasterTableNew_v2` table

### Mitra Flow
1. Read multiple sheets (Mitra N, Mitra, Non Mitra)
2. **For Mitra N & Mitra sheets**:
   - Normalize employee IDs
   - Merge with HCM data (for Mitra N only)
   - Merge with FTE history
   - Filter new records
   - Insert to `MasterTableNew_v2`
3. **For Non Mitra sheet**:
   - Rename columns as per mapping
   - Convert period to last day of month
   - Filter new records
   - Insert to `non_mitra` table

## Column Mappings

### Internal/Mitra Column Mapping (from Excel to Database)

| Excel | Database |
|-------|----------|
| Periode | periode |
| Employee ID | employee_id |
| Employee Name | employee_name |
| EmpType | emptype |
| Job Title | job_title |
| Organization Code | organization_code |
| BU | bu |
| New Location By CC | new_location_by_cc |
| Teritory | teritory |
| CC Code | cc_code |
| Status | status |

### Non-Mitra Column Mapping

| Excel | Database |
|-------|----------|
| Period | period |
| Employee ID | employee_id |
| ID Card | id_card |
| PIN | pin |
| Full Name | full_name |
| Job Title | job_title |
| Mitra | mitra |
| Location Code | location_code |
| Location Name | location_name |
| Cost Code | cost_code |
| Cost Name | cost_name |
| BU Code | bu_code |
| BU | bu_1 |
| Org Code | org_code |
| Dept | dept |
| Gender | gender |
| Birth Date | birth_date |
| Join Date | join_date |
| Jenis Karyawan | jenis_karyawan |
| Basic Salary | basic_salary |
| BU.1 | bu_2 |
| New Location By CC | new_location_by_cc |
| Teritory Name | territory_name |
| Section | section |
| HO/Non HO | ho_non_ho |
| HO/Store | ho_store |
| BU/Supporting | bu_supporting |

## Architecture

### Key Functions

#### Database Connection
- `get_db_engine()`: Creates connection to main database
- `get_hcm_engine()`: Creates connection to HCM database

#### Data Loading
- `load_existing_keys()`: Retrieves existing employee_id + period combinations
- `load_existing_non_mitra_keys()`: Retrieves existing non_mitra records
- `load_fte_history_data()`: Loads FTE history and resignation details
- `load_hcm_data()`: Loads HCM employee information

#### Data Processing
- `process_excel_file()`: Main orchestrator for file processing
- `process_mitra_sheet()`: Processes Mitra sheet
- `process_mitra_n_sheet()`: Processes Mitra N sheet
- `process_non_mitra_sheet()`: Processes Non Mitra sheet
- `merge_with_hcm()`: Enriches data with HCM information
- `merge_with_fte_history()`: Adds FTE and resignation details
- `finalize_data()`: Prepares final data structure for Internal/Mitra
- `finalize_non_mitra_data()`: Prepares final data structure for Non-Mitra
- `filter_new_records()`: Identifies new records not in database
- `insert_to_database()`: Inserts records into appropriate table

#### UI
- `main()`: Streamlit app main function

### Date Handling

All period dates are standardized to the **last day of the month**:
- Excel input: "Jan 26" format
- Processing: Converted to datetime and `MonthEnd(0)` applied
- Database: Stored as YYYY-MM-DD (last day)
- Comparison: Uses `DATE_FORMAT(LAST_DAY(period), '%Y-%m-%d')` in SQL

### Duplicate Detection

Records are considered duplicates based on:
- **employee_id** + **period** combination

New records are identified by comparing against existing database records using a composite key.

## Error Handling

The application includes error handling for:
- Database connection failures
- Missing or invalid sheets
- Date parsing errors
- Data type conversion errors
- File upload issues

All errors are displayed to the user in the Streamlit UI.

## Troubleshooting

### "No valid sheets found in the file"
- Ensure your Excel file has correct sheet names: "Data", "Mitra N", "Mitra", or "Non Mitra"

### "Error loading existing data"
- Check database connection in secrets.toml
- Verify user permissions on the database

### "All data already exists in database"
- Check if the period is already in the database
- Verify employee IDs match (should be 11 digits with leading zeros)


