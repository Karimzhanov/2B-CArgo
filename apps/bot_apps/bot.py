from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import logging
from dotenv import load_dotenv
import os
import django
from asgiref.sync import sync_to_async  # Добавлен импорт

# Load Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telegram_bot_admin.settings')
django.setup()

from apps.bot_apps.models import Client, Code

# Загрузка токена бота из конфигурационного файла
load_dotenv()
token = os.getenv("TOKEN")

# Инициализация бота и диспетчера
bot = Bot(token=token)
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# Функция для генерации персонального кода
async def generate_personal_code():
    last_code = await sync_to_async(Code.objects.order_by('-id').first)()
    new_code = last_code.code + 1 if last_code else 3199
    await sync_to_async(Code.objects.create)(code=new_code)
    return f"2B-{new_code}"

# Класс для состояний регистрации
class RegisterProcess(StatesGroup):
    first_name = State()
    last_name = State()
    phone_number = State()
    warehouse_address = State()

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    # Проверяем, есть ли у пользователя уже персональный код
    client = await sync_to_async(Client.objects.filter(id=message.from_user.id).first)()
    if client and client.personal_code:
        await send_main_menu(message)
    else:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Начать регистрацию", callback_data='start_registration'))
        await message.reply("Здравствуйте! Вас приветствует 2B-Сargo. Для начала регистрации нажмите кнопку ниже:", reply_markup=keyboard)

# Обработчик callback для начала регистрации
@dp.callback_query_handler(lambda c: c.data == 'start_registration')
async def start_registration(callback_query: types.CallbackQuery):
    await RegisterProcess.first_name.set()
    await bot.send_message(callback_query.from_user.id, "Для регистрации, пожалуйста, введите своё имя.")

# Обработчик для ввода имени пользователя
@dp.message_handler(state=RegisterProcess.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['first_name'] = message.text
    await RegisterProcess.next()
    await message.reply("Теперь введите свою фамилию.")

# Обработчик для ввода фамилии пользователя
@dp.message_handler(state=RegisterProcess.last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['last_name'] = message.text
    await RegisterProcess.next()
    
    contact_button = KeyboardButton("Поделитесь контактом", request_contact=True)
    contact_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(contact_button)
    await message.reply("Отлично! Теперь поделитесь своим номером телефона.", reply_markup=contact_keyboard)

# Обработчик для получения контактного номера пользователя
@dp.message_handler(content_types=types.ContentType.CONTACT, state=RegisterProcess.phone_number)
async def process_phone_number(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone_number'] = message.contact.phone_number
    await RegisterProcess.next()
    await message.reply("Прекрасно! Теперь выберите адрес склада в Китае.", reply_markup=warehouse_keyboard())

# Функция для отправки клавиатуры выбора склада
def warehouse_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Гуанчжоу", callback_data='warehouse_guangzhou'))
    return keyboard

# Обработчик callback для выбора склада (Гуанчжоу)
@dp.callback_query_handler(lambda c: c.data == 'warehouse_guangzhou', state=RegisterProcess.warehouse_address)
async def process_warehouse_choice(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        personal_code = await generate_personal_code()
        data['personal_code'] = personal_code
        data['warehouse_address'] = "Гуанчжоу"
    
    await sync_to_async(Client.objects.create)(
        id=callback_query.from_user.id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        phone_number=data['phone_number'],
        personal_code=data['personal_code'],
        warehouse_address=data['warehouse_address']
    )

    warehouse_message = f"""名字：{data['personal_code']}
电话号：18320304605
地址：广东省 广州市 白云区 白云湖街道
细地址：石井石门街红星东成大街3号({data['personal_code']})
邮政编码：510430"""

    response_message = f"""Имя: {data['first_name']}
Фамилия: {data['last_name']}
Телефон: {data['phone_number']}
Адрес склада: {data['warehouse_address']}
Ваш персональный код: {data['personal_code']}

{warehouse_message}

Спасибо за регистрацию!
    """

    await bot.send_message(callback_query.from_user.id, response_message)
    await state.finish()
    await bot.answer_callback_query(callback_query.id)
    await send_main_menu(callback_query.message)

# Новый обработчик для callback 'about_us'
@dp.callback_query_handler(lambda c: c.data == 'about_us')
async def about_us(callback_query: types.CallbackQuery):
    about_message = "Мы компания 2B-Cargo, предоставляем услуги по доставке товаров из Китая в Ош." \
                    "2B Cargo " \
                    "🚚📦АВТОДОСТАВКА 3,49$(только за июль). 9-14дней.\n\n" \
                    "🇨🇳 Гуанчжоу  -🇰🇬ОШ\n\n" \
                    "☎Номера  нашего менеджера: +996999221299\n" 

    await bot.send_message(callback_query.from_user.id, about_message)
    await send_main_menu(callback_query.message)  # Вернуться в главное меню после отправки сообщения

# Обновленная функция send_main_menu для включения раздела 'Приложения' и других кнопок
async def send_main_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Приложения", callback_data='applications'),
        InlineKeyboardButton("Часто задаваемые вопросы", callback_data='faq'),
        InlineKeyboardButton("О нас", callback_data='about_us'),
        InlineKeyboardButton("Наш Адрес", callback_data='delivery_address'),  # Изменено на "Адрес доставки в Оше"
    )
    keyboard.add(
        InlineKeyboardButton("Запрещённые товары", callback_data='forbidden_goods'),
        InlineKeyboardButton("График работы", callback_data='working_hours')
    )
    await message.reply("Выберите раздел или воспользуйтесь другими функциями:", reply_markup=keyboard)

# Новый обработчик для раздела 'Приложения'
@dp.callback_query_handler(lambda c: c.data == 'applications')
async def applications(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Pinduoduo", callback_data='pinduoduo_application'),
        InlineKeyboardButton("Taobao", callback_data='taobao_application'),
        InlineKeyboardButton("Назад", callback_data='back_to_main_menu')
    )
    await bot.send_message(callback_query.from_user.id, "Выберите приложение:", reply_markup=keyboard)


# Обработчик для кнопки "Приложения"
@dp.callback_query_handler(lambda c: c.data == 'applications')
async def applications(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Pinduoduo", callback_data='pinduoduo_application'),
        InlineKeyboardButton("Taobao", callback_data='taobao_application')
    )
    keyboard.add(
        InlineKeyboardButton("Назад", callback_data='back_to_main_menu')
    )
    await bot.send_message(callback_query.from_user.id, "Выберите приложение:", reply_markup=keyboard)

# Обработчик для кнопки "Taobao"
@dp.callback_query_handler(lambda c: c.data == 'taobao_application')
async def taobao_application(callback_query: types.CallbackQuery):
    photo_path = "C:/path/to/your/image/Изображение WhatsApp 2023-06-06 в 19.05.19.jpg"
    caption = "Инструкция для покупок в Taobao:\n\n1. Зарегистрируйтесь на Taobao.\n2. Найдите товар.\n3. Добавьте товар в корзину.\n4. Оплатите товар.\n5. Укажите наш склад в качестве адреса доставки."
    await bot.send_photo(callback_query.from_user.id, photo=open(photo_path, 'rb'), caption=caption)
    await send_main_menu(callback_query.message)  # Вернуться в главное меню после отправки фото

# Обработчик для кнопки "Pinduoduo"
@dp.callback_query_handler(lambda c: c.data == 'pinduoduo_application')
async def pinduoduo_application(callback_query: types.CallbackQuery):
    photo_path = "C:/path/to/your/image/Изображение WhatsApp 2023-06-06 в 19.05.19.jpg"
    caption = "Инструкция для покупок в Pinduoduo:\n\n1. Зарегистрируйтесь на Pinduoduo.\n2. Найдите товар.\n3. Добавьте товар в корзину.\n4. Оплатите товар.\n5. Укажите наш склад в качестве адреса доставки."
    await bot.send_photo(callback_query.from_user.id, photo=open(photo_path, 'rb'), caption=caption)
    await send_main_menu(callback_query.message)  # Вернуться в главное меню после отправки фото

# Новый обработчик для кнопки 'График работы'
@dp.callback_query_handler(lambda c: c.data == 'working_hours')
async def working_hours(callback_query: types.CallbackQuery):
    working_hours_message = "Наш график работы:\n\n" \
                            "Понедельник - Пятница: 10:00 - 21:00\n" \
                            "Суббота - Воскресенье: Выходной\n\n" \
                            "Будем рады видеть вас в рабочее время!"
    await bot.send_message(callback_query.from_user.id, working_hours_message)
    await send_main_menu(callback_query.message)  # Вернуться в главное меню после отправки сообщения

# Новый обработчик для кнопки 'Запрещённые товары'
@dp.callback_query_handler(lambda c: c.data == 'forbidden_goods')
async def forbidden_goods(callback_query: types.CallbackQuery):
    forbidden_goods_message = "🚫 Запрещённые товары:\n\n" \
                             "1. Любые порошки\n" \
                             "2. Винные этикетки и пробки\n" \
                             "3. Жидкости\n" \
                             "4. Спиртные бутылки\n" \
                             "5. Химические жидкости\n" \
                             "6. Взрывоопасные вещества\n" \
                             "7. Батарейки (аккумуляторы)\n" \
                             "8. Оружие (ножи)\n" \
                             "9. Лекарства, наркотические вещества\n" \
                             "10. Горючие смазочные материалы\n" \
                             "11. Электронные сигареты\n" \
                             "12. Животные, растения (фрукты)\n" \
                             "13. Дроны\n\n" \
                             """❗Если вы отправите запрещенные товары не сообщив нам то китайская сторона взимает товар без возврата товара и денег.
❗Если ваш груз стоит дорого или больше 10кг или же габаритный  без нашего уведомление не отправляйте.
 ❗минимальный вес перевоски 100грам, эсли ваш товар менше 100грамма то считается как 100грам. И все товары считаем по отдельности.
 
📌💯ВАЖНО
📣МЫ НЕ НЕСЁМ ОТВЕТСТВЕННОСТЬ ЗА Запрещенных товаров❗❗❗ 
""" \
                             "Если у вас возникли вопросы или вам нужна дополнительная информация, свяжитесь с нашим менеджером."
    await bot.send_message(callback_query.from_user.id, forbidden_goods_message)
    await send_main_menu(callback_query.message)  # Вернуться в главное меню после отправки сообщения

# Новый обработчик для кнопок FAQ
@dp.callback_query_handler(lambda c: c.data == 'faq')
async def faq_menu(callback_query: types.CallbackQuery):
    faq_keyboard = InlineKeyboardMarkup()
    faq_keyboard.add(
        InlineKeyboardButton("Как оформить доставку?", callback_data='faq_how_to_ship'),
        InlineKeyboardButton("Сколько стоит доставка?", callback_data='faq_shipping_cost'),
    )
    faq_keyboard.add(
        InlineKeyboardButton("Как отследить посылку?", callback_data='faq_track_package'),
        InlineKeyboardButton("Как изменить адрес доставки?", callback_data='faq_change_address'),
    )
    faq_keyboard.add(
        InlineKeyboardButton("Моя посылка не пришла, что делать?", callback_data='faq_package_not_arrived')
    )
    faq_keyboard.add(
        InlineKeyboardButton("Назад", callback_data='back_to_main_menu')  # Кнопка "Назад"
    )
    await bot.send_message(callback_query.from_user.id, "Выберите интересующий вопрос:", reply_markup=faq_keyboard)

# Новый обработчик для кнопки "Назад" в меню часто задаваемых вопросов
@dp.callback_query_handler(lambda c: c.data == 'back_to_main_menu')
async def back_to_main_menu(callback_query: types.CallbackQuery):
    await send_main_menu(callback_query.message)

# Новый обработчик для кнопок FAQ
@dp.callback_query_handler(lambda c: c.data.startswith('faq_'))
async def handle_faq(callback_query: types.CallbackQuery):
    faq_answers = {
        'faq_how_to_ship': "Для оформления доставки вам необходимо...",
        'faq_shipping_cost': "Чтобы узнать стоимость доставки, пожалуйста...",
        'faq_track_package': "Для отслеживания вашей посылки воспользуйтесь...",
        'faq_change_address': "Чтобы изменить адрес доставки, необходимо...",
        'faq_package_not_arrived': "Если ваша посылка не дошла, вам следует..."
    }

    answer_key = callback_query.data
    if answer_key in faq_answers:
        await bot.send_message(callback_query.from_user.id, faq_answers[answer_key])
    else:
        await bot.send_message(callback_query.from_user.id, "Извините, ответ на этот вопрос временно недоступен.")

    await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(lambda c: c.data == 'delivery_address')
async def delivery_address(callback_query: types.CallbackQuery):
    delivery_address = "Наш Адрес в Оше:\n211 Курманжан-Датка ул."
    latitude = 40.5274000  # Примерные координаты для Курманжан-Датка ул. в Оше
    longitude = 72.7946000
    await bot.send_location(callback_query.from_user.id, latitude, longitude)
    await bot.send_message(callback_query.from_user.id, delivery_address)
    await send_main_menu(callback_query.message)  # Вернуться в главное меню после отправки адреса

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
