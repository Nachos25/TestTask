# AutoRia Scraper

Додаток для автоматичного збору даних про вживані автомобілі з сайту AutoRia.

## Опис

Додаток виконує наступні функції:
- Щоденний скрапінг платформи AutoRia для збору даних про вживані автомобілі
- Збереження даних у PostgreSQL базу даних
- Щоденне створення резервних копій бази даних

## Структура проекту

```
autoria_scraper/            # Основний пакет
├── __init__.py             # Ініціалізація пакету
├── __main__.py             # Точка входу в додаток
├── config.py               # Конфігурація додатку
├── database.py             # Робота з базою даних
└── scraper.py              # Модуль скрапера
docker-compose.yml          # Налаштування Docker Compose
Dockerfile                  # Налаштування Docker образу
requirements.txt            # Залежності проекту
.env                        # Файл з налаштуваннями оточення
```

## Поля бази даних

- url (рядок) - URL сторінки автомобіля
- title (рядок) - Назва автомобіля
- price_usd (число) - Ціна в USD
- odometer (число) - Пробіг в кілометрах
- username (рядок) - Ім'я продавця
- phone_number (число) - Номер телефону
- image_url (рядок) - URL головного зображення
- images_count (число) - Кількість зображень
- car_number (рядок) - Держ. номер авто
- car_vin (рядок) - VIN-код
- datetime_found (дата) - Дата та час збереження в базу

## Запуск додатку

### Попередні вимоги

- Docker і Docker Compose
- Git

### Кроки для запуску

1. Клонувати репозиторій:
   ```
   git clone https://github.com/yourusername/autoria-scraper.git
   cd autoria-scraper
   ```

2. Створити файл .env з налаштуваннями:
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

3. Запустити додаток за допомогою Docker Compose:
   ```
   docker-compose up -d
   ```

4. Перевірити логи додатку:
   ```
   docker-compose logs -f app
   ```

### Резервні копії бази даних

Резервні копії бази даних зберігаються в директорії `dumps/` з іменем файлу формату `autoria_dump_YYYYMMDD_HHMMSS.sql`.

### Налаштування розкладу

- Час запуску скрапера налаштовується через змінну `SCRAPE_SCHEDULE_TIME` у файлі `.env`
- Час створення резервної копії налаштовується через змінну `DUMP_SCHEDULE_TIME` у файлі `.env`

## Технології

- Python 3.10
- PostgreSQL
- Docker & Docker Compose
- aiohttp - для асинхронних HTTP запитів
- Selenium - для обробки динамічного контенту
- asyncpg - для асинхронної роботи з PostgreSQL
- schedule - для планування завдань
- loguru - для логування
- BeautifulSoup4 - для парсингу HTML 
