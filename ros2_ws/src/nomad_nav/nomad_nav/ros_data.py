import rclpy
from rclpy.time import Time
from rclpy.clock import Clock

class ROSData:
    def __init__(self, timeout: int = 3, queue_size: int = 1, name: str = ""):
        self.clock = Clock()
        self.timeout = timeout
        self.last_time_received = self.clock.now()
        self.queue_size = queue_size
        self.data = [] if queue_size > 1 else None
        self.name = name
        self.phantom = False

    def get(self):
        return self.data

    def set(self, data):
        now = self.clock.now()
        time_waited = (now - self.last_time_received).nanoseconds / 1e9

        if self.queue_size == 1:
            self.data = data
        else:
            if self.data is None or time_waited > self.timeout:  # reset queue if timeout
                self.data = []
            if len(self.data) == self.queue_size:
                self.data.pop(0)
            self.data.append(data)
        self.last_time_received = now

    def is_valid(self, verbose: bool = False):
        now = self.clock.now()
        time_waited = (now - self.last_time_received).nanoseconds / 1e9
        valid = time_waited < self.timeout
        
        if self.queue_size > 1:
            valid = valid and len(self.data) == self.queue_size
        
        if verbose and not valid:
            print(f"Not receiving {self.name} data for {time_waited:.2f} seconds (timeout: {self.timeout} seconds)")
        
        return valid