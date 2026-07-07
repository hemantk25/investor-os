import pandas as pd

from app.prices import _frame_to_quotes


def test_frame_to_quotes_two_days():
    df = pd.DataFrame({("Close", "ALPHAMOT.NS"): [100.0, 110.0],
                       ("Close", "DELTAB.NS"): [50.0, None]})
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    q = _frame_to_quotes(df, ["ALPHAMOT", "DELTAB"])
    assert round(q["ALPHAMOT"].price, 2) == 110.0
    assert round(q["ALPHAMOT"].day_pct, 2) == 10.0
    assert q["DELTAB"].price == 50.0 and q["DELTAB"].day_pct is None
