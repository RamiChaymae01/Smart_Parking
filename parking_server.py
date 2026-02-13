import cv2
import json
import time
import numpy as np
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from web3 import Web3

from config import AppConfig


# -------------------------
# Reservations (mémoire locale)
# -------------------------
reservations = {}


# -------------------------
# Helpers
# -------------------------
def load_rois(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def slot_name_to_index(slot_name: str) -> int:
    # "P5" -> 4
    return int(slot_name[1:]) - 1


def detect_car_centers(model: YOLO, frame, conf: float):
    results = model(frame, conf=conf, verbose=False)
    centers = []
    for r in results:
        if r.boxes is None:
            continue
        # xyxy shape: (N, 4)
        for box in r.boxes.xyxy.cpu().numpy():
            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)
            centers.append((cx, cy))
    return centers


def compute_occupied_slots(parking_rois, car_centers):
    occupied = set()
    for i, slot in enumerate(parking_rois):
        roi = np.array(slot["points"], dtype=np.int32)
        for (cx, cy) in car_centers:
            if cv2.pointPolygonTest(roi, (cx, cy), False) >= 0:
                occupied.add(i)
                break
    return occupied


def build_writer(output_path: str, fps: float, w: int, h: int):
    return cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (w, h),
    )


def init_web3(cfg: AppConfig):
    w3 = Web3(Web3.HTTPProvider(cfg.RPC_URL))
    assert w3.is_connected(), "IOTA EVM non connecté"
    contract = w3.eth.contract(address=cfg.SMART_CONTRACT_ADDRESS, abi=cfg.SMART_CONTRACT_ABI)
    return w3, contract


def send_contract_tx(w3: Web3, contract, cfg: AppConfig, fn_name: str, rid: int):
    """
    Envoie une transaction vers le smart contract.
    (Même logique que ton code original, simplement factorisée.)
    """
    nonce = w3.eth.get_transaction_count(cfg.PARKING_ADDRESS)

    if fn_name == "confirmArrival":
        fn = contract.functions.confirmArrival(rid)
    elif fn_name == "finalizeNoShow":
        fn = contract.functions.finalizeNoShow(rid)
    else:
        raise ValueError("fn_name invalide")

    tx = fn.build_transaction({
        "from": cfg.PARKING_ADDRESS,
        "nonce": nonce,
        "gas": 200000,
        "gasPrice": w3.eth.gas_price,
        "chainId": cfg.CHAIN_ID
    })

    signed = w3.eth.account.sign_transaction(tx, cfg.PARKING_PRIVATE_KEY)
    return w3.eth.send_raw_transaction(signed.rawTransaction)


# -------------------------
# MQTT callback
# -------------------------
def make_on_message():
    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except Exception:
            print("Message MQTT invalide (JSON)")
            return

        # On garde exactement ta règle: on exige reservationId + deadline
        if "reservationId" not in data or "deadline" not in data:
            print("Message MQTT ignoré (incomplet)")
            return

        rid = int(data["reservationId"])
        slot = data.get("slot", "")
        deadline = int(data["deadline"])

        if not slot or not slot.startswith("P"):
            print("Message MQTT ignoré (slot invalide)")
            return

        reservations[rid] = {"slot": slot, "deadline": deadline, "arrived": False}
        print(f"Réservation reçue → {slot} (id={rid})")

       

    return on_message


# -------------------------
# Main
# -------------------------
def main():
    cfg = AppConfig()

    # Blockchain
    w3, contract = init_web3(cfg)

    # MQTT
    mqtt_client = mqtt.Client()
    mqtt_client.on_message = make_on_message()
    mqtt_client.connect(cfg.BROKER, cfg.PORT)
    mqtt_client.subscribe(cfg.RESERVE_TOPIC)
    mqtt_client.loop_start()

    # YOLO + ROIs
    model = YOLO(cfg.MODEL_PATH)
    parking_rois = load_rois(cfg.ROI_JSON)

    # Video
    cap = cv2.VideoCapture(cfg.VIDEO_PATH)
    assert cap.isOpened(), "Impossible d’ouvrir la vidéo"

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    writer = build_writer(cfg.OUTPUT_VIDEO, fps, w, h)

    last_send = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        now = int(time.time())

        # 1) Detection
        car_centers = detect_car_centers(model, frame, cfg.YOLO_CONF)
        occupied_slots = compute_occupied_slots(parking_rois, car_centers)

        output = frame.copy()
        free_slots = []

        # 2) Check reservations (arrivée / no-show)
        for rid in list(reservations.keys()):
            r = reservations[rid]
            slot_index = slot_name_to_index(r["slot"])

            # ARRIVAL
            if slot_index in occupied_slots and not r["arrived"]:
                print(f"Arrivée détectée → {r['slot']}")
                try:
                    send_contract_tx(w3, contract, cfg, "confirmArrival", rid)
                except Exception as e:
                    print(f"Erreur confirmArrival (id={rid}): {e}")
                del reservations[rid]
                continue

            # NO-SHOW
            if now > r["deadline"] and not r["arrived"]:
                print(f"⏱ NO-SHOW → {r['slot']} → pénalité -20%")
                try:
                    send_contract_tx(w3, contract, cfg, "finalizeNoShow", rid)
                except Exception as e:
                    print(f"Erreur finalizeNoShow (id={rid}): {e}")
                del reservations[rid]

        # 3) Draw slots
        for i, slot in enumerate(parking_rois):
            roi = np.array(slot["points"], dtype=np.int32)
            name = f"P{i+1}"

            is_reserved = any(r["slot"] == name for r in reservations.values())

            if i in occupied_slots:
                color = (0, 0, 255)     # occupied: red
            elif is_reserved:
                color = (0, 165, 255)   # reserved: orange
            else:
                color = (0, 255, 0)     # free: green
                free_slots.append(name)

            cv2.polylines(output, [roi], True, color, 2)

            cx = int(np.mean(roi[:, 0]))
            cy = int(np.mean(roi[:, 1]))
            cv2.putText(output, name, (cx - 15, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 4) Publish free slots via MQTT
        if time.time() - last_send > cfg.PUBLISH_EVERY_SEC:
            mqtt_client.publish(
                cfg.FREE_TOPIC,
                json.dumps({"free_count": len(free_slots), "free_slots": free_slots})
            )
            last_send = time.time()

        cv2.imshow("SMART PARKING SERVER", output)
        writer.write(output)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # Clean
    cap.release()
    writer.release()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
