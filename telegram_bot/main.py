import os
import sys
from pathlib import Path
import django
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hbold
from aiogram import Router
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from dotenv import load_dotenv  # ✅ .env yuklash

# 📌 .env faylni yuklash
load_dotenv()

# Django sozlamalari
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic.settings')
django.setup()

from app.models import User, Customer, Meeting
from app2.models import CustomerDebt

# Telegram bot sozlamalari
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
router = Router()

# State klasslari
class LoginState(StatesGroup):
    username = State()
    password = State()

# Start komandasi
@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Assalomu alaykum! 👋\n\nShifokor/Admin uchun: /login\nBemor uchun: /patient"
    )

# Login komandasi
@router.message(Command("login"))
async def login(message: Message, state: FSMContext):
    await message.answer("Loginni kiriting:")
    await state.set_state(LoginState.username)

@router.message(LoginState.username)
async def get_username(message: Message, state: FSMContext):
    await state.update_data(username=message.text)
    await message.answer("Parolni kiriting:")
    await state.set_state(LoginState.password)

@router.message(LoginState.password)
async def get_password(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data.get("username")
    password = message.text

    # Userni sync_to_async bilan olish
    user = await sync_to_async(lambda: User.objects.filter(username=username).first())()
    if user and await sync_to_async(user.check_password)(password):
        await message.answer(
            f"Xush kelibsiz, {hbold(user.get_full_name())}!\nSizning rolingiz: {user.get_role_display()}"
        )

        # Doktorning meetinglarini olish
        meetings = await sync_to_async(lambda: list(
            Meeting.objects.filter(doctor=user).select_related('customer')
        ))()
        if meetings:
            msg = "Sizning qabullaringiz:\n"
            for m in meetings:
                msg += f"{m.date}: {m.customer.full_name}\n"
            await message.answer(msg)
        else:
            await message.answer("Sizda hech qanday qabullar mavjud emas.")
    else:
        await message.answer("Login yoki parol xato.")
    await state.clear()


# Bemor uchun passport ID orqali
@router.message(Command("patient"))
async def patient(message: Message):
    await message.answer("Passport ID ni kiriting:")

@router.message(F.text.startswith("passport:"))
async def process_passport(message: Message):
    passport_id = message.text.replace("passport:", "").strip()

    # Django ORM chaqiruvini asinxron qilish
    customer = await sync_to_async(Customer.objects.filter)(passport_id=passport_id).afirst()
    if customer:
        msg = f"Ism: {customer.full_name}\nTelefon: {customer.phone_number}\n"
        meetings = await sync_to_async(Meeting.objects.filter)(customer=customer)
        msg += "Qabullar:\n"
        for m in meetings:
            debt_obj = await sync_to_async(CustomerDebt.objects.filter)(meeting=m, customer=customer).afirst()
            debt = 0
            if debt_obj:
                dental_services = await sync_to_async(list)(m.dental_services.all())
                debt = sum([ds.amount for ds in dental_services]) - debt_obj.amount_paid - debt_obj.discount
            msg += f"{m.date}: Qarzdorlik: {debt}\n"
        await message.answer(msg)
    else:
        await message.answer("Bunday bemor topilmadi.")

# Xabarnomalar komandasi
@router.message(Command("notifications"))
async def notifications(message: Message):
    await message.answer("Sizga kelgan xabarnomalar: ...")

# Routerni dispatcherga qo‘shish
dp.include_router(router)

# Botni ishga tushirish
if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))