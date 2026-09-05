"""
Day 4 (optional stretch): Send the optimization recommendation via SMS
using Twilio's sandbox. Docs: https://www.twilio.com/docs/sms/quickstart/python

NOT TESTED in this sandbox -- api.twilio.com isn't reachable from here,
and it needs real account credentials anyway. Get a free Twilio trial
account, verify your own phone number as a recipient (trial accounts can
only text pre-verified numbers), and set the three env vars below before
testing this locally.

Install: pip install twilio
"""
import os

# Set these as real environment variables -- never hardcode credentials.
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")  # e.g. "+15005550006" (Twilio sandbox number)


def send_recommendation_sms(to_number: str, summary: str) -> dict:
    """Sends `summary` (e.g. OptimizeResponse.recommendation_summary) via
    SMS. Raises RuntimeError if Twilio env vars aren't configured, and
    lets any twilio.base.exceptions.TwilioRestException bubble up to the
    caller (main.py) to convert into an HTTP error.
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER]):
        raise RuntimeError(
            "Twilio is not configured -- set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
            "and TWILIO_FROM_NUMBER environment variables (see this file's docstring)."
        )

    from twilio.rest import Client  # imported lazily so the app still boots without twilio installed

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=f"UpajMitra recommendation: {summary}",
        from_=TWILIO_FROM_NUMBER,
        to=to_number,
    )
    return {"sid": message.sid, "status": message.status}


# --- To wire this into main.py, add: ------------------------------------
#
# from . import notify as notify_module
#
# class NotifyRequest(BaseModel):        # add to schemas.py
#     phone_number: str
#     summary: str
#
# @app.post("/api/notify")
# def notify(req: NotifyRequest):
#     try:
#         return notify_module.send_recommendation_sms(req.phone_number, req.summary)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
#
# Then on the frontend, add a "Send via SMS" button in OptimizePanel.jsx
# that POSTs { phone_number, summary: result.recommendation_summary }
# to /api/notify.
