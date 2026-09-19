import copy
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import sessionmaker

import routes
from config import Settings, settings
from models import Base, APIKey, AgentBalance, Pattern, TopupIntent, PaymentReceipt, Transaction
from payments import settle_intent


@pytest.fixture
def system(tmp_path, monkeypatch):
    postgres = os.environ.get('RELEASE_TEST_POSTGRES_URL')
    admin = None
    if postgres:
        schema = 'release_' + uuid.uuid4().hex
        admin = create_engine(postgres, isolation_level='AUTOCOMMIT')
        with admin.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA {schema}'))
        engine = create_engine(postgres, connect_args={'options': f'-csearch_path={schema}'})
    else:
        engine = create_engine(f'sqlite:///{tmp_path}/test.db', connect_args={'check_same_thread': False, 'timeout': 30})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as s:
        for name in ['alice', 'bob']:
            s.add(APIKey(key_hash=routes._hash_api_key(name), name=name, agent_id=name))
            s.add(AgentBalance(agent_id=name, balance_cents=500))
        s.add(APIKey(key_hash=routes._hash_api_key('unbound'), name='legacy'))
        for i in range(2):
            s.add(Pattern(carrier='Test', cpt_code='D1', specialty='Dental', denial_reason='Synthetic',
                          resolution_steps=['private resolution'], contributor_id='bob'))
        s.add(TopupIntent(payment_intent_id='pi_test', agent_id='alice', amount_cents=500))
        s.commit()
        ids = [str(p.id) for p in s.query(Pattern).all()]
    def db():
        with factory() as s:
            yield s
    routes.app.dependency_overrides[routes.db] = db
    monkeypatch.setattr(settings, 'STRIPE_SECRET_KEY', None)
    monkeypatch.setattr(settings, 'ALLOW_MOCK_PAYMENTS', False)
    monkeypatch.setattr(settings, 'ENV', 'development')
    client = TestClient(routes.app)
    yield client, factory, ids
    routes.app.dependency_overrides.clear()
    engine.dispose()
    if admin is not None:
        with admin.connect() as conn:
            conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin.dispose()


def headers(name='alice'):
    return {'X-API-Key': name}


def test_readiness_rejects_missing_payment_schema(system):
    client, factory, _ = system
    assert client.get('/ready').status_code == 200
    with factory() as session:
        session.execute(text('DROP TABLE payment_receipts'))
        session.commit()
    response = client.get('/ready')
    assert response.status_code == 503
    assert 'unavailable_or_incompatible_schema' in response.text


def test_staging_requires_test_credentials_and_real_database():
    values = dict(ENV='staging', DATABASE_URL='postgresql://localhost/release_test',
                  STRIPE_SECRET_KEY='sk_test_fixture', STRIPE_WEBHOOK_SECRET='whsec_fixture',
                  ADMIN_API_KEY='local-fixture', ALLOW_MOCK_PAYMENTS=False)
    assert Settings(**values).ENV == 'staging'
    for change in ({'STRIPE_SECRET_KEY': 'sk_live_fixture'}, {'ALLOW_MOCK_PAYMENTS': True},
                   {'DATABASE_URL': 'sqlite:///test.db'}):
        with pytest.raises(ValueError):
            Settings(**(values | change))


def test_failed_contributor_credit_rolls_back_entire_purchase(system, monkeypatch):
    _, factory, _ = system
    from models import PatternEntitlement
    with factory() as s:
        s.query(AgentBalance).filter_by(agent_id='bob').delete()
        s.commit()
    with factory() as s:
        original = s.execute
        def execute(statement, *args, **kwargs):
            if getattr(statement, 'is_update', False) and 'balance_cents +' in str(statement):
                raise RuntimeError('simulated contributor credit failure')
            return original(statement, *args, **kwargs)
        monkeypatch.setattr(s, 'execute', execute)
        with pytest.raises(RuntimeError, match='contributor credit failure'):
            routes.search_patterns(routes.PatternSearchQuery(carrier='Test', cpt_code='D1', agent_id='alice'), s, 'alice')
        s.rollback()
    with factory() as s:
        assert s.get(AgentBalance, 'alice').balance_cents == 500
        assert s.query(PatternEntitlement).count() == 0
        assert s.query(Transaction).count() == 0


def test_low_quality_patterns_are_not_sold(system):
    client, factory, _ = system
    with factory() as s:
        for pattern in s.query(Pattern).all():
            pattern.sample_size = 1
            pattern.success_rate = 0.1
        s.commit()
    response = client.post('/patterns/search', headers=headers(), json={
        'carrier': 'Test', 'cpt_code': 'D1', 'agent_id': 'alice'})
    assert response.status_code == 200
    assert response.json()['patterns'] == []
    assert response.json()['cost_cents'] == 0


def intent():
    return {'id': 'pi_test', 'status': 'succeeded', 'currency': 'usd', 'amount': 500,
            'amount_received': 500, 'metadata': {'agent_id': 'alice', 'type': 'denialnet_topup'}}


def test_pattern_access_and_all_search_entitlements(system):
    client, factory, ids = system
    for pid in ids:
        assert client.get(f'/patterns/{pid}').status_code == 401
        assert client.get(f'/patterns/{pid}', headers=headers()).status_code == 403
    preview = client.get('/patterns/preview', params={'carrier': 'Test', 'cpt_code': 'D1'})
    assert 'private resolution' not in preview.text
    result = client.post('/patterns/search', headers=headers(), json={'carrier': 'Test', 'cpt_code': 'D1', 'agent_id': 'alice'})
    assert result.status_code == 200, result.text
    for pid in ids:
        assert client.get(f'/patterns/{pid}', headers=headers()).status_code == 200
    assert client.get('/credits/alice', headers=headers()).json()['balance_cents'] == 425


@pytest.mark.parametrize('path', ['/credits/bob', '/credits/bob/transactions'])
def test_account_reads_are_scoped(system, path):
    client, _, _ = system
    assert client.get(path).status_code == 401
    assert client.get(path, headers=headers()).status_code == 403
    assert client.get(path, headers=headers('bob')).status_code == 200
    assert client.get(path, headers=headers('unbound')).status_code == 403


def test_identity_substitution_rejected(system):
    client, _, ids = system
    assert client.post('/patterns/search', headers=headers(), json={'carrier': 'Test', 'cpt_code': 'D1', 'agent_id': 'bob'}).status_code == 403
    assert client.post(f'/patterns/{ids[0]}/outcome', headers=headers(), json={'outcome': 'approved', 'submitted_by': 'bob'}).status_code == 403
    assert client.post('/patterns', headers=headers(), json={'carrier': 'Test', 'cpt_code': 'D1', 'specialty': 'Dental', 'denial_reason': 'test', 'resolution_steps': ['x'], 'contributor_id': 'bob'}).status_code == 403
    assert client.post('/patterns/ingest', headers=headers(), json={'contributor_id': 'bob', 'patterns_csv': 'carrier,cpt_code\nTest,D1'}).status_code == 403


def test_missing_stripe_never_credits(system):
    client, _, _ = system
    payload = {'agent_id': 'alice', 'amount_cents': 500, 'stripe_customer_id': 'unused', 'stripe_payment_method_id': 'unused'}
    assert client.post('/credits/topup', headers=headers(), json=payload).status_code == 503
    assert client.post('/credits/topup/confirm', headers=headers(), json={'agent_id': 'alice', 'payment_intent_id': 'pi_test'}).status_code == 503
    assert client.get('/credits/alice', headers=headers()).json()['balance_cents'] == 500


def test_confirm_and_webhook_credit_only_once(system, monkeypatch):
    client, factory, _ = system
    import stripe
    monkeypatch.setattr(settings, 'STRIPE_SECRET_KEY', 'sk_test_fixture')
    monkeypatch.setattr(settings, 'STRIPE_WEBHOOK_SECRET', 'whsec_fixture')
    monkeypatch.setattr(stripe.PaymentIntent, 'retrieve', lambda *a, **k: intent())
    monkeypatch.setattr(stripe.Webhook, 'construct_event', lambda *a, **k: {'id': 'evt_test', 'type': 'payment_intent.succeeded', 'data': {'object': intent()}})
    assert client.post('/credits/topup/confirm', headers=headers(), json={'agent_id': 'bob', 'payment_intent_id': 'pi_test'}).status_code == 403
    for _ in range(2):
        assert client.post('/credits/topup/confirm', headers=headers(), json={'agent_id': 'alice', 'payment_intent_id': 'pi_test'}).status_code == 200
        assert client.post('/webhooks/stripe', content=b'fixture').status_code == 200
    assert client.get('/credits/alice', headers=headers()).json()['balance_cents'] == 1000
    with factory() as s:
        assert s.query(PaymentReceipt).count() == 1
        assert s.query(Transaction).filter_by(tx_type='credit_topup').count() == 1


def test_parallel_deliveries_and_restart(system):
    _, factory, _ = system
    def deliver(_):
        with factory() as s:
            return settle_intent(s, intent())
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(deliver, range(8)))
    assert sum(r['credited'] for r in results) == 1
    with factory() as s:
        assert settle_intent(s, intent())['credited'] is False
        assert s.get(AgentBalance, 'alice').balance_cents == 1000


@pytest.mark.parametrize('change', [{'status': 'processing'}, {'currency': 'eur'}, {'amount_received': 499}, {'amount': 600}, {'metadata': {'agent_id': 'bob', 'type': 'denialnet_topup'}}, {'id': 'pi_unknown'}])
def test_unverified_payment_cannot_credit(system, change):
    _, factory, _ = system
    value = intent(); value.update(change)
    with factory() as s:
        with pytest.raises(HTTPException):
            settle_intent(s, value)
        s.rollback()
        assert s.get(AgentBalance, 'alice').balance_cents == 500
        assert s.query(PaymentReceipt).count() == 0


def test_failed_credit_rolls_back_consumption(system):
    _, factory, _ = system
    with factory() as s:
        s.delete(s.get(AgentBalance, 'alice')); s.commit()
        with pytest.raises(HTTPException):
            settle_intent(s, intent())
        assert s.query(PaymentReceipt).count() == 0
        s.add(AgentBalance(agent_id='alice', balance_cents=0)); s.commit()
        assert settle_intent(s, intent())['credited'] is True


def test_bad_webhook_signature_cannot_credit(system, monkeypatch):
    client, factory, _ = system
    monkeypatch.setattr(settings, 'STRIPE_SECRET_KEY', 'sk_test_fixture')
    monkeypatch.setattr(settings, 'STRIPE_WEBHOOK_SECRET', 'whsec_fixture')
    assert client.post('/webhooks/stripe', content=b'{}', headers={'stripe-signature': 'invalid'}).status_code == 400
    with factory() as s:
        assert s.query(PaymentReceipt).count() == 0


def test_production_fails_closed():
    with pytest.raises(ValueError):
        Settings(ENV='production', _env_file=None)
    with pytest.raises(ValueError):
        Settings(ENV='production', ALLOW_MOCK_PAYMENTS=True, _env_file=None)
    with pytest.raises(ValueError):
        Settings(ENV='development', ALLOW_MOCK_PAYMENTS=True, _env_file=None)
    assert Settings(ENV='test', ALLOW_MOCK_PAYMENTS=True, _env_file=None).ALLOW_MOCK_PAYMENTS
