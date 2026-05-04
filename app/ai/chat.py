import httpx
import json
import re
from datetime import datetime, timezone
from app.services.car_service import car_service
from app.models.user import User
from app.models.chat import ChatHistory

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:1.5b" # Menggunakan Qwen 2.5 1.5B yang lebih stabil dan cepat
MAX_HISTORY = 10

SCHEDULE_KEYWORDS = [
    "jadwal", "janjian", "janji", "ketemu", "bertemu", "temu",
    "appointment", "schedule", "booking", "book", "pesan jadwal",
    "konsultasi", "kunjungan", "visit", "datang", "test drive"
]

CAR_KEYWORDS = [
    "mobil", "car", "kendaraan", "budget", "harga", "juta", "jt",
    "cari", "rekomendasi", "recommend", "murah", "mahal",
    "mpv", "suv", "sedan", "hatchback", "matic", "manual"
]


class AIChatService:
    async def _get_or_create_history(self, session_id: str, user_id: any) -> ChatHistory:
        """Ambil atau buat history percakapan dari MongoDB."""
        history = await ChatHistory.find_one(ChatHistory.session_id == session_id)
        if not history:
            history = ChatHistory(session_id=session_id, user_id=user_id, messages=[])
            await history.insert()
        return history

    async def _add_to_history(self, session_id: str, user_id: any, role: str, content: str):
        """Tambah pesan ke history di MongoDB."""
        history = await self._get_or_create_history(session_id, user_id)
        
        # Bersihkan content dari tag <think> jika ada (khas DeepSeek R1)
        clean_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        
        history.messages.append({"role": role, "content": clean_content})
        
        # Simpan hanya MAX_HISTORY pesan terakhir
        if len(history.messages) > MAX_HISTORY:
            history.messages = history.messages[-MAX_HISTORY:]
            
        history.updated_at = datetime.now(timezone.utc)
        await history.save()

    def _detect_intent(self, message: str) -> str:
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in SCHEDULE_KEYWORDS):
            return "schedule"
        elif any(kw in msg_lower for kw in CAR_KEYWORDS):
            return "search_car"
        return "general"

    async def _call_ollama(self, system_prompt: str, messages: list, timeout: float = 60.0) -> str:
        """Panggil Ollama Chat API dengan format messages."""
        try:
            all_messages = [{"role": "system", "content": system_prompt}] + messages
            async with httpx.AsyncClient() as client:
                res = await client.post(OLLAMA_URL, json={
                    "model": MODEL_NAME,
                    "messages": all_messages,
                    "stream": False
                }, timeout=timeout)
                data = res.json()
                content = data.get("message", {}).get("content", "Maaf, saya gagal merangkai jawaban.")
                
                # DeepSeek R1 sering menyertakan proses berpikir di dalam <think>...</think>
                # Kita hapus agar tidak tampil di UI chat user, tapi tetap tersimpan di logs jika perlu
                reply = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                return reply
        except Exception as e:
            print(f"Ollama Error: {e}")
            return "Maaf, ada gangguan koneksi ke server AI."

    async def _handle_search_car(self, message: str, user: User, history_messages: list) -> dict:
        max_price = None
        juta_match = re.search(r'(\d+)\s*(juta|jt)', message.lower())
        if juta_match:
            max_price = int(juta_match.group(1)) * 1000000
        else:
            num_match = re.search(r'(\d{3,}(?:\.\d{3})*)', message)
            if num_match:
                val = num_match.group(1).replace('.', '')
                if len(val) >= 7:
                    max_price = int(val)

        if max_price:
            cars, _ = await car_service.get_all_cars(page=1, limit=5, max_price=max_price)
        else:
            cars, _ = await car_service.get_all_cars(page=1, limit=5)

        recommendations = []
        cars_context_lines = []
        for c in cars:
            recommendations.append({
                "id": str(c.id), "brand": c.brand,
                "type": c.type, "price": c.price, "status": c.status
            })
            cars_context_lines.append(f"- {c.brand} ({c.type}): Rp {c.price:,.0f} [{c.status}]")

        cars_context = "\n".join(cars_context_lines) if cars else "Tidak ada mobil yang sesuai budget saat ini."

        system_prompt = f"""Kamu adalah asisten dealer mobil profesional. Jawablah dengan ramah dan natural.
Nama customer: {user.username}.
Data stok mobil terbaru kami:
{cars_context}

INSTRUKSI:
1. Gunakan data stok di atas sebagai referensi utama.
2. Jika mobil yang dicari tidak ada atau budget tidak cukup, sarankan mobil lain yang mendekati.
3. JANGAN mengarang mobil yang tidak ada di stok.
4. Jawab langsung ke inti pertanyaan dengan gaya bahasa yang sopan."""

        reply = await self._call_ollama(system_prompt, history_messages + [{"role": "user", "content": message}])
        return {"reply": reply, "car_recommendations": recommendations}

    async def _handle_schedule(self, message: str, user: User, history_messages: list) -> dict:
        cars, _ = await car_service.get_all_cars(page=1, limit=10, status="Tersedia")
        cars_list = [f"- {c.brand} ({c.type}): Rp {c.price:,.0f}" for c in cars]
        available_cars = "\n".join(cars_list) if cars_list else "Belum ada mobil tersedia untuk dikunjungi."

        system_prompt = f"""Kamu asisten dealer mobil. Bantu customer {user.username} menjadwalkan kunjungan atau test drive.
Mobil yang tersedia saat ini:
{available_cars}

INSTRUKSI:
1. Arahkan customer untuk memilih mobil dari daftar di atas.
2. Jelaskan bahwa jadwal harus minimal H+1.
3. Beritahu bahwa mereka bisa klik menu 'Jadwal' atau isi form yang disediakan."""

        reply = await self._call_ollama(system_prompt, history_messages + [{"role": "user", "content": message}])
        return {
            "reply": reply, "car_recommendations": [],
            "action": {
                "type": "navigate_schedule",
                "endpoint": "POST /api/v1/schedules",
                "required_fields": {"car_id": "Pilih mobil", "date": "YYYY-MM-DDTHH:MM:SS"}
            }
        }

    async def _handle_general(self, message: str, user: User, history_messages: list) -> dict:
        system_prompt = f"""Kamu adalah asisten dealer mobil ramah bernama Showroom AI. 
Kamu sedang berbicara dengan {user.username}.
Tugasmu adalah membantu informasi seputar mobil, harga, dan jadwal kunjungan."""

        reply = await self._call_ollama(system_prompt, history_messages + [{"role": "user", "content": message}])
        return {"reply": reply, "car_recommendations": []}

    async def get_response(self, message: str, user: User, session_id: str = "default") -> dict:
        # 1. Ambil history dari DB
        history_doc = await self._get_or_create_history(session_id, user.id)
        history_messages = history_doc.messages

        # 2. Deteksi Intent
        intent = self._detect_intent(message)
        
        # 3. Proses berdasarkan Intent
        if intent == "search_car":
            result = await self._handle_search_car(message, user, history_messages)
        elif intent == "schedule":
            result = await self._handle_schedule(message, user, history_messages)
        else:
            result = await self._handle_general(message, user, history_messages)

        # 4. Simpan ke history DB (Pesan User & Balasan AI)
        await self._add_to_history(session_id, user.id, "user", message)
        await self._add_to_history(session_id, user.id, "assistant", result["reply"])
        
        return result

ai_chat_service = AIChatService()
