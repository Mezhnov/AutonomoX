"""
helmet_detector.py
==================
Определение строительных касок (hard hats) через веб-камеру в реальном времени.

Использует YOLOv8 с предобученной моделью для детекции касок.
Поддерживает 3 класса:
    - hard-hat     (каска надета)
    - no-hard-hat  (каска отсутствует на голове человека)
    - person       (человек)

Режимы запуска:
    1. Веб-камера в реальном времени (по умолчанию)
    2. Анализ одного изображения
    3. Анализ видеофайла

Примеры запуска:
    # Запуск с веб-камеры (камера по умолчанию = 0)
    python helmet_detector.py --source webcam

    # Запуск с конкретной камеры
    python helmet_detector.py --source webcam --camera 0

    # Анализ изображения
    python helmet_detector.py --source image --input photo.jpg

    # Анализ видеофайла
    python helmet_detector.py --source video --input video.mp4

    # Использование своей модели
    python helmet_detector.py --model ./models/my_helmet_model.pt
"""

import argparse
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# YOLOv8 from ultralytics
try:
    from ultralytics import YOLO
except ImportError:
    print("[ERROR] Библиотека ultralytics не установлена.")
    print("        Установите зависимости: pip install -r requirements.txt")
    sys.exit(1)


# ===================== КОНФИГУРАЦИЯ =====================

# Путь к модели по умолчанию (предобученная на hard hats)
DEFAULT_MODEL = "./models/helmet_model.pt"

# Если предобученной модели нет, попробуем загрузить базовый YOLOv8n
# (он не определяет каски, но детектирует людей - полезно как fallback)
FALLBACK_MODEL = "yolov8n.pt"

# Словарь классов модели hard-hat detection (keremberke/yolov8n-hard-hat-detection)
# Эти индексы соответствуют модели, обученной на датасете hard-hat detection
HELMET_CLASSES = {
    0: "hard-hat",       # Каска надета (зеленая рамка)
    1: "no-hard-hat",    # Каска отсутствует (красная рамка)
    2: "person"          # Человек (синяя рамка)
}

# Цвета для отрисовки рамок (BGR)
COLORS = {
    "hard-hat":    (0, 255, 0),     # Зеленый - каска есть
    "no-hard-hat": (0, 0, 255),     # Красный - каски нет
    "person":      (255, 0, 0),     # Синий - человек
    "default":     (0, 255, 255)    # Желтый - прочее
}

# Порог уверенности для детекции
CONFIDENCE_THRESHOLD = 0.45

# Порог Non-Maximum Suppression
IOU_THRESHOLD = 0.5


# ===================== ЗАГРУЗКА МОДЕЛИ =====================

def load_model(model_path: str) -> YOLO:
    """
    Загружает YOLOv8 модель.
    
    Если указанный файл не существует, пытается использовать:
      1. Стандартную предобученную модель касок (helmet_model.pt)
      2. Базовый YOLOv8n (детекция людей, классов касок нет)
    
    Args:
        model_path: путь к .pt файлу модели
    
    Returns:
        YOLO модель готовая к инференсу
    """
    if os.path.exists(model_path):
        print(f"[INFO] Загрузка модели: {model_path}")
        model = YOLO(model_path)
        print(f"[INFO] Модель успешно загружена.")
        print(f"[INFO] Классы модели: {model.names}")
        return model
    
    # Пробуем базовый YOLOv8n как fallback
    print(f"[WARNING] Модель {model_path} не найдена.")
    print(f"[INFO] Использую базовый YOLOv8n (только детекция людей, классов касок нет).")
    print(f"[INFO] Чтобы получить детекцию касок, запустите: python download_model.py")
    
    try:
        model = YOLO(FALLBACK_MODEL)
        print(f"[INFO] Базовая модель YOLOv8n загружена.")
        print(f"[INFO] Классы: {model.names}")
        print(f"[WARNING] Базовая модель определяет людей, но НЕ каски!")
        print(f"[WARNING] Запустите download_model.py для загрузки модели касок.")
        return model
    except Exception as e:
        print(f"[ERROR] Не удалось загрузить даже базовую модель: {e}")
        print(f"[INFO] Проверьте интернет соединение и установите ultralytics.")
        sys.exit(1)


# ===================== ОБРАБОТКА КАДРА =====================

def get_class_name(model: YOLO, class_id: int) -> str:
    """Возвращает имя класса по индексу, учитывая разные модели."""
    if class_id in model.names:
        return model.names[class_id]
    return f"class_{class_id}"


def get_color(class_name: str) -> tuple:
    """Возвращает цвет рамки в зависимости от класса."""
    class_lower = class_name.lower()
    if "hard-hat" in class_lower or "hardhat" in class_lower or "helmet" in class_lower:
        if "no" in class_lower or "without" in class_lower:
            return COLORS["no-hard-hat"]
        return COLORS["hard-hat"]
    if "person" in class_lower or "people" in class_lower:
        return COLORS["person"]
    return COLORS["default"]


def draw_detections(frame: np.ndarray, results, show_confidence: bool = True) -> np.ndarray:
    """
    Отрисовывает bounding boxes и подписи на кадре.
    
    Args:
        frame: исходный кадр (BGR)
        results: результат YOLO предсказания
        show_confidence: показывать ли уверенность
    
    Returns:
        Кадр с нарисованными рамками
    """
    annotated = frame.copy()
    
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue
        
        for box in boxes:
            # Координаты рамки
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            
            # Класс и уверенность
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            
            if confidence < CONFIDENCE_THRESHOLD:
                continue
            
            class_name = get_class_name(result.names, class_id)
            color = get_color(class_name)
            
            # Рисуем рамку
            thickness = 3
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
            
            # Подпись
            label = class_name
            if show_confidence:
                label = f"{class_name} {confidence:.2f}"
            
            # Фон под текст
            (text_w, text_h), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(
                annotated,
                (x1, y1 - text_h - baseline - 5),
                (x1 + text_w + 5, y1),
                color,
                -1
            )
            # Текст
            cv2.putText(
                annotated,
                label,
                (x1 + 2, y1 - baseline - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )
    
    return annotated


def draw_stats(frame: np.ndarray, results, fps: float = 0.0) -> np.ndarray:
    """
    Рисует статистику в верхнем левом углу:
      - FPS
      - Количество людей
      - Количество касок надетых
      - Количество без каски
    """
    stats = {
        "hard-hat": 0,
        "no-hard-hat": 0,
        "person": 0
    }
    
    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            conf = float(box.conf[0].item())
            if conf < CONFIDENCE_THRESHOLD:
                continue
            class_id = int(box.cls[0].item())
            class_name = get_class_name(result.names, class_id).lower()
            
            if "hard-hat" in class_name or "hardhat" in class_name or "helmet" in class_name:
                if "no" in class_name or "without" in class_name:
                    stats["no-hard-hat"] += 1
                else:
                    stats["hard-hat"] += 1
            elif "person" in class_name or "people" in class_name:
                stats["person"] += 1
    
    # Текстовая панель
    lines = [
        f"FPS: {fps:.1f}",
        f"Persons: {stats['person']}",
        f"With helmet: {stats['hard-hat']}",
        f"Without helmet: {stats['no-hard-hat']}",
    ]
    
    # Полупрозрачный фон
    panel_h = len(lines) * 28 + 10
    panel_w = 240
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (10 + panel_w, 10 + panel_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    
    # Текст
    y_offset = 32
    for i, line in enumerate(lines):
        color = (255, 255, 255)
        if "Without" in line and stats["no-hard-hat"] > 0:
            color = (0, 0, 255)   # красный
        elif "With" in line and stats["hard-hat"] > 0:
            color = (0, 255, 0)   # зеленый
        cv2.putText(
            frame,
            line,
            (20, y_offset + i * 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA
        )
    
    return frame


# ===================== ОСНОВНЫЕ РЕЖИМЫ РАБОТЫ =====================

def run_webcam(model: YOLO, camera_index: int = 0):
    """
    Запускает детекцию в реальном времени с веб-камеры.
    
    Управление:
        Q / ESC - выход
        S       - сохранить кадр в ./output/
        F       - вкл/выкл показ уверенности
        D       - вкл/выкл показ статистики
    """
    print(f"[INFO] Открытие камеры #{camera_index}...")
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"[ERROR] Не удалось открыть камеру {camera_index}.")
        print("        Проверьте, что камера подключена и не занята другим приложением.")
        return
    
    # Настройки камеры
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("[INFO] Камера открыта. Запуск детекции...")
    print("[INFO] Управление:")
    print("         Q / ESC - выход")
    print("         S       - сохранить кадр")
    print("         F       - вкл/выкл уверенность")
    print("         D       - вкл/выкл статистику")
    
    show_confidence = True
    show_stats = True
    save_dir = Path("./output")
    save_dir.mkdir(exist_ok=True)
    
    prev_time = time.time()
    fps = 0.0
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[WARNING] Не удалось получить кадр с камеры.")
                break
            
            # Запуск детекции
            results = model(
                frame,
                conf=CONFIDENCE_THRESHOLD,
                iou=IOU_THRESHOLD,
                verbose=False
            )
            
            # Отрисовка
            annotated = draw_detections(frame, results, show_confidence)
            if show_stats:
                annotated = draw_stats(annotated, results, fps)
            
            # FPS расчет
            frame_count += 1
            if frame_count % 10 == 0:
                curr_time = time.time()
                fps = 10.0 / (curr_time - prev_time)
                prev_time = curr_time
            
            # Показ
            cv2.imshow("Helmet Detection (press Q to quit)", annotated)
            
            # Обработка клавиш
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):  # Q или ESC
                break
            elif key == ord('s'):
                filename = save_dir / f"frame_{int(time.time())}.jpg"
                cv2.imwrite(str(filename), annotated)
                print(f"[INFO] Кадр сохранен: {filename}")
            elif key == ord('f'):
                show_confidence = not show_confidence
                print(f"[INFO] Показ уверенности: {show_confidence}")
            elif key == ord('d'):
                show_stats = not show_stats
                print(f"[INFO] Показ статистики: {show_stats}")
    
    except KeyboardInterrupt:
        print("\n[INFO] Прервано пользователем.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("[INFO] Камера освобождена.")


def run_image(model: YOLO, image_path: str, output_path: str = None):
    """
    Анализ одного изображения.
    """
    if not os.path.exists(image_path):
        print(f"[ERROR] Файл не найден: {image_path}")
        return
    
    print(f"[INFO] Анализ изображения: {image_path}")
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"[ERROR] Не удалось прочитать изображение: {image_path}")
        return
    
    # Запуск детекции
    results = model(
        frame,
        conf=CONFIDENCE_THRESHOLD,
        iou=IOU_THRESHOLD,
        verbose=False
    )
    
    # Отрисовка
    annotated = draw_detections(frame, results, show_confidence=True)
    annotated = draw_stats(annotated, results, fps=0.0)
    
    # Сохранение
    if output_path is None:
        output_path = f"output_{Path(image_path).name}"
    
    cv2.imwrite(output_path, annotated)
    print(f"[INFO] Результат сохранен: {output_path}")
    
    # Вывод в консоль
    print("\n[RESULTS] Найденные объекты:")
    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            class_name = get_class_name(result.names, class_id)
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            print(f"  - {class_name}: conf={confidence:.3f}, "
                  f"box=({x1},{y1})-({x2},{y2})")
    
    # Показ
    cv2.imshow("Result (press any key to close)", annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def run_video(model: YOLO, video_path: str):
    """
    Анализ видеофайла.
    """
    if not os.path.exists(video_path):
        print(f"[ERROR] Файл не найден: {video_path}")
        return
    
    print(f"[INFO] Открытие видео: {video_path}")
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"[ERROR] Не удалось открыть видео: {video_path}")
        return
    
    fps_in = cap.get(cv2.CAP_PROP_FPS)
    print(f"[INFO] FPS видео: {fps_in}")
    
    prev_time = time.time()
    fps = 0.0
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[INFO] Конец видео.")
                break
            
            results = model(
                frame,
                conf=CONFIDENCE_THRESHOLD,
                iou=IOU_THRESHOLD,
                verbose=False
            )
            
            annotated = draw_detections(frame, results, True)
            annotated = draw_stats(annotated, results, fps)
            
            frame_count += 1
            if frame_count % 10 == 0:
                curr_time = time.time()
                fps = 10.0 / (curr_time - prev_time)
                prev_time = curr_time
            
            cv2.imshow("Video Detection (press Q to quit)", annotated)
            
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                break
    except KeyboardInterrupt:
        print("\n[INFO] Прервано пользователем.")
    finally:
        cap.release()
        cv2.destroyAllWindows()


# ===================== ТОЧКА ВХОДА =====================

def main():
    parser = argparse.ArgumentParser(
        description="Детекция строительных касок через веб-камеру (YOLOv8)",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--source", "-s",
        choices=["webcam", "image", "video"],
        default="webcam",
        help="Источник: webcam (по умолчанию), image, video"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=None,
        help="Путь к файлу (для image или video)"
    )
    parser.add_argument(
        "--camera", "-c",
        type=int,
        default=0,
        help="Индекс камеры (по умолчанию 0)"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Путь к .pt файлу модели (по умолчанию {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Путь сохранения результата (для режима image)"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=CONFIDENCE_THRESHOLD,
        help=f"Порог уверенности (по умолчанию {CONFIDENCE_THRESHOLD})"
    )
    
    args = parser.parse_args()
    
    # Глобальная настройка порога уверенности
    global CONFIDENCE_THRESHOLD
    CONFIDENCE_THRESHOLD = args.conf
    
    # Загрузка модели
    model = load_model(args.model)
    
    # Запуск в выбранном режиме
    if args.source == "webcam":
        run_webcam(model, args.camera)
    elif args.source == "image":
        if args.input is None:
            print("[ERROR] Для режима image укажите --input <путь_к_файлу>")
            sys.exit(1)
        run_image(model, args.input, args.output)
    elif args.source == "video":
        if args.input is None:
            print("[ERROR] Для режима video укажите --input <путь_к_файлу>")
            sys.exit(1)
        run_video(model, args.input)


if __name__ == "__main__":
    main()
