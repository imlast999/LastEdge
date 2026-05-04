"""
News Filter Service

Pauses trading 30 minutes before and after high-impact news events
to avoid slippage and erratic price action around major releases.

Supported events (hardcoded schedule):
  - NFP: first Friday of each month at 13:30 UTC
  - CPI: second/third week of month at 13:30 UTC (approximate)
  - ECB meetings: quarterly, Thursdays at 12:15 UTC
  - Fed meetings (FOMC): 8 per year, Wednesdays at 19:00 UTC

Symbol mapping:
  - EURUSD: affected by USD and EUR news
  - XAUUSD: affected by USD news
  - BTCEUR: not affected by macro news
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Tuple, List, Dict

logger = logging.getLogger(__name__)

# Blackout window in minutes before and after each event
BLACKOUT_MINUTES = 30


class NewsFilter:
    """
    Checks whether the current time falls within a high-impact news blackout
    window for a given symbol.
    """

    # Currencies that affect each symbol
    SYMBOL_CURRENCIES: Dict[str, List[str]] = {
        'EURUSD': ['USD', 'EUR'],
        'XAUUSD': ['USD'],
        'BTCEUR': [],   # crypto — not affected by macro news
    }

    def is_news_blackout(self, symbol: str) -> Tuple[bool, str]:
        """
        Returns (True, reason) if the current UTC time is within 30 minutes
        of a known high-impact news event that affects the given symbol.

        Args:
            symbol: trading symbol, e.g. 'EURUSD', 'XAUUSD', 'BTCEUR'

        Returns:
            (is_blackout, reason_string)
        """
        try:
            affected_currencies = self.SYMBOL_CURRENCIES.get(symbol.upper(), [])
            if not affected_currencies:
                return False, ""

            now = datetime.now(timezone.utc)
            upcoming_events = self._get_upcoming_events(now, affected_currencies)

            for event in upcoming_events:
                event_time = event['time']
                delta = abs((now - event_time).total_seconds() / 60)
                if delta <= BLACKOUT_MINUTES:
                    direction = "antes de" if now < event_time else "después de"
                    reason = (
                        f"{event['name']} ({event['currency']}) "
                        f"a las {event_time.strftime('%H:%M')} UTC — "
                        f"{int(delta)} min {direction} del evento"
                    )
                    return True, reason

            return False, ""

        except Exception as e:
            logger.warning(f"NewsFilter error for {symbol}: {e}")
            return False, ""

    def _get_upcoming_events(
        self, now: datetime, currencies: List[str]
    ) -> List[Dict]:
        """
        Returns a list of high-impact events within the next/previous 24 hours
        that affect the given currencies.
        """
        events = []

        # Check events for today and tomorrow to catch boundary cases
        for day_offset in (-1, 0, 1):
            check_date = (now + timedelta(days=day_offset)).date()
            year = check_date.year
            month = check_date.month
            day = check_date.day
            weekday = check_date.weekday()  # 0=Monday, 4=Friday

            # ── NFP: first Friday of each month at 13:30 UTC ─────────────────
            if 'USD' in currencies:
                first_friday = self._first_weekday_of_month(year, month, 4)  # 4=Friday
                if check_date == first_friday:
                    events.append({
                        'name': 'NFP (Non-Farm Payrolls)',
                        'currency': 'USD',
                        'time': datetime(year, month, day, 13, 30, tzinfo=timezone.utc),
                    })

            # ── CPI USA: second/third week, typically Tuesday/Wednesday 13:30 UTC
            # Approximate: 2nd Tuesday of each month
            if 'USD' in currencies:
                second_tuesday = self._nth_weekday_of_month(year, month, 1, 2)  # 1=Tuesday, 2nd
                if check_date == second_tuesday:
                    events.append({
                        'name': 'CPI USA',
                        'currency': 'USD',
                        'time': datetime(year, month, day, 13, 30, tzinfo=timezone.utc),
                    })

            # ── Fed FOMC: 8 meetings per year, typically Wednesdays at 19:00 UTC
            # Approximate schedule: Jan, Mar, May, Jun, Jul, Sep, Nov, Dec
            # Use 2nd Wednesday of those months as approximation
            if 'USD' in currencies and month in (1, 3, 5, 6, 7, 9, 11, 12):
                second_wednesday = self._nth_weekday_of_month(year, month, 2, 2)  # 2=Wednesday, 2nd
                if check_date == second_wednesday:
                    events.append({
                        'name': 'Fed FOMC Meeting',
                        'currency': 'USD',
                        'time': datetime(year, month, day, 19, 0, tzinfo=timezone.utc),
                    })

            # ── ECB Meeting: quarterly, typically Thursdays at 12:15 UTC
            # Approximate: 2nd Thursday of Jan, Apr, Jun, Sep
            if 'EUR' in currencies and month in (1, 4, 6, 9):
                second_thursday = self._nth_weekday_of_month(year, month, 3, 2)  # 3=Thursday, 2nd
                if check_date == second_thursday:
                    events.append({
                        'name': 'ECB Meeting',
                        'currency': 'EUR',
                        'time': datetime(year, month, day, 12, 15, tzinfo=timezone.utc),
                    })

            # ── ECB Press Conference: same day as meeting at 12:45 UTC
            if 'EUR' in currencies and month in (1, 4, 6, 9):
                second_thursday = self._nth_weekday_of_month(year, month, 3, 2)
                if check_date == second_thursday:
                    events.append({
                        'name': 'ECB Press Conference',
                        'currency': 'EUR',
                        'time': datetime(year, month, day, 12, 45, tzinfo=timezone.utc),
                    })

        # Filter to events within ±24h of now
        window = timedelta(hours=24)
        return [e for e in events if abs((now - e['time']).total_seconds()) <= window.total_seconds()]

    @staticmethod
    def _first_weekday_of_month(year: int, month: int, weekday: int):
        """Returns the date of the first occurrence of `weekday` in the given month.
        weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
        """
        import calendar
        first_day = datetime(year, month, 1).date()
        days_ahead = weekday - first_day.weekday()
        if days_ahead < 0:
            days_ahead += 7
        return first_day + timedelta(days=days_ahead)

    @staticmethod
    def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int):
        """Returns the date of the nth occurrence of `weekday` in the given month.
        weekday: 0=Monday, ..., 6=Sunday; n: 1=first, 2=second, etc.
        """
        from datetime import date
        first_day = date(year, month, 1)
        days_ahead = weekday - first_day.weekday()
        if days_ahead < 0:
            days_ahead += 7
        first_occurrence = first_day + timedelta(days=days_ahead)
        return first_occurrence + timedelta(weeks=(n - 1))
