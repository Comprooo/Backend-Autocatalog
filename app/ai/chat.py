import httpx
import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.services.car_service import car_service
from app.services.schedule_service import schedule_service
from app.services.available_slot_service import available_slot_service
from app.models.user import User
from app.models.chat import ChatHistory

OLLAMA_URL = "http://ollama:11434/api/chat"
MODEL_NAME = "qwen2.5:1.5b" 
MAX_HISTORY = 10

class AIChatService:
    async def _get_or_create_history(self, session_id: str, user_id: any) -> ChatHistory:
        history = await ChatHistory.find_one(ChatHistory.session_id == session_id)
        if not history:
            history = ChatHistory(session_id=session_id, user_id=user_id, messages=[])
            await history.insert()
        return history

    async def _add_to_history(self, session_id: str, user_id: any, role: str, content: str):
        history = await self._get_or_create_history(session_id, user_id)
        clean_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        history.messages.append({"role": role, "content": clean_content})
        if len(history.messages) > MAX_HISTORY:
            history.messages = history.messages[-MAX_HISTORY:]
        history.updated_at = datetime.now(timezone.utc)
        await history.save()

    async def _call_ollama(self, messages: list, timeout: float = 60.0) -> str:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(OLLAMA_URL, json={
                    "model": MODEL_NAME,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.2} # Low temperature for more consistent JSON/logic
                }, timeout=timeout)
                data = res.json()
                content = data.get("message", {}).get("content", "")
                return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        except Exception as e:
            print(f"Ollama Error: {e}")
            return ""

    async def get_response(self, message: str, user: User, session_id: str = "default") -> dict:
        # 1. Get History
        history_doc = await self._get_or_create_history(session_id, user.id)
        history_messages = history_doc.messages

        # 2. STEP 1: NLU - Extract Intent and Entities
        nlu_prompt = f"""Kamu adalah NLU Parser untuk Showroom Mobil. Tugasmu mengekstrak niat (intent) dan parameter dari pesan user.
Waktu sekarang: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

INTENT yang tersedia:
- SEARCH_CAR: Mencari mobil (params: brand, min_price, max_price, transmission, type)
- GET_SLOTS: Mencari jadwal kosong (params: location_id, date)
- CREATE_BOOKING: Membuat janji temu/booking (params: car_id, slot_id, notes)
- CANCEL_BOOKING: Membatalkan jadwal (params: schedule_id)
- MY_BOOKINGS: Melihat daftar janji temu milik user saat ini
- GENERAL: Tanya jawab umum

Pesan User: "{message}"

OUTPUT HARUS JSON SAJA:
{{"intent": "INTENT_NAME", "params": {{...}}}}"""

        nlu_response = await self._call_ollama([{"role": "system", "content": nlu_prompt}])
        
        try:
            json_match = re.search(r'\{.*\}', nlu_response, re.DOTALL)
            nlu_data = json.loads(json_match.group(0)) if json_match else {"intent": "GENERAL", "params": {}}
        except:
            nlu_data = {"intent": "GENERAL", "params": {}}

        intent = nlu_data.get("intent", "GENERAL")
        params = nlu_data.get("params", {})

        # 3. STEP 2: Execution & Context Gathering
        context = ""
        car_recommendations = []
        
        try:
            if intent == "SEARCH_CAR":
                brand = params.get("brand")
                max_price = params.get("max_price")
                if isinstance(max_price, str):
                    if "juta" in max_price: max_price = int(max_price.replace("juta", "").strip()) * 1000000
                    elif "jt" in max_price: max_price = int(max_price.replace("jt", "").strip()) * 1000000

                cars, _ = await car_service.get_all_cars(
                    page=1, limit=5, brand=brand, max_price=max_price,
                    transmission=params.get("transmission"), car_type=params.get("type")
                )
                
                if cars:
                    context = "Mobil ditemukan:\n" + "\n".join([f"- {c.brand} {c.model} (ID: {c.id}) - Rp {c.price:,.0f}" for c in cars])
                    for c in cars:
                        car_recommendations.append({
                            "car_id": str(c.id), "brand": c.brand, "model": c.model,
                            "price": c.price, "thumbnail_url": c.images[0] if c.images else ""
                        })
                else:
                    context = "Tidak ada mobil ditemukan."

            elif intent == "GET_SLOTS":
                slots = await available_slot_service.get_available_slots(
                    location_id=params.get("location_id"),
                    slot_date=params.get("date")
                )
                if slots:
                    context = "Slot tersedia:\n" + "\n".join([f"- ID: {s.slot_id} | {s.location.location_name if s.location else ''} | {s.date} {s.time}" for s in slots[:5]])
                else:
                    context = "Tidak ada slot jadwal tersedia saat ini."

            elif intent == "MY_BOOKINGS":
                from app.schemas.schedule import ScheduleFilter
                my_schedules = await schedule_service.get_user_schedules(user, ScheduleFilter())
                if my_schedules:
                    context = "Jadwal Anda saat ini:\n" + "\n".join([f"- ID: {s.id} | Mobil: {s.car.brand} {s.car.model} | Status: {s.status} | Waktu: {s.date} {s.time}" for s in my_schedules])
                else:
                    context = "Anda belum memiliki jadwal janji temu."

            elif intent == "CREATE_BOOKING":
                car_id = params.get("car_id")
                slot_id = params.get("slot_id")
                if car_id and slot_id:
                    from app.schemas.schedule import ScheduleCreate
                    new_booking = await schedule_service.create_schedule(user, ScheduleCreate(
                        car_id=car_id, slot_id=slot_id, notes=params.get("notes", "Booking via AI")
                    ))
                    context = f"BERHASIL! Janji temu telah dibuat. ID Jadwal: {new_booking.id}. Status: {new_booking.status}."
                else:
                    context = "Gagal membuat janji. Saya butuh car_id dan slot_id. Tolong berikan ID tersebut atau tanyakan stok mobil/slot jadwal dulu."

            elif intent == "CANCEL_BOOKING":
                schedule_id = params.get("schedule_id")
                if schedule_id:
                    success = await schedule_service.cancel_schedule(user, schedule_id)
                    context = "BERHASIL! Jadwal tersebut telah dibatalkan." if success else "Gagal membatalkan. Pastikan ID Jadwal benar dan itu milik Anda."
                else:
                    context = "Tolong berikan ID Jadwal yang ingin dibatalkan. Anda bisa tanya 'apa jadwal saya' untuk melihat ID-nya."

        except Exception as e:
            context = f"Terjadi kesalahan saat memproses permintaan: {str(e)}"

        # 4. STEP 3: Generate Final Response

        # 4. STEP 3: Generate Final Response
        system_prompt = f"""Kamu adalah Showroom AI, asisten virtual proaktif di Dealer Mobil Premium.
Nama Customer: {user.username}
Role Customer: {user.role}

KONTEN REAL-TIME (Gunakan data ini):
{context}

TUGAS:
1. Berikan jawaban yang ramah, profesional, dan informatif.
2. Jika ada data mobil, sebutkan kelebihannya secara singkat.
3. Jika tidak ada mobil yang cocok, sarankan unit lain atau tanya admin.
4. Jangan mengarang data yang tidak ada di KONTEN REAL-TIME."""

        messages = [{"role": "system", "content": system_prompt}] + history_messages + [{"role": "user", "content": message}]
        reply = await self._call_ollama(messages)
        if not reply:
            reply = "Maaf, saya sedang mengalami kendala teknis. Ada yang bisa saya bantu secara manual?"

        # 5. Save History
        await self._add_to_history(session_id, user.id, "user", message)
        await self._add_to_history(session_id, user.id, "assistant", reply)

        return {
            "reply": reply,
            "car_recommendations": car_recommendations
        }

ai_chat_service = AIChatService()
