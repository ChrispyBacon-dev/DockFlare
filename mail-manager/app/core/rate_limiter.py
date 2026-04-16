import time
import threading

class OutboundRateLimiter:
    def __init__(self, hourly_limit=50, daily_limit=200):
        self.hourly_limit = hourly_limit
        self.daily_limit = daily_limit
        self.history = {}
        self.lock = threading.Lock()

    def check_rate(self, from_address):
        with self.lock:
            now = time.time()
            if from_address not in self.history:
                self.history[from_address] = []
            
            self.history[from_address] = [t for t in self.history[from_address] if now - t < 86400]
            
            recent_hour = [t for t in self.history[from_address] if now - t < 3600]
            
            if len(self.history[from_address]) >= self.daily_limit:
                return False, "Daily limit reached"
            if len(recent_hour) >= self.hourly_limit:
                return False, "Hourly limit reached"
                
            return True, ""

    def record_send(self, from_address):
        with self.lock:
            if from_address not in self.history:
                self.history[from_address] = []
            self.history[from_address].append(time.time())

limiter = OutboundRateLimiter()
