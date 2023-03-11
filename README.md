# Расписание трамваев г.Ижевск

Данные берутся с сайта [ИжГЭТ](https://ижгэт.рф/rasp/)

Проверить можно тут https://t.me/izhGet_bot

## Установка
> Мин. требования python 3.9

linux:
```bash
git clone https://github.com/yuschkof/izhGet_bot.git
cd izhGet_bot
python3.9 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```
Windows:
```bash
git clone https://github.com/yuschkof/izhGet_bot.git
cd izhGet_bot
python -m venv venv
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

# Запуск бота на бесконечную работу (Ubuntu 22.04)

1. Обновите пакеты
  ```bash
  sudo apt update ; sudo apt upgrade
  ```
  > Убедитесь что у вас установлен python версии от 3.9 `python3 --version`

2. Установите systemd
  ```bash
  apt-get install systemd
  ```
3. Настройте файл конфигурации
  ```bash
  vi /etc/systemd/system/bot.service
  ```
  ```bash
  [Unit]
  Description=Telegram bot 'izhGet_bot'
  After=syslog.target
  After=network.target

  [Service]
  Type=simple
  User=root
  WorkingDirectory=/usr/local/bin/bot  # рабочая директория (каталог)
  ExecStart=/usr/bin/python3 /usr/local/bin/bot/main.py  # путь до python и основного файла бота
  RestartSec=10
  Restart=always

  [Install]
  WantedBy=multi-user.target
  ```
  > Чтобы узнать путь до директории бота, введите `pwd`, находясь в в корне проекта.
  
  > Чтобы узнать путь до python, введите `which python3`
4. Запустите бота
  * ```systemctl daemon-reload```
  * ```systemctl enable bot.service```
  * ```systemctl start bot.service```
  * ```systemctl status bot.service```
