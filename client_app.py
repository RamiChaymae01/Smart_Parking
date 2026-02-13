import json
import time
import paho.mqtt.client as mqtt
from web3 import Web3

# ======================================================
# MQTT CONFIG
# ======================================================
BROKER = "localhost"
PORT = 1883

FREE_TOPIC = "city/parking/free"
RESERVE_TOPIC = "city/parking/reserved"

# ======================================================
# IOTA EVM CONFIG
# ======================================================
RPC_URL = "https://json-rpc.evm.testnet.iota.cafe"
CHAIN_ID = 1076


CLIENT_PRIVATE_KEY = ""
CLIENT_ADDRESS = ""

PARKING_ADDRESS = ""

w3 = Web3(Web3.HTTPProvider(RPC_URL))
assert w3.is_connected()

# ======================================================
# GLOBAL
# ======================================================
current_free_slots = []
fake_reservation_id = 1   # temporaire

# ======================================================
# RESERVE
# ======================================================
def reserve_slot(slot_id):
    global fake_reservation_id

    print(f"\n Réservation de {slot_id}")

    nonce = w3.eth.get_transaction_count(CLIENT_ADDRESS)

    tx = {
        "nonce": nonce,
        "to": PARKING_ADDRESS,
        "value": w3.to_wei(0.1, "ether"),
        "gas": 100000,
        "gasPrice": w3.eth.gas_price,
        "chainId": CHAIN_ID,
        "data": w3.to_bytes(text=slot_id)
    }

    signed_tx = w3.eth.account.sign_transaction(tx, CLIENT_PRIVATE_KEY)
    w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    # --------------------------------------------------
    # SIMULATED BLOCKCHAIN DATA
    # --------------------------------------------------
    reservation_id = fake_reservation_id
    fake_reservation_id += 1

    deadline = int(time.time()) + 0.1 * 60

    mqtt_client.publish(
        RESERVE_TOPIC,
        json.dumps({
            "slot": slot_id,
            "reservationId": reservation_id,
            "deadline": deadline
        })
    )

    print(f" MQTT envoyé : {slot_id} | id={reservation_id}")

# ======================================================
# MQTT CALLBACK
# ======================================================
def on_message(client, userdata, msg):
    global current_free_slots

    data = json.loads(msg.payload.decode())
    current_free_slots = data["free_slots"]

    print("\n PARKING DISPONIBLE")
    for p in current_free_slots:
        print("", p)

# ======================================================
# MQTT
# ======================================================
mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT)
mqtt_client.subscribe(FREE_TOPIC)
mqtt_client.loop_start()

print("📡 Client connecté\n")

while True:
    slot = input("Réserver (ex P5) ou q : ")

    if slot == "q":
        break

    if slot not in current_free_slots:
        print(" Place non libre")
        continue

    reserve_slot(slot)

mqtt_client.loop_stop()
mqtt_client.disconnect()

