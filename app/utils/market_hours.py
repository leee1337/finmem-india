from datetime import datetime, time, timedelta
import pytz

class MarketHours:
    def __init__(self):
        self.ist_tz = pytz.timezone('Asia/Kolkata')
        self.market_open_time = time(9, 15)  # 9:15 AM IST
        self.market_close_time = time(15, 30)  # 3:30 PM IST
        self.pre_market_start = time(9, 0)  # 9:00 AM IST
        self.post_market_end = time(15, 45)  # 3:45 PM IST
        
        # Market holidays 2024 (update yearly)
        self.holidays = [
            "2024-01-26",  # Republic Day
            "2024-03-08",  # Mahashivratri
            "2024-03-25",  # Holi
            "2024-03-29",  # Good Friday
            "2024-04-11",  # Eid-Ul-Fitr
            "2024-04-17",  # Ram Navami
            "2024-05-01",  # Maharashtra Day
            "2024-06-17",  # Bakri Eid
            "2024-08-15",  # Independence Day
            "2024-09-02",  # Ganesh Chaturthi
            "2024-10-02",  # Gandhi Jayanti
            "2024-11-01",  # Diwali Laxmi Pujan
            "2024-11-15",  # Gurunanak Jayanti
            "2024-12-25",  # Christmas
        ]
    
    def get_current_ist_time(self):
        """Get current time in IST"""
        return datetime.now(self.ist_tz)
    
    def is_market_holiday(self, date=None):
        """Check if given date is a market holiday"""
        if date is None:
            date = self.get_current_ist_time().date()
        return date.strftime("%Y-%m-%d") in self.holidays
    
    def is_weekend(self, date=None):
        """Check if given date is a weekend"""
        if date is None:
            date = self.get_current_ist_time().date()
        return date.weekday() >= 5  # Saturday = 5, Sunday = 6
    
    def is_market_open(self):
        """Check if market is currently open"""
        current_time = self.get_current_ist_time()
        
        # Check for weekends and holidays
        if self.is_weekend() or self.is_market_holiday():
            return False
        
        current_time_obj = current_time.time()
        return self.market_open_time <= current_time_obj < self.market_close_time
    
    def is_pre_market(self):
        """Check if currently in pre-market hours"""
        current_time = self.get_current_ist_time()
        
        if self.is_weekend() or self.is_market_holiday():
            return False
        
        current_time_obj = current_time.time()
        return self.pre_market_start <= current_time_obj < self.market_open_time
    
    def is_post_market(self):
        """Check if currently in post-market hours"""
        current_time = self.get_current_ist_time()
        
        if self.is_weekend() or self.is_market_holiday():
            return False
        
        current_time_obj = current_time.time()
        return self.market_close_time <= current_time_obj <= self.post_market_end
    
    def get_next_market_open(self):
        """Get next market opening time"""
        current_time = self.get_current_ist_time()
        next_day = current_time
        
        # If after market close, start checking from next day
        if current_time.time() >= self.market_close_time:
            next_day += timedelta(days=1)
        
        # Find next trading day
        while self.is_weekend(next_day.date()) or self.is_market_holiday(next_day.date()):
            next_day += timedelta(days=1)
        
        return datetime.combine(
            next_day.date(),
            self.market_open_time
        ).replace(tzinfo=self.ist_tz)
    
    def get_market_status(self):
        """Get detailed market status"""
        current_time = self.get_current_ist_time()
        
        if self.is_market_open():
            time_to_close = datetime.combine(
                current_time.date(),
                self.market_close_time
            ).replace(tzinfo=self.ist_tz) - current_time
            
            return {
                'status': 'OPEN',
                'message': f'Market is open. Closes in {time_to_close.seconds // 60} minutes',
                'next_event': 'close',
                'next_event_time': self.market_close_time.strftime('%H:%M')
            }
        
        elif self.is_pre_market():
            time_to_open = datetime.combine(
                current_time.date(),
                self.market_open_time
            ).replace(tzinfo=self.ist_tz) - current_time
            
            return {
                'status': 'PRE-MARKET',
                'message': f'Pre-market. Opens in {time_to_open.seconds // 60} minutes',
                'next_event': 'open',
                'next_event_time': self.market_open_time.strftime('%H:%M')
            }
        
        elif self.is_post_market():
            next_open = self.get_next_market_open()
            
            return {
                'status': 'POST-MARKET',
                'message': f'Post-market. Next open {next_open.strftime("%Y-%m-%d %H:%M")}',
                'next_event': 'end',
                'next_event_time': self.post_market_end.strftime('%H:%M')
            }
        
        else:
            next_open = self.get_next_market_open()
            
            if self.is_weekend():
                reason = "Weekend"
            elif self.is_market_holiday():
                reason = "Market Holiday"
            else:
                reason = "After Hours"
            
            return {
                'status': 'CLOSED',
                'message': f'Market closed ({reason}). Opens {next_open.strftime("%Y-%m-%d %H:%M")}',
                'next_event': 'open',
                'next_event_time': next_open.strftime('%Y-%m-%d %H:%M')
            } 