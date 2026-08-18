"""Redis resource semaphore.

One sorted set per resource: members are reservation tokens, scores are lease
deadlines. Checking capacity and taking a slot happen in one Lua script, because a
client-side check-then-add lets two workers pass the same capacity check and
over-admit.

Deadlines come from Redis's own clock (`TIME`), not from each caller's clock, so
workers with skewed clocks still agree on when a lease lapsed.
"""

from uuid import uuid4

from redis.asyncio import Redis

from agentic_qa.application.ports.semaphores import SlotReservation

_NOW_MS = """
local now = redis.call('TIME')
local now_ms = tonumber(now[1]) * 1000 + math.floor(tonumber(now[2]) / 1000)
"""

# KEYS[1] = resource key; ARGV = token, capacity, ttl_ms
_ACQUIRE = (
    _NOW_MS
    + """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now_ms)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then
    return 0
end
redis.call('ZADD', KEYS[1], now_ms + tonumber(ARGV[3]), ARGV[1])
redis.call('PEXPIRE', KEYS[1], tonumber(ARGV[3]) * 2)
return 1
"""
)

# KEYS[1] = resource key; ARGV = token, ttl_ms
_RENEW = (
    _NOW_MS
    + """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now_ms)
if redis.call('ZSCORE', KEYS[1], ARGV[1]) then
    redis.call('ZADD', KEYS[1], now_ms + tonumber(ARGV[2]), ARGV[1])
    redis.call('PEXPIRE', KEYS[1], tonumber(ARGV[2]) * 2)
    return 1
end
return 0
"""
)

# KEYS[1] = resource key; ARGV = token
_RELEASE = (
    _NOW_MS
    + """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now_ms)
return redis.call('ZREM', KEYS[1], ARGV[1])
"""
)

_IN_USE = (
    _NOW_MS
    + """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now_ms)
return redis.call('ZCARD', KEYS[1])
"""
)


class RedisResourceSemaphore:
    def __init__(self, client: Redis) -> None:
        self._acquire = client.register_script(_ACQUIRE)
        self._renew = client.register_script(_RENEW)
        self._release = client.register_script(_RELEASE)
        self._in_use = client.register_script(_IN_USE)

    async def acquire(
        self, resource: str, *, capacity: int, ttl_seconds: float
    ) -> SlotReservation | None:
        token = str(uuid4())
        taken = await self._acquire(keys=[resource], args=[token, capacity, _millis(ttl_seconds)])
        return SlotReservation(resource=resource, token=token) if taken else None

    async def renew(self, reservation: SlotReservation, *, ttl_seconds: float) -> bool:
        result = await self._renew(
            keys=[reservation.resource], args=[reservation.token, _millis(ttl_seconds)]
        )
        return bool(result)

    async def release(self, reservation: SlotReservation) -> bool:
        result = await self._release(keys=[reservation.resource], args=[reservation.token])
        return bool(result)

    async def in_use(self, resource: str) -> int:
        return int(await self._in_use(keys=[resource], args=[]))


def _millis(ttl_seconds: float) -> int:
    return max(1, int(ttl_seconds * 1000))
