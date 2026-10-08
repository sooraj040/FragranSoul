"""Online payments through Razorpay (UPI, net banking and cards).

The store never sees card numbers or bank details: the customer enters them
in Razorpay's own checkout window, and Razorpay tells us the result. Two
settings switch this on, both read from environment variables:

    RAZORPAY_KEY_ID      the public key, sent to the browser
    RAZORPAY_KEY_SECRET  the private key, used only on the server

Without them, online options are unavailable on the live site. On a
developer's machine (DEBUG on) a stand-in "test payment" page is used instead
so the flow can be tried without an account; no money moves there.
"""

import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.request

from django.conf import settings

ORDERS_URL = "https://api.razorpay.com/v1/orders"


class PaymentError(Exception):
    """The payment gateway could not be reached or refused the request."""


def gateway_ready():
    """True when Razorpay keys are configured."""
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def sandbox():
    """True when the stand-in test payment page should be used."""
    return settings.PAYMENTS_SANDBOX and not gateway_ready()


def online_available():
    """True when customers can choose to pay online."""
    return gateway_ready() or sandbox()


def call_gateway(url, payload=None):
    """Send one authenticated request to Razorpay and return the decoded reply."""
    credentials = f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode()
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Basic " + base64.b64encode(credentials).decode(),
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except (urllib.error.URLError, ValueError) as error:
        raise PaymentError(str(error)) from error


def create_gateway_order(order):
    """Register the amount with Razorpay and return its order id.

    Razorpay works in paise, so the total is multiplied by 100.
    """
    reply = call_gateway(
        ORDERS_URL,
        {
            "amount": int(order.total * 100),
            "currency": "INR",
            "receipt": order.order_number,
        },
    )
    try:
        return reply["id"]
    except (KeyError, TypeError) as error:
        raise PaymentError("Unexpected reply from the payment gateway.") from error


def captured_payment_id(gateway_order_id):
    """Ask Razorpay whether an order has been paid; return the payment id or None.

    The browser normally reports a payment itself, but a customer who pays in
    a UPI app and never comes back to the tab would otherwise stay unpaid.
    """
    reply = call_gateway(f"{ORDERS_URL}/{gateway_order_id}/payments")
    try:
        for payment in reply["items"]:
            if payment["status"] == "captured":
                return payment["id"]
    except (KeyError, TypeError) as error:
        raise PaymentError("Unexpected reply from the payment gateway.") from error
    return None


def signature_is_valid(gateway_order_id, payment_id, signature):
    """Check that a payment confirmation really came from Razorpay.

    Razorpay signs "<order id>|<payment id>" with the secret key. Without this
    check anyone could mark their own order as paid.
    """
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{gateway_order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")
