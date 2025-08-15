import os
import sys
from pathlib import Path
import django
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hbold, hcode
from aiogram import Router
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from dotenv import load_dotenv
from datetime import datetime
import math

# 📌 .env faylni yuklash
load_dotenv()

# Django sozlamalari
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic.settings')
django.setup()

from app.models import User, Customer, Meeting, DentalService
from app2.models import CustomerDebt

# Telegram bot sozlamalari
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
router = Router()

class StaffLoginState(StatesGroup):
    username = State()
    password = State()

class PatientLoginState(StatesGroup):
    passport_id = State()

user_sessions = {}
MEETINGS_PER_PAGE = 5

@router.message(Command("start"))
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍⚕️ Shifokor/Admin/Direktor", callback_data="staff_login")],
        [InlineKeyboardButton(text="🏥 Bemor", callback_data="patient_login")],
        [InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help")]
    ])
    
    await message.answer(
        "🏥 <b>Klinika CRM Telegram Bot</b>\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    help_text = (
        "📋 <b>Bot haqida ma'lumot:</b>\n\n"
        "👨‍⚕️ <b>Shifokor uchun:</b>\n"
        "• O'z qabullarini ko'rish\n"
        "• Qabul tafsilotlarini ko'rish\n\n"
        "👨‍💼 <b>Admin/Direktor uchun:</b>\n"
        "• Barcha qabullarni ko'rish\n"
        "• Barcha bemorlarni ko'rish\n\n"
        "🏥 <b>Bemor uchun:</b>\n"
        "• O'z qabullarini ko'rish\n"
        "• Xizmat narxlari va qarzlarni ko'rish\n\n"
        "Bosh menyuga qaytish uchun /start ni bosing."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_start")]
    ])
    
    await callback.message.edit_text(help_text, reply_markup=keyboard)

@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍⚕️ Shifokor/Admin/Direktor", callback_data="staff_login")],
        [InlineKeyboardButton(text="🏥 Bemor", callback_data="patient_login")],
        [InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help")]
    ])
    
    await callback.message.edit_text(
        "🏥 <b>Klinika CRM Telegram Bot</b>\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "staff_login")
async def staff_login_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("👤 <b>Username</b> ni kiriting:")
    await state.set_state(StaffLoginState.username)

@router.callback_query(F.data == "patient_login")
async def patient_login_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🆔 <b>Passport ID</b> ni kiriting:")
    await state.set_state(PatientLoginState.passport_id)

@router.message(StaffLoginState.username)
async def get_staff_username(message: Message, state: FSMContext):
    await state.update_data(username=message.text)
    await message.answer("🔐 <b>Parol</b>ni kiriting:")
    await state.set_state(StaffLoginState.password)

@router.message(StaffLoginState.password)
async def get_staff_password(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data.get("username")
    password = message.text

    loading_msg = await message.answer("⏳ <b>Tekshirilmoqda...</b>")

    user = await sync_to_async(lambda: User.objects.filter(username=username).first())()
    if user and await sync_to_async(user.check_password)(password):
        user_sessions[message.from_user.id] = {
            'user_id': user.id,
            'role': user.role,
            'full_name': user.get_full_name()
        }
        
        if user.role == 'doctor':
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📅 Mening qabullarim", callback_data="my_meetings")]
            ])
        else:  # admin or director
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📅 Barcha qabullar", callback_data="all_meetings")],
                [InlineKeyboardButton(text="👥 Barcha bemorlar", callback_data="all_patients")]
            ])
        
        await loading_msg.delete()
        await message.answer(
            f"✅ <b>Xush kelibsiz, {hbold(user.get_full_name())}!</b>\n"
            f"📋 Sizning rolingiz: <b>{user.get_role_display()}</b>",
            reply_markup=keyboard
        )
    else:
        await loading_msg.delete()
        await message.answer("❌ <b>Login yoki parol xato!</b>\n\nQaytadan urinish uchun /start ni bosing.")
    
    await state.clear()

@router.message(PatientLoginState.passport_id)
async def get_patient_passport(message: Message, state: FSMContext):
    passport_id = message.text.strip()
    
    loading_msg = await message.answer("⏳ <b>Tekshirilmoqda...</b>")
    
    customer = await sync_to_async(lambda: Customer.objects.filter(passport_id=passport_id).first())()
    if customer:
        user_sessions[message.from_user.id] = {
            'customer_id': customer.id,
            'role': 'patient',
            'full_name': customer.full_name
        }
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Mening qabullarim", callback_data="patient_meetings")],
            [InlineKeyboardButton(text="💰 Qarzlarim", callback_data="patient_debts")]
        ])
        
        await loading_msg.delete()
        await message.answer(
            f"✅ <b>Xush kelibsiz, {hbold(customer.full_name)}!</b>\n"
            f"📞 Telefon: {customer.phone_number}",
            reply_markup=keyboard
        )
    else:
        await loading_msg.delete()
        await message.answer("❌ <b>Bunday passport ID bilan bemor topilmadi!</b>\n\nQaytadan urinish uchun /start ni bosing.")
    
    await state.clear()

@router.callback_query(F.data.startswith("my_meetings"))
async def doctor_meetings(callback: CallbackQuery):
    user_session = user_sessions.get(callback.from_user.id)
    if not user_session or user_session['role'] != 'doctor':
        await callback.answer("❌ Ruxsat yo'q!")
        return
    
    page = 1
    if ":" in callback.data:
        page = int(callback.data.split(":")[1])
    
    user = await sync_to_async(lambda: User.objects.get(id=user_session['user_id']))()
    meetings = await sync_to_async(lambda: list(
        Meeting.objects.filter(doctor=user, branch=user.branch)
        .select_related('customer', 'room')
        .order_by('-date')
    ))()
    
    if not meetings:
        await callback.message.edit_text(
            "📅 <b>Sizda hech qanday qabullar mavjud emas.</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
            ])
        )
        return
    
    total_pages = math.ceil(len(meetings) / MEETINGS_PER_PAGE)
    start_idx = (page - 1) * MEETINGS_PER_PAGE
    end_idx = start_idx + MEETINGS_PER_PAGE
    page_meetings = meetings[start_idx:end_idx]
    
    keyboard_buttons = []
    text = f"📅 <b>Mening qabullarim</b> (Sahifa {page}/{total_pages})\n\n"
    
    for i, meeting in enumerate(page_meetings, start=start_idx + 1):
        meeting_date = meeting.date.strftime("%d.%m.%Y %H:%M")
        text += f"{i}. {meeting.customer.full_name} - {meeting_date}\n"
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"👁️ {meeting.customer.full_name} - {meeting_date}",
                callback_data=f"meeting_detail:{meeting.id}"
            )
        ])
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"my_meetings:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"my_meetings:{page+1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("meeting_detail:"))
async def meeting_detail(callback: CallbackQuery):
    meeting_id = int(callback.data.split(":")[1])
    
    meeting = await sync_to_async(lambda: Meeting.objects.select_related(
        'customer', 'doctor', 'room'
    ).prefetch_related('dental_services').get(id=meeting_id))()
    
    dental_services = await sync_to_async(list)(meeting.dental_services.all())
    total_service_cost = sum(service.amount for service in dental_services)
    
    debt_obj = await sync_to_async(lambda: CustomerDebt.objects.filter(
        meeting=meeting, customer=meeting.customer
    ).first())()
    
    amount_paid = debt_obj.amount_paid if debt_obj else 0
    discount = debt_obj.discount if debt_obj else 0
    remaining_debt = total_service_cost - amount_paid - discount
    
    meeting_date = meeting.date.strftime("%d.%m.%Y %H:%M")
    text = (
        f"📋 <b>Qabul tafsilotlari</b>\n\n"
        f"👤 <b>Bemor:</b> {meeting.customer.full_name}\n"
        f"📞 <b>Telefon:</b> {meeting.customer.phone_number}\n"
        f"🆔 <b>Passport:</b> {meeting.customer.passport_id}\n"
        f"📅 <b>Sana:</b> {meeting_date}\n"
        f"🏥 <b>Xona:</b> {meeting.room.name}\n"
        f"📊 <b>Status:</b> {meeting.get_status_display()}\n"
        f"🩺 <b>Tashxis:</b> {meeting.diognosis or 'Kiritilmagan'}\n"
        f"💬 <b>Izoh:</b> {meeting.comment or 'Yo\'q'}\n\n"
        f"💰 <b>Moliyaviy ma'lumotlar:</b>\n"
        f"💵 Jami xizmat narxi: {total_service_cost:,.0f} so'm\n"
        f"💳 To'langan: {amount_paid:,.0f} so'm\n"
        f"🎁 Chegirma: {discount:,.0f} so'm\n"
        f"💸 Qarz: {remaining_debt:,.0f} so'm\n\n"
    )
    
    if dental_services:
        text += "🦷 <b>Xizmatlar:</b>\n"
        for service in dental_services:
            text += f"• {service.name} - {service.amount:,.0f} so'm\n"
    
    user_session = user_sessions.get(callback.from_user.id)
    if user_session and user_session['role'] in ['admin', 'director']:
        back_callback = "all_meetings"
    else:
        back_callback = "my_meetings"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Qabullarga qaytish", callback_data=back_callback)]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("all_meetings"))
async def all_meetings(callback: CallbackQuery):
    user_session = user_sessions.get(callback.from_user.id)
    if not user_session or user_session['role'] not in ['admin', 'director']:
        await callback.answer("❌ Ruxsat yo'q!")
        return
    
    page = 1
    if ":" in callback.data:
        page = int(callback.data.split(":")[1])
    
    user = await sync_to_async(lambda: User.objects.get(id=user_session['user_id']))()
    
    if user.role == 'director':
        # Director sees all meetings from their clinic (all branches)
        meetings = await sync_to_async(lambda: list(
            Meeting.objects.filter(branch__clinic=user.clinic)
            .select_related('customer', 'doctor', 'room')
            .order_by('-date')
        ))()
    else:  # admin
        # Admin sees only meetings from their specific branch
        meetings = await sync_to_async(lambda: list(
            Meeting.objects.filter(branch=user.branch)
            .select_related('customer', 'doctor', 'room')
            .order_by('-date')
        ))()
    
    if not meetings:
        await callback.message.edit_text(
            "📅 <b>Hech qanday qabullar mavjud emas.</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
            ])
        )
        return
    
    total_pages = math.ceil(len(meetings) / MEETINGS_PER_PAGE)
    start_idx = (page - 1) * MEETINGS_PER_PAGE
    end_idx = start_idx + MEETINGS_PER_PAGE
    page_meetings = meetings[start_idx:end_idx]
    
    keyboard_buttons = []
    text = f"📅 <b>Barcha qabullar</b> (Sahifa {page}/{total_pages})\n\n"
    
    for i, meeting in enumerate(page_meetings, start=start_idx + 1):
        meeting_date = meeting.date.strftime("%d.%m.%Y %H:%M")
        text += f"{i}. {meeting.customer.full_name} - Dr.{meeting.doctor.get_full_name()} - {meeting_date}\n"
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"👁️ {meeting.customer.full_name} - {meeting_date}",
                callback_data=f"meeting_detail:{meeting.id}"
            )
        ])
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"all_meetings:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"all_meetings:{page+1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("all_patients"))
async def all_patients(callback: CallbackQuery):
    user_session = user_sessions.get(callback.from_user.id)
    if not user_session or user_session['role'] not in ['admin', 'director']:
        await callback.answer("❌ Ruxsat yo'q!")
        return
    
    page = 1
    if ":" in callback.data:
        page = int(callback.data.split(":")[1])
    
    user = await sync_to_async(lambda: User.objects.get(id=user_session['user_id']))()
    
    if user.role == 'director':
        # Director sees all customers from their clinic (all branches)
        customers = await sync_to_async(lambda: list(
            Customer.objects.filter(branch__clinic=user.clinic).order_by('full_name')
        ))()
    else:  # admin
        # Admin sees only customers from their specific branch
        customers = await sync_to_async(lambda: list(
            Customer.objects.filter(branch=user.branch).order_by('full_name')
        ))()
    
    if not customers:
        await callback.message.edit_text(
            "👥 <b>Hech qanday bemorlar mavjud emas.</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
            ])
        )
        return
    
    total_pages = math.ceil(len(customers) / MEETINGS_PER_PAGE)
    start_idx = (page - 1) * MEETINGS_PER_PAGE
    end_idx = start_idx + MEETINGS_PER_PAGE
    page_customers = customers[start_idx:end_idx]
    
    keyboard_buttons = []
    text = f"👥 <b>Barcha bemorlar</b> (Sahifa {page}/{total_pages})\n\n"
    
    for i, customer in enumerate(page_customers, start=start_idx + 1):
        text += f"{i}. {customer.full_name} - {customer.phone_number}\n"
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"👁️ {customer.full_name}",
                callback_data=f"patient_detail:{customer.id}"
            )
        ])
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"all_patients:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"all_patients:{page+1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("patient_meetings"))
async def patient_meetings(callback: CallbackQuery):
    user_session = user_sessions.get(callback.from_user.id)
    if not user_session or user_session['role'] != 'patient':
        await callback.answer("❌ Ruxsat yo'q!")
        return
    
    page = 1
    if ":" in callback.data:
        page = int(callback.data.split(":")[1])
    
    customer = await sync_to_async(lambda: Customer.objects.get(id=user_session['customer_id']))()
    meetings = await sync_to_async(lambda: list(
        Meeting.objects.filter(customer=customer, branch=customer.branch)
        .select_related('doctor', 'room')
        .prefetch_related('dental_services')
        .order_by('-date')
    ))()
    
    if not meetings:
        await callback.message.edit_text(
            "📅 <b>Sizda hech qanday qabullar mavjud emas.</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_patient_menu")]
            ])
        )
        return
    
    total_pages = math.ceil(len(meetings) / MEETINGS_PER_PAGE)
    start_idx = (page - 1) * MEETINGS_PER_PAGE
    end_idx = start_idx + MEETINGS_PER_PAGE
    page_meetings = meetings[start_idx:end_idx]
    
    keyboard_buttons = []
    text = f"📅 <b>Mening qabullarim</b> (Sahifa {page}/{total_pages})\n\n"
    
    for i, meeting in enumerate(page_meetings, start=start_idx + 1):
        meeting_date = meeting.date.strftime("%d.%m.%Y %H:%M")
        text += f"{i}. Dr.{meeting.doctor.get_full_name()} - {meeting_date}\n"
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"👁️ {meeting_date} - Dr.{meeting.doctor.get_full_name()}",
                callback_data=f"patient_meeting_detail:{meeting.id}"
            )
        ])
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"patient_meetings:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"patient_meetings:{page+1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_patient_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("patient_meeting_detail:"))
async def patient_meeting_detail(callback: CallbackQuery):
    meeting_id = int(callback.data.split(":")[1])
    
    meeting = await sync_to_async(lambda: Meeting.objects.select_related(
        'doctor', 'room'
    ).prefetch_related('dental_services').get(id=meeting_id))()
    
    dental_services = await sync_to_async(list)(meeting.dental_services.all())
    total_service_cost = sum(service.amount for service in dental_services)
    
    debt_obj = await sync_to_async(lambda: CustomerDebt.objects.filter(
        meeting=meeting, customer=meeting.customer
    ).first())()
    
    amount_paid = debt_obj.amount_paid if debt_obj else 0
    discount = debt_obj.discount if debt_obj else 0
    remaining_debt = total_service_cost - amount_paid - discount
    
    meeting_date = meeting.date.strftime("%d.%m.%Y %H:%M")
    text = (
        f"📋 <b>Qabul ma'lumotlari</b>\n\n"
        f"👨‍⚕️ <b>Shifokor:</b> Dr.{meeting.doctor.get_full_name()}\n"
        f"📅 <b>Sana:</b> {meeting_date}\n"
        f"🏥 <b>Xona:</b> {meeting.room.name}\n"
        f"📊 <b>Status:</b> {meeting.get_status_display()}\n"
        f"🩺 <b>Tashxis:</b> {meeting.diognosis or 'Kiritilmagan'}\n"
        f"💬 <b>Izoh:</b> {meeting.comment or 'Yo\'q'}\n\n"
        f"💰 <b>Moliyaviy ma'lumotlar:</b>\n"
        f"💵 Jami xizmatlar narxi: {total_service_cost:,.0f} so'm\n"
        f"💳 Siz to'ladingiz: {amount_paid:,.0f} so'm\n"
        f"🎁 Chegirma: {discount:,.0f} so'm\n"
        f"💸 Qarzingiz: {remaining_debt:,.0f} so'm\n\n"
    )
    
    if dental_services:
        text += "🦷 <b>Olingan xizmatlar:</b>\n"
        for service in dental_services:
            text += f"• {service.name} - {service.amount:,.0f} so'm\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Qabullarga qaytish", callback_data="patient_meetings")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "patient_debts")
async def patient_debts(callback: CallbackQuery):
    user_session = user_sessions.get(callback.from_user.id)
    if not user_session or user_session['role'] != 'patient':
        await callback.answer("❌ Ruxsat yo'q!")
        return
    
    customer = await sync_to_async(lambda: Customer.objects.get(id=user_session['customer_id']))()
    meetings = await sync_to_async(lambda: list(
        Meeting.objects.filter(customer=customer, branch=customer.branch)
        .prefetch_related('dental_services')
        .order_by('-date')
    ))()
    
    total_debt = 0
    total_paid = 0
    total_services = 0
    debt_details = []
    
    for meeting in meetings:
        dental_services = await sync_to_async(list)(meeting.dental_services.all())
        service_cost = sum(service.amount for service in dental_services)
        
        debt_obj = await sync_to_async(lambda: CustomerDebt.objects.filter(
            meeting=meeting, customer=customer
        ).first())()
        
        amount_paid = debt_obj.amount_paid if debt_obj else 0
        discount = debt_obj.discount if debt_obj else 0
        meeting_debt = service_cost - amount_paid - discount
        
        total_services += service_cost
        total_paid += amount_paid
        total_debt += meeting_debt
        
        if meeting_debt > 0:
            meeting_date = meeting.date.strftime("%d.%m.%Y")
            debt_details.append(f"• {meeting_date}: {meeting_debt:,.0f} so'm")
    
    text = (
        f"💰 <b>Qarzlar bo'yicha hisobot</b>\n\n"
        f"💵 Jami xizmatlar narxi: {total_services:,.0f} so'm\n"
        f"💳 Jami to'langan: {total_paid:,.0f} so'm\n"
        f"💸 Jami qarz: {total_debt:,.0f} so'm\n\n"
    )
    
    if debt_details:
        text += "📋 <b>Qarzlar tafsiloti:</b>\n"
        text += "\n".join(debt_details[:10])  # Show max 10 debts
        if len(debt_details) > 10:
            text += f"\n... va yana {len(debt_details) - 10} ta qarz"
    else:
        text += "✅ <b>Sizda hech qanday qarz yo'q!</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_patient_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    user_session = user_sessions.get(callback.from_user.id)
    if not user_session:
        await callback.answer("❌ Sessiya tugagan!")
        return
    
    if user_session['role'] == 'doctor':
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Mening qabullarim", callback_data="my_meetings")]
        ])
    else:  # admin or director
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Barcha qabullar", callback_data="all_meetings")],
            [InlineKeyboardButton(text="👥 Barcha bemorlar", callback_data="all_patients")]
        ])
    
    await callback.message.edit_text(
        f"✅ <b>Xush kelibsiz, {user_session['full_name']}!</b>",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "back_to_patient_menu")
async def back_to_patient_menu(callback: CallbackQuery):
    user_session = user_sessions.get(callback.from_user.id)
    if not user_session or user_session['role'] != 'patient':
        await callback.answer("❌ Sessiya tugagan!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Mening qabullarim", callback_data="patient_meetings")],
        [InlineKeyboardButton(text="💰 Qarzlarim", callback_data="patient_debts")]
    ])
    
    await callback.message.edit_text(
        f"✅ <b>Xush kelibsiz, {user_session['full_name']}!</b>",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("patient_detail:"))
async def patient_detail(callback: CallbackQuery):
    user_session = user_sessions.get(callback.from_user.id)
    if not user_session or user_session['role'] not in ['admin', 'director']:
        await callback.answer("❌ Ruxsat yo'q!")
        return
    
    customer_id = int(callback.data.split(":")[1])
    
    customer = await sync_to_async(lambda: Customer.objects.select_related('branch__clinic').get(id=customer_id))()
    
    # Get customer's meetings and debt information
    meetings = await sync_to_async(lambda: list(
        Meeting.objects.filter(customer=customer)
        .select_related('doctor', 'room')
        .prefetch_related('dental_services')
        .order_by('-date')
    ))()
    
    total_debt = 0
    total_paid = 0
    total_services = 0
    meetings_count = len(meetings)
    
    for meeting in meetings:
        dental_services = await sync_to_async(list)(meeting.dental_services.all())
        service_cost = sum(service.amount for service in dental_services)
        
        debt_obj = await sync_to_async(lambda: CustomerDebt.objects.filter(
            meeting=meeting, customer=customer
        ).first())()
        
        amount_paid = debt_obj.amount_paid if debt_obj else 0
        discount = debt_obj.discount if debt_obj else 0
        meeting_debt = service_cost - amount_paid - discount
        
        total_services += service_cost
        total_paid += amount_paid
        total_debt += meeting_debt
    
    text = (
        f"👤 <b>Bemor ma'lumotlari</b>\n\n"
        f"📝 <b>F.I.O:</b> {customer.full_name}\n"
        f"📞 <b>Telefon:</b> {customer.phone_number}\n"
        f"🆔 <b>Passport ID:</b> {customer.passport_id}\n"
        f"🏥 <b>Filial:</b> {customer.branch.name}\n"
        f"🏢 <b>Klinika:</b> {customer.branch.clinic.name}\n"
        f"📅 <b>Ro'yxatdan o'tgan:</b> {customer.created_at.strftime('%d.%m.%Y')}\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"🔢 Jami qabullar: {meetings_count} ta\n"
        f"💵 Jami xizmatlar narxi: {total_services:,.0f} so'm\n"
        f"💳 Jami to'langan: {total_paid:,.0f} so'm\n"
        f"💸 Jami qarz: {total_debt:,.0f} so'm\n"
    )
    
    # if customer.address:
    #     text += f"🏠 <b>Manzil:</b> {customer.address}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Bemorlarga qaytish", callback_data="all_patients")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.message()
async def unknown_message(message: Message):
    await message.answer(
        "❓ <b>Noma'lum buyruq!</b>\n\n"
        "Bosh menyuga o'tish uchun /start ni bosing."
    )

# Routerni dispatcherga qo'shish
dp.include_router(router)

# Botni ishga tushirish
if __name__ == "__main__":
    print("🤖 Telegram bot ishga tushmoqda...")
    dp.run_polling(bot)
