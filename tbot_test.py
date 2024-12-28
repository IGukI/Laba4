from typing import Any

import requests
import telebot
from telebot import types

API_URL = 'https://open.er-api.com/v6/latest/'
API_TOKEN = '8094863586:AAFdkqW3lRHy7zAvd9uhh8CmpzcT7LI6v0s'

bot = telebot.TeleBot(API_TOKEN)

global base_currency
base_currency = "USD"

# Функция получения актуальных курсов валют
def get_exchange_rates(currency) -> str | Any:
    try:
        response = requests.get(f"{API_URL}{currency}")
        response.raise_for_status()
        data = response.json()
        return data['rates']
    except requests.RequestException as e:
        print(e)
        return None


def get_available_currencies():
    try:
        response = requests.get(f"{API_URL}USD")
        response.raise_for_status()
        data = response.json()
        return data['rates'].keys()
    except requests.RequestException as e:
        return str(e)


@bot.message_handler(commands=['start'])
def start_command(message: types.Message):
    start_menu(message)


def start_menu(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_rates = types.KeyboardButton("📈 Получить курсы валют")
    button_convert = types.KeyboardButton("💱 Конвертировать валюту")
    button_settings = types.KeyboardButton("⚙️ Настройки")
    button_available_currencies = types.KeyboardButton("💱 Доступные валюты")

    markup.add(button_rates, button_convert, button_settings, button_available_currencies)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "📈 Получить курсы валют")
def rates_command(message: types.Message):
    global base_currency
    rates = get_exchange_rates(base_currency)
    if isinstance(rates, str):
        bot.send_message(message.chat.id, f"Ошибка получения данных: {rates}")
    else:
        rates_message = "\n".join([f"{currency}: {rate}" for currency, rate in rates.items()])
        bot.send_message(message.chat.id, f"Актуальные курсы валют:\n{rates_message}")


@bot.message_handler(func=lambda message: message.text == "💱 Доступные валюты")
def available_currencies_command(message: types.Message):
    currencies = get_available_currencies()
    if isinstance(currencies, str):
        bot.send_message(message.chat.id, f"Ошибка получения данных: {currencies}")
    else:
        currencies_message = "\n".join(currencies)  # Формируем список доступных валют
        bot.send_message(message.chat.id, f"Доступные валюты:\n{currencies_message}")


# Обработка команды конвертации валюты
@bot.message_handler(func=lambda message: message.text == "💱 Конвертировать валюту")
def convert_command(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    rates = get_exchange_rates('USD')

    if isinstance(rates, str):
        bot.send_message(message.chat.id, f"Ошибка получения данных: {rates}")
        return

    currency_buttons = [types.KeyboardButton(currency) for currency in rates.keys()]
    currency_buttons.insert(0, "BASE")
    markup.add(*currency_buttons)

    bot.send_message(message.chat.id, "Выберите валюту, которую хотите конвертировать:", reply_markup=markup)
    bot.register_next_step_handler(message, process_currency_from)


def process_currency_from(message: types.Message):
    currency_from = message.text
    rates = get_exchange_rates('USD')

    if currency_from not in rates and currency_from != "BASE":
        bot.send_message(message.chat.id, "Неправильная валюта. Пожалуйста, выберите снова.")
        return convert_command(message)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    currency_buttons = [types.KeyboardButton(currency) for currency in rates.keys() if currency != currency_from]
    markup.add(*currency_buttons)

    bot.send_message(message.chat.id, "Выберите валюту, в которую хотите конвертировать:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda m: process_currency_to(m, currency_from))


def process_currency_to(message: types.Message, currency_from: str):
    currency_to = message.text
    rates = get_exchange_rates('USD')

    if currency_to not in rates:
        bot.send_message(message.chat.id, "Неправильная валюта. Пожалуйста, выберите снова.")
        return process_currency_from(message)

    # Запрос суммы для конвертации
    bot.send_message(message.chat.id, f"Введите сумму в {currency_from} для конвертации в {currency_to}:")
    bot.register_next_step_handler(message, lambda m: convert_currency(m, currency_from, currency_to))


def convert_currency(message: types.Message, currency_from: str, currency_to: str):
    try:
        global base_currency
        amount = float(message.text)
        rates = get_exchange_rates('USD')
        if currency_from == "BASE":
            currency_from = base_currency

        if currency_from in rates and currency_to in rates:
            converted_amount = amount * (rates[currency_to] / rates[currency_from])
            bot.send_message(message.chat.id, f"{amount} {currency_from} = {converted_amount:.2f} {currency_to}")
        else:
            bot.send_message(message.chat.id, "Ошибка в конвертации валют.")
        start_menu(message)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректную сумму.")


# Обработка команды настроек
@bot.message_handler(func=lambda message: message.text == "⚙️ Настройки")
def settings_command(message: types.Message):
    bot.send_message(message.chat.id, "Вы можете сохранить настройки, отправив команду /save <валюта>.")


@bot.message_handler(commands=['save'])
def save_settings_command(message: types.Message):
    global base_currency
    base_currency = message.text.split(' ', 1)[1].strip().upper() if len(message.text.split()) > 1 else ''

    rates = get_exchange_rates(base_currency)

    if base_currency in rates:
        bot.send_message(message.chat.id, f"Настройки сохранены! Предпочитаемая валюта: {base_currency}.")
    else:
        base_currency = "USD"
        bot.send_message(message.chat.id, f"Неправильная валюта: {base_currency}. Используйте команду /rates для проверки.")


@bot.message_handler(func=lambda message: True)
def handle_unknown_message(message: types.Message):
    bot.send_message(message.chat.id, "Команда не распознана. Пожалуйста, используйте меню или доступные команды.")


if __name__ == '__main__':
    bot.polling(none_stop=True)