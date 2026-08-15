"""
download_model.py
=================
Скрипт для загрузки предобученной YOLOv8 модели для детекции строительных касок.

Источники моделей:
    1. keremberke/yolov8n-hard-hat-detection (HuggingFace)
       Классы: hard-hat, no-hard-hat, person
    
    2. Если модель с HuggingFace недоступна, скрипт попробует другие варианты.

Использование:
    python download_model.py
"""

import os
import sys
import shutil
import urllib.request
from pathlib import Path

MODELS_DIR = Path("./models")
MODELS_DIR.mkdir(exist_ok=True)

TARGET_PATH = MODELS_DIR / "helmet_model.pt"

# Список источников для попытки загрузки (по приоритету)
MODEL_SOURCES = [
    {
        "name": "keremberke/yolov8n-hard-hat-detection",
        "url": "https://huggingface.co/keremberke/yolov8n-hard-hat-detection/resolve/main/best.pt",
        "description": "YOLOv8n обученная на hard hat detection (3 класса: hard-hat, no-hard-hat, person)"
    },
    {
        "name": "Alternative Roboflow model",
        "url": "https://huggingface.co/KutumAxel/helmet-detection-yolov8/resolve/main/best.pt",
        "description": "Альтернативная модель детекции касок"
    },
]


def download_with_huggingface_hub():
    """
    Пытается загрузить модель через huggingface-hub библиотеку.
    Это предпочтительный способ - библиотека сама обрабатывает токены и т.д.
    """
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("[WARNING] huggingface-hub не установлен. Установите: pip install huggingface-hub")
        return False
    
    repos = [
        ("keremberke/yolov8n-hard-hat-detection", "best.pt"),
        ("keremberke/yolov8m-hard-hat-detection", "best.pt"),
    ]
    
    for repo_id, filename in repos:
        try:
            print(f"[INFO] Попытка загрузки {repo_id}/{filename} через huggingface_hub...")
            local_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=str(MODELS_DIR),
                local_dir_use_symlinks=False
            )
            # local_path указывает на ./models/best.pt - переименовываем
            if os.path.exists(local_path):
                shutil.move(local_path, TARGET_PATH)
                print(f"[OK] Модель загружена и сохранена как: {TARGET_PATH}")
                return True
        except Exception as e:
            print(f"[WARNING] Не удалось: {e}")
            continue
    
    return False


def download_direct_url():
    """
    Пытается загрузить модель прямым URL запросом.
    """
    for source in MODEL_SOURCES:
        url = source["url"]
        name = source["name"]
        print(f"\n[INFO] Попытка прямой загрузки: {name}")
        print(f"       URL: {url}")
        
        try:
            print(f"[INFO] Скачивание...")
            urllib.request.urlretrieve(url, TARGET_PATH)
            
            # Проверка размера
            size = os.path.getsize(TARGET_PATH)
            if size < 1024:
                # Слишком маленький файл - наверное HTML страница с ошибкой
                os.remove(TARGET_PATH)
                print(f"[WARNING] Файл слишком маленький ({size} байт) - возможно это страница ошибки.")
                continue
            
            print(f"[OK] Модель загружена: {TARGET_PATH} ({size} байт)")
            print(f"[INFO] Описание: {source['description']}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки: {e}")
            if os.path.exists(TARGET_PATH):
                os.remove(TARGET_PATH)
            continue
    
    return False


def download_via_ultralytics():
    """
    Альтернативный способ - использовать ultralytics для загрузки базовой YOLOv8
    и потом дообучить. Это запасной вариант если модель касок недоступна.
    """
    print("\n[INFO] Попытка загрузки базовой YOLOv8n через ultralytics...")
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")
        # Базовая модель уже сохранена в кэше ultralytics
        print("[OK] Базовая YOLOv8n загружена в кэш.")
        print("[WARNING] Базовая модель определяет людей, но НЕ каски!")
        print("[WARNING] Для детекции касок запустите train_custom_model.py")
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    print("=" * 60)
    print("  ЗАГРУЗКА ПРЕДОБУЧЕННОЙ МОДЕЛИ ДЕТЕКЦИИ КАСКИ (YOLOv8)")
    print("=" * 60)
    print()
    
    # Проверка - не загружена ли уже модель
    if os.path.exists(TARGET_PATH):
        size = os.path.getsize(TARGET_PATH)
        print(f"[INFO] Модель уже существует: {TARGET_PATH} ({size} байт)")
        answer = input("Перезаписать? (y/N): ").strip().lower()
        if answer != 'y':
            print("[INFO] Отмена. Текущая модель сохранена.")
            return
        os.remove(TARGET_PATH)
    
    # Способ 1: huggingface_hub (предпочтительный)
    print("\n--- Способ 1: huggingface_hub ---")
    if download_with_huggingface_hub():
        print("\n[SUCCESS] Модель касок успешно загружена!")
        print(f"[INFO] Теперь можно запустить: python helmet_detector.py --source webcam")
        return
    
    # Способ 2: прямой URL
    print("\n--- Способ 2: Прямой URL ---")
    if download_direct_url():
        print("\n[SUCCESS] Модель касок успешно загружена!")
        print(f"[INFO] Теперь можно запустить: python helmet_detector.py --source webcam")
        return
    
    # Способ 3: базовая YOLOv8 (только как fallback)
    print("\n--- Способ 3: Базовая YOLOv8 (fallback) ---")
    if download_via_ultralytics():
        print("\n[INFO] Загружена базовая модель YOLOv8n.")
        print("[INFO] Для детекции именно касок необходимо:")
        print("         1. Запустить train_custom_model.py для обучения на ваших фото")
        print("         ИЛИ")
        print("         2. Скачать модель вручную с HuggingFace:")
        print("            https://huggingface.co/keremberke/yolov8n-hard-hat-detection")
        print("            и сохранить как ./models/helmet_model.pt")
    else:
        print("\n[ERROR] Все способы загрузки не удались.")
        print("        Проверьте интернет-соединение и попробуйте позже.")
        sys.exit(1)


if __name__ == "__main__":
    main()
