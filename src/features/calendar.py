"""Calendar and event-based features.

Features:
    - Days to next FOMC meeting
    - Earnings season flag
    - Monthly options expiration proximity
"""

import pandas as pd

# FOMC meeting dates (2006-2026)
# Source: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
# Only the announcement dates (typically Wednesday of 2-day meetings)
# This list should be updated periodically
FOMC_DATES = [
    # 2006
    "2006-01-31", "2006-03-28", "2006-05-10", "2006-06-29",
    "2006-08-08", "2006-09-20", "2006-10-25", "2006-12-12",
    # 2007
    "2007-01-31", "2007-03-21", "2007-05-09", "2007-06-28",
    "2007-08-07", "2007-09-18", "2007-10-31", "2007-12-11",
    # 2008
    "2008-01-30", "2008-03-18", "2008-04-30", "2008-06-25",
    "2008-08-05", "2008-09-16", "2008-10-29", "2008-12-16",
    # 2009
    "2009-01-28", "2009-03-18", "2009-04-29", "2009-06-24",
    "2009-08-12", "2009-09-23", "2009-11-04", "2009-12-16",
    # 2010
    "2010-01-27", "2010-03-16", "2010-04-28", "2010-06-23",
    "2010-08-10", "2010-09-21", "2010-11-03", "2010-12-14",
    # 2011
    "2011-01-26", "2011-03-15", "2011-04-27", "2011-06-22",
    "2011-08-09", "2011-09-21", "2011-11-02", "2011-12-13",
    # 2012
    "2012-01-25", "2012-03-13", "2012-04-25", "2012-06-20",
    "2012-08-01", "2012-09-13", "2012-10-24", "2012-12-12",
    # 2013
    "2013-01-30", "2013-03-20", "2013-05-01", "2013-06-19",
    "2013-07-31", "2013-09-18", "2013-10-30", "2013-12-18",
    # 2014
    "2014-01-29", "2014-03-19", "2014-04-30", "2014-06-18",
    "2014-07-30", "2014-09-17", "2014-10-29", "2014-12-17",
    # 2015
    "2015-01-28", "2015-03-18", "2015-04-29", "2015-06-17",
    "2015-07-29", "2015-09-17", "2015-10-28", "2015-12-16",
    # 2016
    "2016-01-27", "2016-03-16", "2016-04-27", "2016-06-15",
    "2016-07-27", "2016-09-21", "2016-11-02", "2016-12-14",
    # 2017
    "2017-02-01", "2017-03-15", "2017-05-03", "2017-06-14",
    "2017-07-26", "2017-09-20", "2017-11-01", "2017-12-13",
    # 2018
    "2018-01-31", "2018-03-21", "2018-05-02", "2018-06-13",
    "2018-08-01", "2018-09-26", "2018-11-08", "2018-12-19",
    # 2019
    "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19",
    "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
    # 2020
    "2020-01-29", "2020-03-03", "2020-03-15", "2020-04-29",
    "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05", "2020-12-16",
    # 2021
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16",
    "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    # 2022
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15",
    "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    # 2023
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
    "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    # 2024
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    # 2025
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    # 2026 (add as released)
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
]


def days_to_fomc(dates: pd.DatetimeIndex) -> pd.Series:
    """Compute trading days until next FOMC announcement.

    Args:
        dates: DatetimeIndex of trading days.

    Returns:
        Series with number of calendar days to next FOMC meeting.
    """
    fomc = pd.to_datetime(FOMC_DATES)

    result = pd.Series(index=dates, dtype=int)
    for i, date in enumerate(dates):
        future_meetings = fomc[fomc >= date]
        if len(future_meetings) > 0:
            result.iloc[i] = (future_meetings[0] - date).days
        else:
            result.iloc[i] = 999  # No known future meeting

    return result


def earnings_season_flag(dates: pd.DatetimeIndex) -> pd.Series:
    """Flag earnings season periods.

    Earnings season roughly: weeks 2-5 of Jan, Apr, Jul, Oct.
    This is when aggregate market vol tends to be elevated.

    Args:
        dates: DatetimeIndex of trading days.

    Returns:
        Binary series: 1 if in earnings season, 0 otherwise.
    """
    month = dates.month
    day = dates.day

    # Earnings months: Jan(1), Apr(4), Jul(7), Oct(10)
    # Roughly day 10 to day 31 of each earnings month
    is_earnings_month = month.isin([1, 4, 7, 10])
    is_earnings_window = day >= 10

    return (is_earnings_month & is_earnings_window).astype(int)


def opex_proximity(dates: pd.DatetimeIndex) -> pd.Series:
    """Compute days to monthly options expiration (3rd Friday).

    OpEx weeks often have unusual volume and gamma effects.

    Args:
        dates: DatetimeIndex of trading days.

    Returns:
        Days until next monthly OpEx (0 = OpEx day).
    """
    result = pd.Series(index=dates, dtype=int)

    for i, date in enumerate(dates):
        # Find 3rd Friday of current month
        year, month = date.year, date.month
        first_day = pd.Timestamp(year, month, 1)
        # First Friday
        first_friday = first_day + pd.offsets.Week(weekday=4)
        if first_friday.month != month:
            first_friday = first_day + pd.offsets.Week(1, weekday=4)
        # Third Friday
        third_friday = first_friday + pd.DateOffset(weeks=2)

        if date <= third_friday:
            result.iloc[i] = (third_friday - date).days
        else:
            # Next month's third Friday
            next_month = date + pd.DateOffset(months=1)
            first_day_next = pd.Timestamp(next_month.year, next_month.month, 1)
            first_friday_next = first_day_next + pd.offsets.Week(weekday=4)
            if first_friday_next.month != next_month.month:
                first_friday_next = first_day_next + pd.offsets.Week(1, weekday=4)
            third_friday_next = first_friday_next + pd.DateOffset(weeks=2)
            result.iloc[i] = (third_friday_next - date).days

    return result


def build_calendar_features(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Build all calendar/event features.

    Args:
        dates: DatetimeIndex of trading days.

    Returns:
        DataFrame with calendar features.
    """
    features = pd.DataFrame(index=dates)

    features["days_to_fomc"] = days_to_fomc(dates)
    features["earnings_season"] = earnings_season_flag(dates)
    features["days_to_opex"] = opex_proximity(dates)

    return features
