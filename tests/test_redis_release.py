import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import redis
from fastapi import HTTPException
import routes


def test_shared_limit_is_atomic_across_clients(monkeypatch):
    url = os.environ.get('RELEASE_TEST_REDIS_URL')
    if not url:
        pytest.skip('RELEASE_TEST_REDIS_URL required')
    clients = [redis.from_url(url) for _ in range(4)]
    agent = 'test_' + uuid.uuid4().hex
    def hit(index):
        # Independent Redis clients represent separate application workers.
        import threading
        worker.client = clients[index % len(clients)]
        try:
            routes.check_rate_limit(None, agent, 'search', 5, 1)
            return 200
        except HTTPException as exc:
            return exc.status_code
    import threading
    worker = threading.local()
    monkeypatch.setattr(routes, '_get_redis_client', lambda: worker.client)
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(hit, range(20)))
        assert results.count(200) == 5
        assert results.count(429) == 15
        keys = list(clients[0].scan_iter(f'denialnet:rl:{agent}:*'))
        assert keys and all(clients[0].ttl(key) > 0 for key in keys)
    finally:
        for key in clients[0].scan_iter(f'denialnet:rl:{agent}:*'):
            clients[0].delete(key)
        for client in clients:
            client.close()


def test_redis_outage_does_not_allow_requests(monkeypatch):
    class Unavailable:
        def eval(self, *args):
            raise redis.ConnectionError('fixture outage')
    monkeypatch.setattr(routes, '_get_redis_client', lambda: Unavailable())
    with pytest.raises(HTTPException) as error:
        routes.check_rate_limit(None, 'fixture', 'search', 5, 1)
    assert error.value.status_code == 503
