"""Timer manager for controlling multiple timers in the flash sintering system.
"""
import time
import threading

class TimerManager:
    """Manages multiple timers for different system functions.
    """
    def __init__(self):
        """Initialize timer manager."""
        self.timers = {}
        self.running = False
        self.threads = {}
        self.callbacks = {}

    def add_timer(self, name, period, callback):
        """Add a new timer.
        Args:
            name (str): Timer name
            period (float): Timer period in seconds
            callback (callable): Function to call on timer tick
        """
        self.timers[name] = period
        self.callbacks[name] = callback
        self.threads[name] = None

    def start_timer(self, name):
        """Start a specific timer.
        Args:
            name (str): Timer name to start
        """
        if name not in self.timers:
            raise ValueError(f"Timer {name} not found")

        if self.threads[name] is None or not self.threads[name].is_alive():
            self.threads[name] = threading.Thread(
                target=self._timer_loop,
                args=(name,),
                daemon=True
            )
            self.threads[name].start()

    def stop_timer(self, name):
        """Stop a specific timer.
        Args:
            name (str): Timer name to stop
        """
        if name in self.threads and self.threads[name] is not None:
            self.running = False
            self.threads[name].join()
            self.threads[name] = None

    def start_all(self):
        """Start all timers."""
        self.running = True
        for name in self.timers:
            self.start_timer(name)

    def stop_all(self):
        """Stop all timers."""
        self.running = False
        for name in self.threads:
            if self.threads[name] is not None:
                self.threads[name].join()
                self.threads[name] = None

    def _timer_loop(self, name):
        """Timer loop function.
        Args:
            name (str): Timer name
        """
        while self.running:
            start_time = time.time()
            
            # Execute callback
            try:
                self.callbacks[name]()
            except Exception as e:
                print(f"Error in timer {name} callback: {e}")

            # Calculate sleep time
            elapsed = time.time() - start_time
            sleep_time = max(0, self.timers[name] - elapsed)
            
            # Sleep until next tick
            if sleep_time > 0:
                time.sleep(sleep_time)

    def update_period(self, name, new_period):
        """Update timer period.
        Args:
            name (str): Timer name
            new_period (float): New period in seconds
        """
        if name in self.timers:
            self.timers[name] = new_period 