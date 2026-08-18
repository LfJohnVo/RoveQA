"""Redis lock manager with TTL and ownership tokens.

Release and renew compare the token *inside* Redis (Lua, so the check and the write
are atomic). A GET-then-DEL from the client could delete a lock that expired and was
re-acquired by someone else in between, which is exactly the bug that turns a
mutual-exclusion guarantee into a silent race.
"""

from uuid import uuid4

from redis.asyncio import Redis

from agentic_qa.application.ports.locks import LockHandle

# KEYS[1] = lock key, ARGV[1] = token, ARGV[2] = new ttl in milliseconds
_RENEW_IF_OWNER = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('pexpire', KEYS[1], ARGV[2])
else
    return 0
end
"""

_RELEASE_IF_OWNER = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""


class RedisLockManager:
    def __init__(self, client: Redis) -> None:
        self._client = client
        self._renew = client.register_script(_RENEW_IF_OWNER)
        self._release = client.register_script(_RELEASE_IF_OWNER)

    async def acquire(self, key: str, *, ttl_seconds: float) -> LockHandle | None:
        token = str(uuid4())
        acquired = await self._client.set(key, token, nx=True, px=_millis(ttl_seconds))
        return LockHandle(key=key, token=token) if acquired else None

    async def renew(self, handle: LockHandle, *, ttl_seconds: float) -> bool:
        result = await self._renew(keys=[handle.key], args=[handle.token, _millis(ttl_seconds)])
        return bool(result)

    async def release(self, handle: LockHandle) -> bool:
        result = await self._release(keys=[handle.key], args=[handle.token])
        return bool(result)


def _millis(ttl_seconds: float) -> int:
    return max(1, int(ttl_seconds * 1000))
