from flask import Flask, request, jsonify
from twilio.rest import Client

# Initialize Flask app
app = Flask(__name__)

# Twilio credentials (replace with your actual credentials)
TWILIO_ACCOUNT_SID = 'AC62c9795393449f1e2b2154b7a42aafc9'
TWILIO_AUTH_TOKEN = 'da2a85e1dcbf0f3fc8c1d9b05ce36da6'
TWILIO_FROM_NUMBER = '+18129944315'

# Default recipients (always get SMS)
DEFAULT_RECIPIENTS = ["+21625279771"]

@app.route('/send_sms', methods=['POST'])
def send_sms():
    try:
        data = request.json
        message_body = data.get('message')
        
        # Always send to default recipients
        to_numbers = DEFAULT_RECIPIENTS
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        results = []
        
        for to_number in to_numbers:
            message = client.messages.create(
                body=message_body,
                from_=TWILIO_FROM_NUMBER,
                to=to_number
            )
            results.append({"to": to_number, "sid": message.sid})
        
        return jsonify({"status": "sent", "messages": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500