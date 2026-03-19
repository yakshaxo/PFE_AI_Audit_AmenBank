from twilio.rest import Client

account_sid = "AC62c9795393449f1e2b2154b7a42aafc9"
auth_token = "da2a85e1dcbf0f3fc8c1d9b05ce36da6"

client = Client(account_sid, auth_token)

try:
    message = client.messages.create(
        body="message from lou",
        from_="+18129944315",
        to="+21625279771"
    )
    print(f"SUCCESS! Message SID: {message.sid}")
except Exception as e:
    print(f"ERROR: {e}")