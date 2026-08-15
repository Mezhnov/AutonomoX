# Детекция строительных касок через веб-камеру (YOLOv8)

Python-приложение для определения строительных касок (hard hats) в реальном времени через веб-камеру с помощью нейросети YOLOv8.

## Возможности

- Определение касок в реальном времени с веб-камеры
- Анализ отдельных изображений и видеофайлов
- 3 класса объектов: `hard-hat` (каска надета), `no-hard-hat` (каски нет), `person` (человек)
- Цветовая индикация: зелёная рамка — каска есть, красная — нет
- Подсчёт статистики (FPS, количество людей, количество с каской/без)
- Сохранение кадров по нажатию клавиши
- Возможность обучения собственной модели на ваших фото

## Требования

- Python 3.8+
- Веб-камера
- ОС: Windows / macOS / Linux

## Установка

```bash
# 1. Перейдите в папку проекта
cd helmet_detector

# 2. (Рекомендуется) Создайте виртуальное окружение
python -m venv venv

# Активация на Windows:
venv\Scripts\activate
# Активация на macOS/Linux:
source venv/bin/activate

# 3. Установите зависимости
pip install -r requirements.txt
```

## Загрузка предобученной модели

Перед первым запуском необходимо загрузить модель, обученную для детекции касок:

```bash
python download_model.py
```

Скрипт попытается загрузить модель `keremberke/yolov8n-hard-hat-detection` с HuggingFace (классы: hard-hat, no-hard-hat, person). Модель сохранится в `./models/helmet_model.pt`.

Если автоматически скачать не удалось:
1. Зайдите на https://huggingface.co/keremberke/yolov8n-hard-hat-detection
2. Скачайте файл `best.pt`
3. Переименуйте его в `helmet_model.pt` и положите в папку `models/`

## Запуск

### Веб-камера (основной режим)

```bash
python helmet_detector.py --source webcam
```

Выбор конкретной камеры:
```bash
python helmet_detector.py --source webcam --camera 0   # первая камера
python helmet_detector.py --source webcam --camera 1   # вторая камера (если есть)
```

### Анализ изображения

```bash
python helmet_detector.py --source image --input photo.jpg
```

С указанием пути сохранения:
```bash
python helmet_detector.py --source image --input photo.jpg --output result.jpg
```

### Анализ видеофайла

```bash
python helmet_detector.py --source video --input video.mp4
```

### Управление (в режиме веб-камеры/видео)

| Клавиша | Действие |
|---------|----------|
| `Q` или `ESC` | Выход |
| `S` | Сохранить текущий кадр в `./output/` |
| `F` | Включить/выключить показ уверенности |
| `D` | Включить/выключить показ статистики |

### Дополнительные параметры

```bash
# Изменить порог уверенности (по умолчанию 0.45)
python helmet_detector.py --conf 0.6

# Использовать другую модель
python helmet_detector.py --model ./models/my_model.pt
```

## Обучение собственной модели

Если готовая модель работает плохо на ваших касках (например, на российских касках РОСОМЗ), можно обучить свою.

### Шаг 1: Подготовка датасета

```bash
python train_custom_model.py --init-template
```

Создаст структуру:
```
dataset/
├── images/
│   ├── train/    ← положите тренировочные фото (.jpg)
│   └── val/      ← положите валидационные фото (.jpg)
├── labels/
│   ├── train/    ← положите аннотации (.txt)
│   └── val/
└── data.yaml
```

### Шаг 2: Разметка аннотаций

Используйте один из инструментов разметки:
- **LabelImg** (бесплатно, локально): `pip install labelImg`, запуск: `labelImg`
- **Roboflow** (онлайн, удобно): https://roboflow.com/
- **CVAT** (онлайн, мощно): https://cvat.org/

Формат аннотации YOLO (одна строка на объект):
```
<class_id> <x_center> <y_center> <width> <height>
```
Координаты нормированы от 0 до 1 относительно размера изображения.

Классы (указаны в `data.yaml`):
- `0` — hard-hat (каска надета)
- `1` — no-hard-hat (человек без каски)
- `2` — person (человек)

Пример содержимого `IMG_2826.txt`:
```
0 0.512 0.324 0.187 0.142
2 0.500 0.550 0.250 0.500
```

### Шаг 3: Обучение

```bash
# Полное обучение (50 эпох)
python train_custom_model.py --data dataset/data.yaml --epochs 50

# Быстрая проверка (10 эпох)
python train_custom_model.py --data dataset/data.yaml --epochs 10

# Использование более крупной базовой модели (лучше качество, дольше обучение)
python train_custom_model.py --data dataset/data.yaml --epochs 100 --base yolov8s.pt
```

После обучения лучшая модель автоматически копируется в `./models/helmet_model.pt` и готова к использованию.

### Рекомендации по датасету

- Минимум **100–300** размеченных фото для приемлемого качества
- Разные ракурсы, освещение, фоны
- ~20% фото — валидационные (в `val/`)
- Если фото мало — используйте аугментацию (ultralytics делает это автоматически)

## Структура проекта

```
helmet_detector/
├── helmet_detector.py        ← основной скрипт (веб-камера/фото/видео)
├── download_model.py         ← загрузка предобученной модели
├── train_custom_model.py     ← обучение собственной модели
├── requirements.txt          ← зависимости
├── README.md                 ← этот файл
├── models/                   ← папка для .pt моделей
└── dataset/                  ← папка для датасета (создаётся при --init-template)
```

## Решение проблем

### "Не удалось открыть камеру"
- Проверьте, что камера не занята другим приложением (Skype, Zoom, браузер)
- На Linux: `sudo usermod -aG video $USER` и перезайдите в систему
- Попробуйте другой индекс камеры: `--camera 1`

### "Model not found"
- Запустите `python download_model.py`
- Или скачайте модель вручную с HuggingFace

### Низкий FPS
- Используйте модель `yolov8n` (nano) — она самая быстрая
- Уменьшите разрешение камеры в коде (`CAP_PROP_FRAME_WIDTH`)
- Если есть GPU — установите CUDA: `pip install torch --index-url https://download.pytorch.org/whl/cu118`

### Плохая точность
- Понизьте порог уверенности: `--conf 0.3`
- Обучите собственную модель на ваших касках (`train_custom_model.py`)
- Соберите больше фото для датасета

## Технические детали

- **Модель**: YOLOv8n (Ultralytics) — самый быстрый вариант
- **Backend**: PyTorch
- **Захват видео**: OpenCV
- **Размер входа**: 640×640 пикселей
- **Скорость**: 15–30 FPS на CPU, 60+ FPS на GPU

## Источники

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics)
- [HuggingFace: keremberke/yolov8n-hard-hat-detection](https://huggingface.co/keremberke/yolov8n-hard-hat-detection)
- [Датасет Hard Hat Detection](https://www.kaggle.com/datasets/andrewmvd/hard-hat-detection)
