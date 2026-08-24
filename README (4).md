# Sales Analysis Streamlit App

A 4-section sales analysis dashboard built on your Sales Data Sheet
(Year, Month, Item No., Item Description, Customer Code, Customer Name,
Quantity, Sales Amt, Gross Profit (currency), Gross Profit, Gross Profit %,
Column1, Zone).

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. Get your data into the app

I could not read your Google Sheet directly — it isn't shared publicly, so
this app expects the data to come in one of two ways, chosen in the sidebar:

**Option A — Upload a file (simplest)**
In Google Sheets: `File → Download → Comma Separated Values (.csv)` (make
sure the *Sheet1* tab is the active tab when you download), then upload that
file with the "Upload CSV or XLSX" control in the sidebar.

**Option B — Live link to Google Sheets**
1. In Google Sheets: `File → Share → Publish to web`, choose the `Sheet1`
   tab, format **CSV**, and publish.
2. Copy the generated URL (it looks like
   `https://docs.google.com/spreadsheets/d/e/XXXX/pub?gid=0&single=true&output=csv`)
   and paste it into the "Google Sheet CSV export URL" box in the sidebar.
3. Click **Load / Refresh Data** any time the sheet changes.

> Note: `Publish to web` makes the data viewable by anyone with the link —
> only use this if that's acceptable for your data.

## 3. Run

```bash
streamlit run app.py
```

## How Sales Type is determined

There's no explicit "Sales Type" column in the sheet, so it's derived from
the **Item No.** prefix, per your spec:

`FEED, PROB, PUMP, CHEM, GEOM, PADW, PAIT, GEIT, TEST, OTHE`

Any Item No. that doesn't start with one of the first nine codes is bucketed
into `OTHE`. Selecting **All Sales** removes this filter entirely.

## The 4 sections (in the right-hand sidebar)

1. **Zone Wise Sale Analysis** — filters: Sales Type, Zone, Time Frame
   (Yearly / Monthly / Quarterly). Line chart of total Sales Amt over time,
   with each point labeled.
2. **Item Wise Sales Analysis** — filters: Zone, Sales Type, Time Frame,
   then an Item Description dropdown (scoped to the chosen Zone + Sales
   Type). Line chart of that item's Sales Amt over time.
3. **Sales % Contribution Analysis** — filters: Sales Type, Time Frame,
   Zone. Table of Customer Name (Code) × Time Frame period, where each cell
   is that customer's share (%) of total sales for the chosen Zone + Sales
   Type in that period. Each column sums to 100% (a check-total row is
   shown underneath).
4. **Sales % with Time Analysis** — filters: Time Frame, Zone, Sales Type,
   Customer Code. Line chart of that one customer's % contribution
   (their Sales Amt ÷ total Sales Amt for that Sales Type + Zone) over time.

## Notes / assumptions

- The sidebar is repositioned to the **right** of the screen using CSS
  (Streamlit doesn't natively support a right-hand sidebar). If a future
  Streamlit version changes its internal HTML structure, the sidebar will
  simply fall back to appearing on the left — functionality is unaffected.
- "Month" is parsed whether it's stored as a number (1–12) or a month name
  (e.g. "January" / "Jan").
- Rows with unparseable Year/Month are dropped from the analysis.
- `Gross Profit`, `Gross Profit %`, and `Column1` are loaded but not used in
  the current 4 sections — let me know if you'd like them surfaced too.

## Files

- `app.py` — main Streamlit app (all 4 sections + sidebar navigation)
- `data_utils.py` — data loading, cleaning, Sales Type classification, and
  period (Yearly/Monthly/Quarterly) helpers
- `requirements.txt` — Python dependencies
