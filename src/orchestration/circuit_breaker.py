"""Circuit Breaker pattern implementation for fault tolerance.

This module provides a circuit breaker that prevents cascading failures
by temporarily blocking requests to failing services.
"""

import asyncio
import time
from enum import Enum
from typing import Optional, Callable, Any, Dict
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"      # Service failure detected, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 3  # Failures before opening circuit
    success_threshold: int = 2  # Successes in half-open before closing
    timeout: float = 60.0  # Seconds before attempting reset
    expected_exception: type = Exception  # Exception types to catch
    exclude_exceptions: tuple = ()  # Exceptions that don't count as failures


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    state_changes: list = field(default_factory=list)


class CircuitBreaker:
    """Circuit breaker implementation with configurable behavior."""
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Callable[[str, CircuitState, CircuitState], None]] = None
    ):
        """Initialize circuit breaker.
        
        Args:
            name: Identifier for this circuit breaker
            config: Configuration parameters
            on_state_change: Callback for state changes
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.on_state_change = on_state_change
        
        self._state = CircuitState.CLOSED
        self._last_failure_time: Optional[float] = None
        self._stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
        
    @property
    def stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        return self._stats
        
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED
        
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self._state == CircuitState.OPEN
        
    async def _change_state(self, new_state: CircuitState) -> None:
        """Change circuit state and notify observers."""
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            self._stats.state_changes.append({
                "from": old_state.value,
                "to": new_state.value,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Circuit breaker '{self.name}' state changed: {old_state.value} -> {new_state.value}")
            
            if self.on_state_change:
                try:
                    self.on_state_change(self.name, old_state, new_state)
                except Exception as e:
                    logger.error(f"Error in state change callback: {e}")
                    
    async def _record_success(self) -> None:
        """Record successful call."""
        async with self._lock:
            self._stats.total_calls += 1
            self._stats.successful_calls += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            
            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self.config.success_threshold:
                    await self._change_state(CircuitState.CLOSED)
                    
    async def _record_failure(self) -> None:
        """Record failed call."""
        async with self._lock:
            self._stats.total_calls += 1
            self._stats.failed_calls += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = datetime.utcnow()
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.CLOSED:
                if self._stats.consecutive_failures >= self.config.failure_threshold:
                    await self._change_state(CircuitState.OPEN)
            elif self._state == CircuitState.HALF_OPEN:
                await self._change_state(CircuitState.OPEN)
                
    async def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self._state == CircuitState.OPEN and
            self._last_failure_time is not None and
            time.time() - self._last_failure_time >= self.config.timeout
        )
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func execution
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If func raises an exception
        """
        async with self._lock:
            # Check if we should attempt reset
            if await self._should_attempt_reset():
                await self._change_state(CircuitState.HALF_OPEN)
                self._stats.consecutive_failures = 0
                self._stats.consecutive_successes = 0
                
            # Reject call if circuit is open
            if self._state == CircuitState.OPEN:
                self._stats.rejected_calls += 1
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is open. Service unavailable."
                )
                
        # Execute the function
        try:
            # Handle both sync and async functions
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
                
            await self._record_success()
            return result
            
        except self.config.exclude_exceptions:
            # Don't count excluded exceptions as failures
            raise
            
        except self.config.expected_exception as e:
            await self._record_failure()
            raise
            
    def __call__(self, func: Callable) -> Callable:
        """Decorator for wrapping functions with circuit breaker."""
        async def async_wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
            
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.call(func, *args, **kwargs))
            
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics for monitoring."""
        return {
            "name": self.name,
            "state": self._state.value,
            "total_calls": self._stats.total_calls,
            "successful_calls": self._stats.successful_calls,
            "failed_calls": self._stats.failed_calls,
            "rejected_calls": self._stats.rejected_calls,
            "success_rate": (
                self._stats.successful_calls / self._stats.total_calls
                if self._stats.total_calls > 0 else 0.0
            ),
            "consecutive_failures": self._stats.consecutive_failures,
            "consecutive_successes": self._stats.consecutive_successes,
            "last_failure_time": (
                self._stats.last_failure_time.isoformat()
                if self._stats.last_failure_time else None
            )
        }


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
        
    async def register(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Callable] = None
    ) -> CircuitBreaker:
        """Register a new circuit breaker."""
        async with self._lock:
            if name in self._breakers:
                return self._breakers[name]
                
            breaker = CircuitBreaker(name, config, on_state_change)
            self._breakers[name] = breaker
            return breaker
            
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)
        
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers."""
        return {
            name: breaker.get_metrics()
            for name, breaker in self._breakers.items()
        }