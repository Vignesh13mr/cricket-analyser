# Cricket Analyser

A cricket statistics dashboard built with Python, Streamlit, Pandas, and DuckDB. It includes a dashboard, player analysis, player comparison, leaderboards, and match analysis.

## Data archive

The project uses `cricket_database/cricket_all_tables.duckdb`. The extracted database is excluded from Git because it is large. The included `cricket_database.zip` contains the database and its data notice.

To prepare the database after downloading or cloning this project:

1. Create the folder `cricket_database` if it does not already exist.
2. Extract `cricket_database.zip` into that folder.
3. Confirm that `cricket_database/cricket_all_tables.duckdb` exists.

## Run on Windows

From Command Prompt, open the project folder and install the required packages:

```text
py -m pip install -r requirements.txt
```

Start the dashboard:

```text
py -m streamlit run app.py
```

The optional `VK.py` file is a terminal-based version. Run it with `py VK.py` after preparing the database.

## Data attribution

The underlying ball-by-ball data is from Cricsheet, provided through the TigZig cricket API. The derived data is licensed under the Open Data Commons Attribution License 1.0 (ODC-BY 1.0). The included archive's `README.txt` contains the full notice and attribution details. License: <https://opendatacommons.org/licenses/by/1-0/>.
