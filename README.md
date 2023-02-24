# Расписание трамваев г.Ижевск

Данные берутся с сайта [ИжГЭТ](https://ижгэт.рф/rasp/)

## Установка
linux:
```bash
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Windows
```bash
pip install virtualenv
virtualenv --python C:\Path\To\Python\python.exe venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка
Добавьте токен бота в ваш файл `.env` в корне проекта:
```shell
BOT_TOKEN='your token'
```

## Запуск
```bash
python main.py
```
