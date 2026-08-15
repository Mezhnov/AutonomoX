"""
train_custom_model.py
=====================
Скрипт для fine-tuning (дообучения) YOLOv8 на ваших собственных фото касок.

Если у вас есть набор размеченных фото (с аннотациями в формате YOLO),
этот скрипт поможет обучить собственную модель.

Формат датасета YOLO:
    dataset/
    ├── images/
    │   ├── train/   (тренировочные фото *.jpg)
    │   └── val/     (валидационные фото *.jpg)
    └── labels/
        ├── train/   (тренировочные аннотации *.txt, по одной на фото)
        └── val/     (валидационные аннотации *.txt)

Формат аннотации (одна строка на объект):
    <class_id> <x_center> <y_center> <width> <height>
    
    Координаты нормированы от 0 до 1.
    Пример: 0 0.5 0.3 0.2 0.15  (класс 0, центр (0.5, 0.3), ширина 0.2, высота 0.15)

Также необходим файл data.yaml в корне датасета:
    path: ./dataset
    train: images/train
    val: images/val
    names:
      0: hard-hat
      1: no-hard-hat
      2: person

Использование:
    python train_custom_model.py --data ./dataset/data.yaml --epochs 50
    
    # Краткая тренировка (для проверки)
    python train_custom_model.py --data ./dataset/data.yaml --epochs 10 --img 640
"""

import argparse
import os
import sys
from pathlib import Path


def check_dataset(data_yaml: str) -> bool:
    """Проверяет структуру датасета."""
    if not os.path.exists(data_yaml):
        print(f"[ERROR] Файл датасета не найден: {data_yaml}")
        return False
    
    print(f"[INFO] Найден файл конфигурации датасета: {data_yaml}")
    print("[INFO] Проверьте, что в нём правильно указаны:")
    print("         - path: путь к корню датасета")
    print("         - train: путь к тренировочным изображениям")
    print("         - val: путь к валидационным изображениям")
    print("         - names: словарь классов")
    return True


def train_model(
    data_yaml: str,
    epochs: int = 50,
    img_size: int = 640,
    base_model: str = "yolov8n.pt",
    project: str = "./runs",
    name: str = "helmet_detection"
):
    """
    Запускает обучение YOLOv8.
    
    Args:
        data_yaml: путь к data.yaml
        epochs: количество эпох
        img_size: размер изображения
        base_model: базовая модель для fine-tuning (yolov8n.pt / yolov8s.pt / yolov8m.pt)
        project: папка для сохранения результатов
        name: имя эксперимента
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics не установлен.")
        print("        Установите: pip install ultralytics")
        sys.exit(1)
    
    if not check_dataset(data_yaml):
        sys.exit(1)
    
    print(f"\n[INFO] Запуск обучения:")
    print(f"         Датасет:    {data_yaml}")
    print(f"         Базовая:    {base_model}")
    print(f"         Эпох:       {epochs}")
    print(f"         Размер:     {img_size}x{img_size}")
    print(f"         Проект:     {project}")
    print(f"         Эксперимент: {name}")
    print()
    
    # Загрузка базовой модели
    model = YOLO(base_model)
    
    # Обучение
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=img_size,
        project=project,
        name=name,
        device="auto",          # автоматически выбрать GPU/CPU
        patience=10,            # ранняя остановка если нет улучшений 10 эпох
        save=True,
        save_period=10,         # сохранять чекпоинты каждые 10 эпох
        plots=True,             # генерировать графики
        verbose=True
    )
    
    print("\n[SUCCESS] Обучение завершено!")
    print(f"[INFO] Результаты сохранены в: {project}/{name}")
    print(f"[INFO] Лучшая модель: {project}/{name}/weights/best.pt")
    
    # Копирование лучшей модели в стандартное место
    best_model_path = Path(project) / name / "weights" / "best.pt"
    if best_model_path.exists():
        target = Path("./models/helmet_model.pt")
        target.parent.mkdir(exist_ok=True)
        import shutil
        shutil.copy(best_model_path, target)
        print(f"[INFO] Лучшая модель скопирована в: {target}")
        print(f"[INFO] Теперь можно запустить: python helmet_detector.py --source webcam")
    
    return results


def create_dataset_template():
    """
    Создает шаблон структуры датасета для последующей разметки.
    """
    base = Path("./dataset")
    (base / "images" / "train").mkdir(parents=True, exist_ok=True)
    (base / "images" / "val").mkdir(parents=True, exist_ok=True)
    (base / "labels" / "train").mkdir(parents=True, exist_ok=True)
    (base / "labels" / "val").mkdir(parents=True, exist_ok=True)
    
    yaml_content = """# Конфигурация датасета для детекции касок
path: ./dataset
train: images/train
val: images/val

names:
  0: hard-hat
  1: no-hard-hat
  2: person
"""
    yaml_path = base / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)
    
    print(f"[OK] Шаблон датасета создан в: {base}")
    print(f"[INFO] Файл конфигурации: {yaml_path}")
    print()
    print("[INFO] Дальнейшие шаги:")
    print("  1. Поместите тренировочные фото в: dataset/images/train/")
    print("  2. Поместите валидационные фото в: dataset/images/val/")
    print("  3. Разметьте аннотации в формате YOLO:")
    print("     - Используйте LabelImg: pip install labelImg")
    print("     - Или Roboflow: https://roboflow.com/")
    print("     - Или CVAT: https://cvat.org/")
    print("  4. Аннотации (.txt) в dataset/labels/train/ и dataset/labels/val/")
    print("  5. Запустите обучение:")
    print("     python train_custom_model.py --data dataset/data.yaml --epochs 50")
    print()
    print("[INFO] Формат строки аннотации (один объект на строку):")
    print("  <class_id> <x_center> <y_center> <width> <height>")
    print("  Координаты нормированы 0-1 относительно размера изображения")
    print()
    print("[INFO] Пример:")
    print("  0 0.512 0.324 0.187 0.142  (hard-hat)")
    print("  2 0.500 0.550 0.250 0.500  (person)")


def main():
    parser = argparse.ArgumentParser(
        description="Обучение YOLOv8 для детекции касок на пользовательских фото",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--data", "-d",
        type=str,
        default=None,
        help="Путь к data.yaml файлу датасета"
    )
    parser.add_argument(
        "--epochs", "-e",
        type=int,
        default=50,
        help="Количество эпох обучения (по умолчанию 50)"
    )
    parser.add_argument(
        "--img",
        type=int,
        default=640,
        help="Размер изображения (по умолчанию 640)"
    )
    parser.add_argument(
        "--base",
        type=str,
        default="yolov8n.pt",
        choices=["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"],
        help="Базовая модель (n=маленькая, x=большая)"
    )
    parser.add_argument(
        "--init-template",
        action="store_true",
        help="Создать шаблон структуры датасета для разметки"
    )
    
    args = parser.parse_args()
    
    if args.init_template:
        create_dataset_template()
        return
    
    if args.data is None:
        print("[ERROR] Укажите путь к data.yaml через --data")
        print("        Или используйте --init-template для создания шаблона")
        parser.print_help()
        sys.exit(1)
    
    train_model(
        data_yaml=args.data,
        epochs=args.epochs,
        img_size=args.img,
        base_model=args.base
    )


if __name__ == "__main__":
    main()
