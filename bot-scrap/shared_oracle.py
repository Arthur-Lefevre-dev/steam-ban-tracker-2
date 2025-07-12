#!/usr/bin/env python3
"""
Shared Oracle instance - Singleton pattern
"""
import threading
from oracle import Oracle

class SharedOracle:
    """Singleton Oracle instance shared across all bots"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._oracle = Oracle()
                    cls._instance._initialized = False
        return cls._instance
    
    def start(self):
        """Start the shared Oracle"""
        if not self._initialized:
            success = self._oracle.start()
            if success:
                self._initialized = True
            return success
        return True
    
    def stop(self):
        """Stop the shared Oracle"""
        if self._initialized:
            self._oracle.stop()
            self._initialized = False
    
    def __getattr__(self, name):
        """Delegate all other method calls to the Oracle instance"""
        return getattr(self._oracle, name)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

# Global shared oracle instance
shared_oracle = SharedOracle() 