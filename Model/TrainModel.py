from ultralytics import YOLO
import os, yaml

class YOLOTrainer:
    def __init__(
        self,
        model_name="yolo12s.pt",
        data_yaml="dataset.yaml",
        imgsz=960,
        device=0,
        project="runs_det",
        run_name="yolo12s_detrac_carvan"
    ):
  
        self.model = YOLO(model_name)
        self.data_yaml = data_yaml
        self.imgsz = imgsz
        self.device = device
        self.project = project
        self.run_name = run_name

    def train(
        self,
        epochs=30,
        batch=16,
        workers=4,

        # fine-tuning
        freeze=12,
        patience=4,
        lr0=0.005,
        lrf=0.01,

        # loss weights
        box=7.5,
        cls=0.5,

    ):
        """
        Entraînement YOLO optimisé pour scènes fixes
        et détection de véhicules légers.
        """

        results = self.model.train(
            data=self.data_yaml,
            imgsz=self.imgsz,
            epochs=epochs,
            batch=batch,
            device=self.device,
            workers=workers,

            # stabilité apprentissage
            freeze=freeze,
            patience=patience,
            lr0=lr0,
            lrf=lrf,

            # pondération pertes
            box=box,
            cls=cls,
            
            # NMS (impact direct precision / recall)
            conf=0.30,          
            iou=0.60,           
            max_det=300,        
            agnostic_nms=True,  
           
            project=self.project,
            name=self.run_name,
        )

        return results

    def validate(self):
        """
        Évaluation finale sur validation UA-DETRAC.
        """
        return self.model.val(
            data=self.data_yaml,
            imgsz=self.imgsz,
            device=self.device
        )

    def export_onnx(self):
        """
        Export ONNX pour edge deployment / quantization.
        """
        return self.model.export(
            format="onnx",
            imgsz=self.imgsz,
            simplify=True
        )
    
data = {
    "train": "data/images/train",
    "val": "data/images/val",
    "nc": 1,
    "names":  ["car"]
}

with open("dataset.yaml", "w") as f:
    yaml.safe_dump(data, f, sort_keys=False)

print("dataset.yaml créé :", "dataset.yaml")

trainer = YOLOTrainer(
    model_name="yolo12l.pt",
    data_yaml="dataset.yaml",
    imgsz=768,
    device=0,
    project="runs",
    run_name="yolov8n_detrac_car_rot"
)

trainer.train()