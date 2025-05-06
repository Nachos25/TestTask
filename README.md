# AutoRia Scraper

Приложение для автоматического сбора данных о б/у автомобилях с сайта AutoRia.

## Описание

Приложение выполняет следующие функции:
- Ежедневный скрапинг платформы AutoRia для сбора данных о б/у автомобилях
- Сохранение данных в PostgreSQL базу данных
- Ежедневное создание резервных копий базы данных

## Структура проекта

```
autoria_scraper/            # Основной пакет
├── __init__.py             # Инициализация пакета
├── __main__.py             # Точка входа в приложение
├── config.py               # Конфигурация приложения
├── database.py             # Работа с базой данных
└── scraper.py              # Модуль скрапера
docker-compose.yml          # Настройки Docker Compose
Dockerfile                  # Настройка Docker образа
requirements.txt            # Зависимости проекта
.env                        # Файл с настройками окружения
```

## Поля базы данных

- url (строка) - URL страницы автомобиля
- title (строка) - Название автомобиля
- price_usd (число) - Цена в USD
- odometer (число) - Пробег в километрах
- username (строка) - Имя продавца
- phone_number (число) - Номер телефона
- image_url (строка) - URL основного изображения
- images_count (число) - Количество изображений
- car_number (строка) - Гос. номер авто
- car_vin (строка) - VIN-код
- datetime_found (дата) - Дата и время сохранения в базу

## Запуск приложения

### Предварительные требования

- Docker и Docker Compose
- Git

### Шаги по запуску

1. Клонировать репозиторий:
   ```
   git clone https://github.com/yourusername/autoria-scraper.git
   cd autoria-scraper
   ```

2. Создать файл .env с настройками:
   ```
   # Database settings
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=autoria
   POSTGRES_HOST=db
   POSTGRES_PORT=5432

   # Application settings
   START_URL=https://auto.ria.com/uk/search/?indexName=auto,order_auto,newauto_search&categories.main.id=1&country.import.usa.not=-1&price.currency=1&abroad.not=0&custom.not=1&page=0&size=100
   SCRAPE_SCHEDULE_TIME=12:00
   DUMP_SCHEDULE_TIME=00:00
   TIMEZONE=Europe/Kiev

   # Scraper settings
   CONCURRENCY=5
   REQUEST_TIMEOUT=30
   REQUEST_DELAY=1
   MAX_RETRIES=3
   ```

3. Запустить приложение с помощью Docker Compose:
   ```
   docker-compose up -d
   ```

4. Проверить логи приложения:
   ```
   docker-compose logs -f app
   ```

### Резервные копии базы данных

Резервные копии базы данных сохраняются в директории `dumps/` с именем файла формата `autoria_dump_YYYYMMDD_HHMMSS.sql`.

### Настройка расписания

- Время запуска скрапера настраивается через переменную `SCRAPE_SCHEDULE_TIME` в файле `.env`
- Время создания резервной копии настраивается через переменную `DUMP_SCHEDULE_TIME` в файле `.env`

## Технологии

- Python 3.10
- PostgreSQL
- Docker & Docker Compose
- aiohttp - для асинхронных HTTP запросов
- Selenium - для обработки динамического контента
- asyncpg - для асинхронной работы с PostgreSQL
- schedule - для планирования задач
- loguru - для логирования
- BeautifulSoup4 - для парсинга HTML 