import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Zenoti API Config
ZENOTI_API_KEY = os.getenv("ZENOTI_API_KEY")
ZENOTI_ORG_ID = os.getenv("ZENOTI_ORG_ID")
ZENOTI_CENTER_ID = os.getenv("ZENOTI_CENTER_ID")

@app.route("/openphone/incoming", methods=["POST"])
def handle_reply():
    data = request.json
    print("📥 Incoming SMS:", data)

    reply = data.get("text", "").strip().lower()
    from_number = data.get("from", {}).get("phone_number", "")

    if reply != "y":
        print("🔕 Ignored (Not 'Y')")
        return jsonify({"message": "Ignored"}), 200

    # Find appointment
    appt = find_latest_unconfirmed_appt(from_number)
    if not appt:
        print("❌ No matching unconfirmed appointment")
        return jsonify({"message": "No unconfirmed appointment found"}), 404

    # Confirm appointment
    success = confirm_appt(appt["id"])
    if success:
        print(f"✅ Appointment {appt['id']} confirmed.")
        return jsonify({"message": "Appointment confirmed"}), 200
    else:
        print(f"❌ Failed to confirm appointment {appt['id']}.")
        return jsonify({"message": "Failed to confirm appointment"}), 500

def find_latest_unconfirmed_appt(phone):
    headers = {
        "Authorization": f"apikey {ZENOTI_API_KEY}",
        "org": ZENOTI_ORG_ID
    }
    url = f"https://api.zenoti.com/v1/appointments?center_id={ZENOTI_CENTER_ID}"

    try:
        response = requests.get(url, headers=headers)
        appointments = response.json()
    except Exception as e:
        print("❌ Error fetching appointments:", e)
        return None

    for appt in appointments:
        guest = appt.get("guest", {})
        guest_phone = guest.get("mobile") or guest.get("phone_number")
        if not guest_phone:
            continue

        if phone[-10:] in guest_phone[-10:] and appt.get("status") == 0:
            return {"id": appt["id"], "guest_name": guest.get("first_name")}

    return None

def confirm_appt(appt_id):
    url = f"https://api.zenoti.com/v1/appointments/{appt_id}"
    headers = {
        "Authorization": f"apikey {ZENOTI_API_KEY}",
        "org": ZENOTI_ORG_ID,
        "Content-Type": "application/json"
    }
    payload = {"status": 1}  # 1 = Confirmed

    try:
        res = requests.put(url, headers=headers, json=payload)
        return res.status_code in (200, 204)
    except Exception as e:
        print("❌ Error confirming appointment:", e)
        return False

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)