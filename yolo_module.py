from ultralytics import YOLO


class YoloModule:
    def __init__(self, model_path="yolov8n.pt", target_class=None, conf=0.5):
        self.model = YOLO(model_path)
        self.target_class = target_class
        self.conf = conf

    def detect_target(self, frame):
        results = self.model(frame, conf=self.conf, verbose=False)

        best_target = None
        best_area = 0

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                if self.target_class is not None and cls_id != self.target_class:
                    continue

                width = x2 - x1
                height = y2 - y1
                area = width * height

                if area > best_area:
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)

                    best_area = area
                    best_target = {
                        "class_id": cls_id,
                        "confidence": conf,
                        "bbox": (int(x1), int(y1), int(x2), int(y2)),
                        "center": (center_x, center_y)
                    }

        return best_target