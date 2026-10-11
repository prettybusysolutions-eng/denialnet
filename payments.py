"""Atomic, account-bound credit settlement shared by all delivery paths."""
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from models import AgentBalance, Transaction, TopupIntent, PaymentReceipt


def settle_intent(session, intent, expected_agent=None):
    payment_id = intent.get('id')
    binding = session.get(TopupIntent, payment_id)
    if binding is None:
        raise HTTPException(409, 'Payment has no server-created topup binding')
    agent = binding.agent_id
    amount = binding.amount_cents
    metadata = intent.get('metadata') or {}
    if expected_agent is not None and agent != expected_agent:
        raise HTTPException(403, 'Payment belongs to another account')
    if (intent.get('status') != 'succeeded' or intent.get('currency') != 'usd'
            or intent.get('amount_received') != amount
            or intent.get('amount') != amount
            or metadata.get('agent_id') != agent
            or metadata.get('type') != 'denialnet_topup'):
        raise HTTPException(400, 'Payment status, amount, currency, or binding mismatch')
    existing = session.get(PaymentReceipt, payment_id)
    if existing:
        if existing.agent_id != agent or existing.amount_cents != amount:
            raise HTTPException(409, 'Receipt binding mismatch')
        return {'ok': True, 'credited': False, 'payment_intent_id': payment_id}
    try:
        session.add(PaymentReceipt(payment_intent_id=payment_id, agent_id=agent, amount_cents=amount))
        session.flush()  # Unique payment ID arbitrates concurrent deliveries.
        credited = session.execute(update(AgentBalance).where(
            AgentBalance.agent_id == agent
        ).values(balance_cents=AgentBalance.balance_cents + amount))
        if credited.rowcount != 1:
            raise HTTPException(409, 'Topup account is missing')
        session.add(Transaction(agent_id=agent, tx_type='credit_topup',
                                amount_cents=amount, description=f'Stripe PaymentIntent: {payment_id}'))
        session.commit()
    except IntegrityError:
        session.rollback()
        receipt = session.get(PaymentReceipt, payment_id)
        if receipt and receipt.agent_id == agent and receipt.amount_cents == amount:
            return {'ok': True, 'credited': False, 'payment_intent_id': payment_id}
        raise
    except Exception:
        session.rollback()
        raise
    return {'ok': True, 'credited': True, 'payment_intent_id': payment_id, 'amount_cents': amount}
