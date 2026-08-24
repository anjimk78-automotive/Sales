"""
data_utils.py
Shared data loading, cleaning, and helper functions for the Sales Analysis app.
"""

import re
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Sales Type configuration
# ---------------------------------------------------------------------------
# Order matters only in that longer/more-specific codes should be checked
# first if there were ever overlapping prefixes. Currently all are distinct.
SALES_TYPE_CODES = [
    "FEED", "PROB", "PUMP", "CHEM", "GEOM",
    "PADW", "PAIT", "GEIT", "TEST", "OTHR",
]
ALL_SALES_LABEL = "All Sales"
SALES_TYPE_OPTIONS = [ALL_SALES_LABEL] + SALES_TYPE_CODES

ALL_ZONES_LABEL = "All Zones"

TIME_FRAME_OPTIONS = ["Yearly", "Monthly", "Quarterly"]

MONTH_NAME_TO_NUM = {
    "JAN": 1, "JANUARY": 1, "FEB": 2, "FEBRUARY": 2, "MAR": 3, "MARCH": 3,
    "APR": 4, "APRIL": 4, "MAY": 5, "JUN": 6, "JUNE": 6, "JUL": 7, "JULY": 7,
    "AUG": 8, "AUGUST": 8, "SEP": 9, "SEPT": 9, "SEPTEMBER": 9,
    "OCT": 10, "OCTOBER": 10, "NOV": 11, "NOVEMBER": 11, "DEC": 12, "DECEMBER": 12,
}


def classify_sales_type(item_no: str) -> str:
    """Return the Sales Type code for a given Item No., based on its prefix.
    Falls back to 'OTHR' if no known prefix matches."""
    if not isinstance(item_no, str):
        return "OTHR"
    code = item_no.strip().upper()
    for prefix in SALES_TYPE_CODES:
        if code.startswith(prefix):
            return prefix
    return "OTHR"


def _month_to_num(month_val) -> int:
    """Convert a Month cell (number, numeric-string, or month name) to 1-12."""
    if pd.isna(month_val):
        return None
    # Already numeric
    try:
        m = int(float(month_val))
        if 1 <= m <= 12:
            return m
    except (ValueError, TypeError):
        pass
    # Text month name
    text = re.sub(r"[^A-Za-z]", "", str(month_val)).upper()
    return MONTH_NAME_TO_NUM.get(text, None)


@st.cache_data(show_spinner=False)
def load_dataframe(file_or_buffer, sheet_name: str = "Sheet1") -> pd.DataFrame:
    """Load the raw sales data from an uploaded CSV/XLSX file-like object."""
    name = getattr(file_or_buffer, "name", "") or ""
    if name.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(file_or_buffer, sheet_name=sheet_name)
    else:
        df = pd.read_csv(file_or_buffer)
    return df


def normalize_google_sheet_url(url: str, gid: str = "0") -> str:
    """Accept any normal Google Sheets URL (the /edit?usp=sharing link you
    copy from the Share button, a /pub link, or an already-correct export
    link) and turn it into a direct CSV export URL.

    This only works if the sheet's general access is set to
    'Anyone with the link' (Viewer) -- Google will still reject the request
    with a 401 for restricted/private sheets, since there is no login here.
    """
    url = url.strip()

    # Already a published-to-web CSV link -> use as-is.
    if "output=csv" in url or "/pub" in url and "csv" in url:
        return url

    # Standard /d/<ID>/... link -> build the export URL.
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if match:
        sheet_id = match.group(1)
        gid_match = re.search(r"[?&#]gid=([0-9]+)", url)
        use_gid = gid_match.group(1) if gid_match else gid
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={use_gid}"

    # Fallback: return the URL unchanged (e.g. user already pasted an export link)
    return url


@st.cache_data(show_spinner=False)
def load_dataframe_from_url(csv_url: str) -> pd.DataFrame:
    """Load raw sales data from a public Google Sheets CSV export URL."""
    direct_url = normalize_google_sheet_url(csv_url)
    try:
        return pd.read_csv(direct_url)
    except Exception as e:
        raise ValueError(
            "Could not read the Google Sheet. Make sure its sharing setting "
            "is 'Anyone with the link' (Viewer) -- Share -> General access -- "
            f"then try again. (Underlying error: {e})"
        )


def prepare_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Clean columns, derive Sales Type, and build Yearly/Monthly/Quarterly
    period labels + numeric sort keys used across all four sections."""
    df = df_raw.copy()

    # Normalize column names (strip whitespace) but keep original labels
    df.columns = [str(c).strip() for c in df.columns]

    required = [
        "Year", "Month", "Item No.", "Item Description", "Customer Code",
        "Customer Name", "Quantity", "Sales Amt", "Zone",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"The uploaded data is missing required column(s): {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    # Types
    _NUMBER_TOKEN_RE = re.compile(r"-?\d+(?:\.\d+)?")

    def _to_number(series):
        """Robust numeric parser. Handles:
        - comma-formatted numbers stored as text, e.g. "1,500.00"
        - non-breaking / regular spaces used as thousands separators
        - accounting-style negatives in parentheses, e.g. "(1,500.00)"
        - a unicode minus sign ("−") instead of a plain hyphen
        - stray currency symbols / letters (e.g. "Rs. 500,000") -- extracts
          the actual numeric token instead of deleting letters in place,
          which avoids things like "Rs." collapsing into a decimal point
          and silently turning 500000 into 0.5.
        Returns (parsed_series, unparsed_mask) where unparsed_mask flags
        cells that had real (non-blank) content but failed to become a
        number -- these must NOT be silently treated as correct zeros.
        """
        raw = series.fillna("").astype(str).str.strip()
        was_blank = raw.isin(["", "nan", "None", "-", "–", "—"])

        cleaned = raw.str.replace("\u00a0", "", regex=False)  # non-breaking space
        cleaned = cleaned.str.replace(" ", "", regex=False)   # space thousands-sep
        cleaned = cleaned.str.replace(",", "", regex=False)
        cleaned = cleaned.str.replace("\u2212", "-", regex=False)  # unicode minus
        cleaned = cleaned.str.replace(r"^\((.*)\)$", r"-\1", regex=True)  # (1500) -> -1500

        def _extract(s):
            m = _NUMBER_TOKEN_RE.search(s)
            return float(m.group()) if m else None

        parsed = cleaned.apply(_extract)
        parsed = pd.Series(parsed, index=series.index, dtype="float64")
        unparsed_mask = parsed.isna() & ~was_blank
        return parsed, unparsed_mask

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    df["MonthNum"] = df["Month"].apply(_month_to_num)

    # Sums naturally net out negative Sales Amt (returns/discounts) rather
    # than excluding them, as long as they parse correctly. Any cell that
    # had real content but couldn't be parsed is tracked (not silently
    # zeroed) so the app can warn about it instead of hiding bad data.
    sales_parsed, sales_bad_mask = _to_number(df["Sales Amt"])
    qty_parsed, qty_bad_mask = _to_number(df["Quantity"])

    bad_sales_examples = df.loc[sales_bad_mask, "Sales Amt"].fillna("").astype(str).unique().tolist()[:10]
    bad_qty_examples = df.loc[qty_bad_mask, "Quantity"].fillna("").astype(str).unique().tolist()[:10]

    df["Sales Amt"] = sales_parsed.fillna(0.0)
    df["Quantity"] = qty_parsed.fillna(0.0)

    rows_before_period_drop = len(df)
    df = df.dropna(subset=["Year", "MonthNum"]).copy()
    df["Year"] = df["Year"].astype(int)
    df["MonthNum"] = df["MonthNum"].astype(int)
    dropped_row_count = rows_before_period_drop - len(df)

    # Sales Type derived from Item No. prefix
    df["Sales Type"] = df["Item No."].apply(classify_sales_type)

    # Zone / Customer cleanup
    df["Zone"] = df["Zone"].fillna("Unassigned").astype(str).str.strip()
    df["Zone"] = df["Zone"].replace({"": "Unassigned", "nan": "Unassigned", "None": "Unassigned"})
    df["Customer Code"] = df["Customer Code"].astype(str).str.strip()
    df["Customer Name"] = df["Customer Name"].astype(str).str.strip()
    df["Customer Display"] = df["Customer Name"] + " (" + df["Customer Code"] + ")"

    # --- Period labels + sort keys -----------------------------------
    # Yearly
    df["Period_Yearly"] = df["Year"].astype(str)
    df["Sort_Yearly"] = df["Year"]

    # Monthly  (e.g. "Jan-2025")
    abbr_lookup = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
    }
    df["Period_Monthly"] = df["MonthNum"].map(abbr_lookup) + "-" + df["Year"].astype(str)
    df["Sort_Monthly"] = df["Year"] * 100 + df["MonthNum"]

    # Quarterly (e.g. "Q1-2025")
    df["Quarter"] = ((df["MonthNum"] - 1) // 3) + 1
    df["Period_Quarterly"] = "Q" + df["Quarter"].astype(str) + "-" + df["Year"].astype(str)
    df["Sort_Quarterly"] = df["Year"] * 10 + df["Quarter"]

    # Data-quality flags surfaced by the app (not silently swallowed).
    df.attrs["sales_amt_unparsed_count"] = int(sales_bad_mask.sum())
    df.attrs["sales_amt_unparsed_examples"] = bad_sales_examples
    df.attrs["quantity_unparsed_count"] = int(qty_bad_mask.sum())
    df.attrs["quantity_unparsed_examples"] = bad_qty_examples
    df.attrs["rows_dropped_bad_period"] = dropped_row_count

    return df


PERIOD_COL = {
    "Yearly": "Period_Yearly",
    "Monthly": "Period_Monthly",
    "Quarterly": "Period_Quarterly",
}
SORT_COL = {
    "Yearly": "Sort_Yearly",
    "Monthly": "Sort_Monthly",
    "Quarterly": "Sort_Quarterly",
}


def filter_by_zone(df: pd.DataFrame, zone: str) -> pd.DataFrame:
    if zone == ALL_ZONES_LABEL:
        return df
    return df[df["Zone"] == zone]


def filter_by_sales_type(df: pd.DataFrame, sales_type: str) -> pd.DataFrame:
    if sales_type == ALL_SALES_LABEL:
        return df
    return df[df["Sales Type"] == sales_type]


def get_period_order(df: pd.DataFrame, time_frame: str):
    """Return the list of period labels in chronological order for the
    given (already filtered) dataframe."""
    period_col = PERIOD_COL[time_frame]
    sort_col = SORT_COL[time_frame]
    ordered = (
        df[[period_col, sort_col]]
        .drop_duplicates()
        .sort_values(sort_col)[period_col]
        .tolist()
    )
    return ordered
