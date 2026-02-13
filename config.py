
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    # ---------------------
    # Video / YOLO / ROI
    # ---------------------
    VIDEO_PATH: str = "Test/VideoTest.mp4"
    OUTPUT_VIDEO: str = "Test/smart_parking_result.mp4"
    MODEL_PATH: str = "Model/best.pt"
    ROI_JSON: str = "BBox/bounding_boxes.json"
    YOLO_CONF: float = 0

    # ---------------------
    # MQTT
    # ---------------------
    BROKER: str = "localhost"
    PORT: int = 1883
    FREE_TOPIC: str = "city/parking/free"
    RESERVE_TOPIC: str = "city/parking/reserved"
    PUBLISH_EVERY_SEC: float = 3.0

    # ---------------------
    # IOTA EVM
    # ---------------------
    RPC_URL: str = "https://json-rpc.evm.testnet.iota.cafe"
    CHAIN_ID: int = 1076

    PARKING_PRIVATE_KEY: str = ""
    PARKING_ADDRESS: str = ""

    SMART_CONTRACT_ADDRESS = ""

    SMART_CONTRACT_ABI: list = field(default_factory=lambda: [
        {
            "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
            "name": "finalizeNoShow",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
            "name": "confirmArrival",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ])
