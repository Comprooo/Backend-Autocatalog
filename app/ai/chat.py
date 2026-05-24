import httpx
import json
import re
import uuid
from datetime import datetime, timezone, date
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
                    "options": {"temperature": 0.2}
                }, timeout=timeout)
                data = res.json()
                content = data.get("message", {}).get("content", "")
                return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        except Exception as e:
            print(f"Ollama Error: {e}")
            return ""

    async def _retrieve_relevant_cars(self, query: str, limit: int = 4):
        query_tokens = set(re.findall(r"\w+", query.lower()))
        if not query_tokens:
            return []

        cars, _, _ = await car_service.get_all_cars(page=1, limit=100)
        scored = []
        for c in cars:
            searchable = " ".join([
                c.brand or "",
                c.model or "",
                c.description or "",
                c.car_type or "",
                c.transmission or "",
                c.fuel or "",
                " ".join(c.features or [])
            ]).lower()
            score = sum(1 for token in query_tokens if token in searchable)
            if score > 0:
                scored.append((score, c))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def _detect_response_style(self, message: str) -> str:
        text = message.lower()
        if re.search(r"\b(ringkas|singkat|padat|sekilas|cepat|to the point)\b", text):
            return "ringkas"
        if re.search(r"\b(detail|lengkap|jelas|panjang|terperinci|mendalam|komprehensif)\b", text):
            return "detail"
        if re.search(r"\b(rekomendasi|saran|pilihkan|pilihan|terbaik|favorit)\b", text):
            return "rekomendasi"
        if re.search(r"\b(cari|carikan|ada|available|tersedia|mobil|unit|harga|murah|terjangkau|budget|suv|mpv|sedan|toyota|honda|daihatsu|nissan|mitsubishi|suzuki)\b", text):
            return "rekomendasi"
        return "default"

    def _format_price(self, price: float) -> str:
        try:
            return f"Rp {float(price):,.0f}".replace(",", ".")
        except (TypeError, ValueError):
            return "Harga belum tersedia"

    def _format_car_line(self, car: Dict[str, Any], response_style: str) -> str:
        specs = car.get("specifications") or {}
        title = f"{car.get('brand', '')} {car.get('model', '')}".strip()
        price = self._format_price(car.get("price", 0))
        status = car.get("status") or "-"

        if response_style == "ringkas":
            return f"- {title} - {price} ({status})"

        details = [
            str(specs.get("year") or "").strip(),
            str(specs.get("type") or "").strip(),
            str(specs.get("transmission") or "").strip(),
            str(specs.get("fuel") or "").strip(),
        ]
        details = [item for item in details if item]
        line = f"- {title} - {price} | {status}"
        if details:
            line += f" | {' | '.join(details)}"

        features = car.get("features") or []
        if response_style == "detail" and features:
            line += f"\n  Fitur utama: {', '.join(features[:5])}"

        return line

    def _build_data_reply(
        self,
        context: str,
        car_recommendations: List[Dict[str, Any]],
        response_style: str,
        has_retrieval_data: bool,
    ) -> str:
        if car_recommendations:
            return "Berikut data yang saya temukan sesuai permintaan Anda."

        blocked_contexts = {
            "",
            "Gunakan informasi inventaris relevan dan riwayat pengguna untuk menjawab.",
            "Tidak ada data mobil yang relevan ditemukan dari inventaris saat ini.",
        }
        if context and context not in blocked_contexts:
            return context

        if has_retrieval_data:
            return "Saya menemukan data terkait request Anda, tetapi belum bisa menyusunnya dengan lengkap. Silakan lihat rekomendasi unit yang muncul di bawah ini."

        return "Maaf, saya belum menemukan data yang sesuai. Coba sebutkan brand, tipe mobil, atau batas harga yang Anda inginkan."

    def _rule_detect_car_search(self, message: str) -> dict | None:
        text = message.lower()
        search_patterns = [
            r"\b(tampilkan|lihat|cari|carikan|ada|available|tersedia|rekomendasi|saran)\b.*\b(mobil|unit|kendaraan)\b",
            r"\b(mobil|unit|kendaraan)\b.*\b(apa|mana|tersedia|available|murah|terjangkau|harga|budget)\b",
            r"\b(suv|mpv|sedan|hatchback|city car|pickup)\b",
            r"\b(toyota|honda|daihatsu|nissan|mitsubishi|suzuki|hyundai|mazda|bmw|mercedes|wuling)\b",
        ]
        if not any(re.search(pattern, text) for pattern in search_patterns):
            return None

        params: Dict[str, Any] = {}

        brands = [
            "toyota", "honda", "daihatsu", "nissan", "mitsubishi",
            "suzuki", "hyundai", "mazda", "bmw", "mercedes", "wuling"
        ]
        for brand in brands:
            if re.search(rf"\b{brand}\b", text):
                params["brand"] = brand.title()
                break

        car_types = ["suv", "mpv", "sedan", "hatchback", "city car", "pickup"]
        for car_type in car_types:
            if re.search(rf"\b{re.escape(car_type)}\b", text):
                params["type"] = car_type.upper()
                break

        if re.search(r"\bmanual\b", text):
            params["transmission"] = "Manual"
        elif re.search(r"\b(matic|automatic|otomatis)\b", text):
            params["transmission"] = "Automatic"

        price_match = re.search(r"(?:di\s*bawah|dibawah|maks(?:imal)?|max|budget|harga)\s*(?:rp\.?\s*)?(\d+(?:[.,]\d+)?)\s*(juta|jt|miliar|milyar|m)?", text)
        if price_match:
            amount = float(price_match.group(1).replace(",", "."))
            unit = price_match.group(2) or ""
            multiplier = 1_000_000_000 if unit in ("miliar", "milyar", "m") else 1_000_000
            params["max_price"] = int(amount * multiplier)
        elif re.search(r"\b(murah|terjangkau)\b", text):
            params["max_price"] = 250_000_000

        return params

    def _parse_date_from_text(self, message: str) -> date | None:
        text = message.lower()
        month_map = {
            "januari": 1, "februari": 2, "maret": 3, "april": 4,
            "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
            "september": 9, "oktober": 10, "november": 11, "desember": 12
        }

        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            match = re.search(r"\b(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}-\d{1,2}-\d{4})\b", text)
            if match:
                try:
                    return datetime.strptime(match.group(1), fmt).date()
                except ValueError:
                    pass

        match = re.search(
            r"\b(\d{1,2})\s+(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)(?:\s+(\d{4}))?\b",
            text
        )
        if match:
            today = datetime.now().date()
            day = int(match.group(1))
            month = month_map[match.group(2)]
            year = int(match.group(3)) if match.group(3) else today.year
            try:
                parsed = date(year, month, day)
                if not match.group(3) and parsed < today:
                    parsed = date(year + 1, month, day)
                return parsed
            except ValueError:
                return None

        match = re.search(r"\btanggal\s+(\d{1,2})\b", text)
        if match:
            today = datetime.now().date()
            day = int(match.group(1))
            try:
                parsed = date(today.year, today.month, day)
                if parsed < today:
                    month = 1 if today.month == 12 else today.month + 1
                    year = today.year + 1 if today.month == 12 else today.year
                    parsed = date(year, month, day)
                return parsed
            except ValueError:
                return None

        return None

    def _rule_detect_slots(self, message: str) -> dict | None:
        text = message.lower()
        if not re.search(r"\b(slot|jadwal kosong|available slot|jadwal tersedia|jam kosong|waktu kosong)\b", text):
            return None

        params: Dict[str, Any] = {}
        parsed_date = self._parse_date_from_text(message)
        if parsed_date:
            params["date"] = parsed_date
        return params

    async def _build_rag_context(self, message: str, user: User) -> tuple[str, bool]:
        """Build RAG context and return (context, has_data)"""
        parts = []
        has_data = False
        
        relevant_cars = await self._retrieve_relevant_cars(message, limit=3)
        if relevant_cars:
            has_data = True
            parts.append("Informasi inventaris relevan untuk pertanyaan ini:")
            for c in relevant_cars:
                parts.append(
                    f"- {c.brand} {c.model} ({c.year}) [{c.car_type}] - Rp {c.price:,.0f} | {c.transmission} | {c.fuel} | Status: {c.status}"
                )
                if c.features:
                    parts.append(f"  Fitur: {', '.join(c.features)}")
                if c.description:
                    parts.append(f"  Deskripsi: {c.description}")
        else:
            parts.append("Tidak ada data mobil yang relevan ditemukan dari inventaris saat ini.")

        try:
            my_bookings = await schedule_service.get_my_schedules(user, page=1, limit=3)
            if getattr(my_bookings, 'appointments', None):
                has_data = True
                parts.append("Ringkasan jadwal Anda saat ini:")
                for s in my_bookings.appointments:
                    car_desc = f"{s.car.brand} {s.car.model}" if getattr(s, 'car', None) else "-"
                    slot_desc = f"{s.slot.location.location_name if getattr(s, 'slot', None) and getattr(s.slot, 'location', None) else ''} {s.slot.date} {s.slot.time}" if getattr(s, 'slot', None) else ""
                    parts.append(f"- ID: {s.id} | {car_desc} | {s.status} | {slot_desc}")
        except Exception:
            pass

        return "\n".join(parts), has_data

    def _rule_detect_booking(self, message: str, history: list) -> dict | None:
        """
        Rule-based booking detector. Checks if message + recent history signals CREATE_BOOKING.
        Returns params dict (may be empty) if signal detected, None if no booking signal at all.
        IMPORTANT: Always returns dict (not None) when booking signal found, so CREATE_BOOKING
        handler shows the form template instead of falling back to NLU hallucination.
        """
        BOOKING_SIGNALS = [
            r"\bbuat\b.*(jadwal|janji|temu|booking|appointment)",
            r"\bjadwal\b.*(temu|ketemu|meeting|bertemu)",
            r"\bingin\b.*(jadwal|booking|temu|janji)",
            r"\b(mau|ingin|pengen|pingin)\b.*\b(ketemu|ketemuan|bertemu|temu|janjian)\b.*\b(admin|owner)\b",
            r"\b(mau|ingin|pengen|pingin|buat|bikin)\b.*\b(appointment|janji|jadwal)\b.*\b(admin|owner)\b",
            r"\b(ketemu|ketemuan|bertemu|temu|janjian)\b.*\b(admin|owner)\b",
            r"\bbuat\s+jadwal\b",
            r"\bbikin\s+jadwal\b",
            r"\bbooking\b",
            r"\bappointment\b",
            r"\bbuat\s+appointment\b",
            r"\bbikin\s+appointment\b",
            r"\bjanjian\b",
            r"\bketemu\s+admin\b",
            r"\bketemuan\s+sama\s+admin\b",
            r"\bbertemu\s+admin\b",
            r"\btemu\s+admin\b",
            r"\bketemu\s+owner\b",
            r"\btemu\s+owner\b",
        ]
        HISTORY_BOOKING_SIGNALS = [
            r"jadwal", r"temu", r"booking", r"appointment", r"janjian",
            r"bawa ke owner", r"bawa mobil", r"ketemu owner", r"temu owner",
            r"ketemu admin", r"ketemuan sama admin", r"bertemu admin", r"temu admin"
        ]

        MONTH_MAP = {
            "januari": 1, "februari": 2, "maret": 3, "april": 4,
            "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
            "september": 9, "oktober": 10, "november": 11, "desember": 12
        }

        # Check if current message has a direct booking signal
        msg_lower = message.lower()
        msg_has_signal = any(re.search(p, msg_lower) for p in BOOKING_SIGNALS)
        msg_has_booking_details = any(re.search(p, msg_lower) for p in [
            r"\btanggal\s*[=:]?\s*\d{1,2}",
            r"\b\d{1,2}\s+(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)(?:\s+\d{4})?\b",
            r"\b\d{4}[\/-](?:\d{1,2}|januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)[\/-]\d{1,2}\b",
            r"\b(jam|pukul)\s*[=:]?\s*\d{1,2}(?:[.:]\d{2})?\b",
            r"\b\d{1,2}[.:]\d{2}\b",
            r"\b(mobil|kendaraan|unit)\b\s*(?:yang\s+akan\s+di\s+bawa\s+owner|yang\s+dibawa\s+owner|owner)?\s*[=:]",
        ])

        # Check if recent history (last 4 msgs) has booking context
        recent_texts = " ".join([m.get("content", "") for m in history[-4:]]).lower()
        history_has_signal = any(re.search(p, recent_texts) for p in HISTORY_BOOKING_SIGNALS)

        if not (msg_has_signal or (history_has_signal and msg_has_booking_details)):
            return None  # No booking signal → fall through to NLU

        # Booking confirmed. Extract params from all user messages combined.
        all_user_msgs = " ".join([m.get("content", "") for m in history if m.get("role") == "user"])
        all_user_msgs += " " + message
        combined = all_user_msgs.lower()
        params = {}

        # ── DATE EXTRACTION ───────────────────────────────────────────────
        # Format 1: "2026/mei/18" or "2026-mei-18" (year/month_name/day)
        mx = re.search(
            r"(\d{4})[\/-](januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)[\/-](\d{1,2})",
            combined
        )
        if mx:
            params["date"] = f"{mx.group(1)}-{MONTH_MAP[mx.group(2)]:02d}-{int(mx.group(3)):02d}"

        # Format 2: "18 mei" or "tanggal 18 mei"
        if "date" not in params:
            mx = re.search(
                r"(?:tanggal\s*[=:]?\s*)?(\d{1,2})[\/ ](januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)",
                combined
            )
            if mx:
                params["date"] = f"{datetime.now().year}-{MONTH_MAP[mx.group(2)]:02d}-{int(mx.group(1)):02d}"

        # Format 3: ISO "2026-05-18"
        if "date" not in params:
            mx = re.search(r"(\d{4}-\d{2}-\d{2})", combined)
            if mx:
                params["date"] = mx.group(1)

        # Format 4: "18/05/2026"
        if "date" not in params:
            mx = re.search(r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})", combined)
            if mx:
                params["date"] = f"{mx.group(3)}-{int(mx.group(2)):02d}-{int(mx.group(1)):02d}"

        # Format 5: bare "tanggal 18"
        if "date" not in params:
            mx = re.search(r"tanggal\s*[=:]?\s*(\d{1,2})\b", combined)
            if mx:
                day = int(mx.group(1))
                today = datetime.now().date()
                from datetime import date as _date
                try:
                    candidate = _date(today.year, today.month, day)
                    if candidate < today:
                        nm = 1 if today.month == 12 else today.month + 1
                        ny = today.year + 1 if today.month == 12 else today.year
                        candidate = _date(ny, nm, day)
                    params["date"] = candidate.isoformat()
                except ValueError:
                    pass

        # ── TIME EXTRACTION ───────────────────────────────────────────────
        # Handles: "jam 15:00", "jam= 15:00", "Jam=15:00", "pukul 15.00", "3 sore"
        mx = re.search(
            r"(?:jam|pukul)\s*[=:]?\s*(\d{1,2})(?:[.:](\d{2}))?\s*(sore|malam|pagi|siang)?",
            combined
        )
        if mx:
            hour = int(mx.group(1))
            minute = (mx.group(2) or "00").strip()
            period = mx.group(3) or ""
            if period in ("sore", "malam") and hour < 12:
                hour += 12
            params["time"] = f"{hour:02d}:{minute.zfill(2)}"
        else:
            mx = re.search(r"\b(\d{2})[.:](\d{2})\b", combined)
            if mx:
                params["time"] = f"{mx.group(1)}:{mx.group(2).strip()}"

        # ── CAR NAME EXTRACTION ───────────────────────────────────────────
        # Strategy 1: after "mobil/kendaraan/unit" keyword, including longer labels
        # like "Mobil yang akan di bawa owner: toyota agya".
        mx = re.search(
            r"(?:mobil|kendaraan|unit)(?:\s+yang\s+akan\s+di\s+bawa\s+owner|\s+yang\s+dibawa\s+owner|\s+owner)?\s*[=:]?\s*([A-Za-z0-9][A-Za-z0-9 \-]{1,38})",
            all_user_msgs,
            re.IGNORECASE
        )
        if mx:
            car_name = mx.group(1).strip().rstrip(",.")
            car_name = re.split(r"\s*(?:,|;|\n|tanggal\s*=|jam\s*=)\s*", car_name, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            if car_name and not re.search(r"^(yang|akan|di|dibawa|bawa|owner)\b", car_name, re.IGNORECASE):
                params["car_name"] = car_name

        # Strategy 2: last comma-separated segment that looks like a proper car name
        if "car_name" not in params:
            NOISE = {"tanggal", "jam", "pukul", "jadwal", "temu", "meeting",
                     "booking", "saya", "mau", "ingin", "buat", "halo", "aku",
                     "kami", "dengan", "untuk", "yang", "dan", "ke", "di"}
            segments = [s.strip() for s in re.split(r"[,;\n]", message)]
            for seg in reversed(segments):
                seg_clean = seg.strip().rstrip(".,")
                words = seg_clean.split()
                if (len(words) >= 2
                        and seg_clean
                        and not any(w.lower() in NOISE for w in words)
                        and not re.search(r"\d{4}|\d{2}[:.]\d{2}", seg_clean)):
                    params["car_name"] = seg_clean
                    break

        return params

    async def get_response(self, message: str, user: User, session_id: Optional[str] = None) -> dict:
        # Auto-generate session_id if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 1. Get History
        history_doc = await self._get_or_create_history(session_id, user.id)
        history_messages = history_doc.messages
        
        # Format history for NLU context (last 3 messages)
        history_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history_messages[-3:]]) if history_messages else "Tidak ada"

        # 2. STEP 1: Rule-based intent detection FIRST (bypass NLU model)
        rule_params = self._rule_detect_booking(message, history_messages)
        if rule_params is not None:
            intent = "CREATE_BOOKING"
            params = rule_params
            print(f"[RULE-BASED] Detected CREATE_BOOKING: {params}")
        else:
            slot_params = self._rule_detect_slots(message)
            if slot_params is not None:
                intent = "GET_SLOTS"
                params = slot_params
                print(f"[RULE-BASED] Detected GET_SLOTS: {params}")
            else:
                search_params = self._rule_detect_car_search(message)
                if search_params is not None:
                    intent = "SEARCH_CAR"
                    params = search_params
                    print(f"[RULE-BASED] Detected SEARCH_CAR: {params}")
                else:
                    # Fall back to NLU model
                    nlu_prompt = f"""Kamu adalah NLU Parser untuk Showroom Mobil. Tugasmu mengekstrak niat (intent) dan parameter dari pesan user.
Waktu sekarang: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

INTENT yang tersedia:
- SEARCH_CAR: Mencari mobil (params: brand, min_price, max_price, transmission, type)
- GET_SLOTS: Mencari jadwal kosong (params: location_id, date)
- CREATE_BOOKING: Membuat janji temu/booking (params: date (format YYYY-MM-DD atau DD), time (format HH:MM), car_name, notes)
- CANCEL_BOOKING: Membatalkan jadwal (params: schedule_id)
- MY_BOOKINGS: Melihat daftar janji temu milik user saat ini
- GENERAL: Tanya jawab umum

Konteks Percakapan Sebelumnya:
{history_context}

Pesan User Saat Ini: "{message}"

PENTING: Gunakan 'Konteks Percakapan Sebelumnya' untuk menentukan apakah pesan saat ini adalah kelanjutan dari niat sebelumnya.

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

        response_style = self._detect_response_style(message)

        # 3. STEP 2: Execution & Context Gathering
        context = ""
        car_recommendations = []
        available_slots = []
        # Skip RAG context for booking intents to avoid car info contaminating the reply
        if intent in ("CREATE_BOOKING", "CANCEL_BOOKING", "MY_BOOKINGS"):
            rag_context, has_retrieval_data = "", False
        else:
            rag_context, has_retrieval_data = await self._build_rag_context(message, user)


        try:
            if intent == "SEARCH_CAR":
                brand = params.get("brand")
                max_price = params.get("max_price")
                if isinstance(max_price, str):
                    if "juta" in max_price:
                        max_price = int(re.sub(r'[^0-9]', '', max_price)) * 1000000
                    elif "jt" in max_price:
                        max_price = int(re.sub(r'[^0-9]', '', max_price)) * 1000000

                cars, _, _ = await car_service.get_all_cars(
                    page=1, limit=5, brand=brand, max_price=max_price,
                    transmission=params.get("transmission"), car_type=params.get("type")
                )
                
                if cars:
                    context = "Mobil ditemukan:\n" + "\n".join([f"- {c.brand} {c.model} (ID: {c.id}) - Rp {c.price:,.0f}" for c in cars])
                    from app.schemas.car import CarResponse
                    for c in cars:
                        car_recommendations.append(CarResponse.from_model(c).model_dump())
                else:
                    context = "Tidak ada mobil ditemukan."

            elif intent == "GET_SLOTS":
                slot_date = params.get("date")
                if isinstance(slot_date, str):
                    slot_date = self._parse_date_from_text(slot_date)
                slots = await available_slot_service.get_available_slots(
                    location_id=params.get("location_id"),
                    slot_date=slot_date
                )
                if slots:
                    available_slots = [s.model_dump(mode="json") for s in slots[:5]]
                    context = "Slot tersedia:\n" + "\n".join([f"- ID: {s.slot_id} | {s.location.location_name if s.location else ''} | {s.date} {s.time}" for s in slots[:5]])
                else:
                    if slot_date:
                        context = "Maaf pada tanggal tersebut admin tidak memiliki jadwal kosong untuk bertemu."
                    else:
                        context = "Tidak ada slot jadwal tersedia saat ini."

            elif intent == "MY_BOOKINGS":
                my_schedules = await schedule_service.get_my_schedules(user, page=1, limit=5)
                if getattr(my_schedules, 'appointments', None):
                    context = "Jadwal Anda saat ini:\n" + "\n".join([
                        f"- ID: {s.id} | Mobil: {s.car.brand} {s.car.model if s.car else 'Tidak ditemukan'} | Status: {s.status} | Waktu: {s.slot.date if getattr(s, 'slot', None) else ''} {s.slot.time if getattr(s, 'slot', None) else ''}"
                        if s.car else
                        f"- ID: {s.id} | Mobil: Tidak ditemukan | Status: {s.status} | Waktu: {s.slot.date if getattr(s, 'slot', None) else ''} {s.slot.time if getattr(s, 'slot', None) else ''}"
                        for s in my_schedules.appointments
                    ])
                else:
                    context = "Anda belum memiliki jadwal janji temu."

            elif intent == "CREATE_BOOKING":
                date_str = params.get("date")
                time_str = params.get("time")
                car_name = params.get("car_name")
                notes = params.get("notes")

                if not date_str or not time_str or not car_name:
                    context = (
                        "pastikan sudah menentukan mobil yang akan dibawa owner saat booking dilakukan, untuk membuat jadwal bertemu silahkan isi data berikut:\n"
                        "Tanggal = Tahun/bulan/tanggal,\n"
                        "Jam = XX:XX,\n"
                        "Mobil yang akan di bawa owner:....,\n"
                    )
                else:
                    from datetime import date
                    today = datetime.now().date()
                    slot_date = None
                    if isinstance(date_str, str):
                        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %m %Y"):
                            try:
                                slot_date = datetime.strptime(date_str, fmt).date()
                                break
                            except ValueError:
                                pass
                        
                        if not slot_date and date_str.isdigit() and 1 <= int(date_str) <= 31:
                            target_day = int(date_str)
                            try:
                                slot_date = date(today.year, today.month, target_day)
                                if slot_date < today:
                                    month = 1 if today.month == 12 else today.month + 1
                                    year = today.year + 1 if today.month == 12 else today.year
                                    slot_date = date(year, month, target_day)
                            except ValueError:
                                pass

                    if not slot_date:
                        context = "Format tanggal tidak valid. Mohon berikan tanggal yang benar (contoh: 2026-05-18 atau 18)."
                    else:
                        from app.models.car import Car
                        # Split car_name into tokens and build OR query for each token
                        # e.g. "Nissan New Livina" → search brand/model for "Nissan" OR "Livina" etc.
                        tokens = [t for t in car_name.split() if len(t) >= 3]
                        if not tokens:
                            tokens = [car_name]
                        token_conditions = []
                        for token in tokens:
                            token_conditions.extend([
                                {"brand": {"$regex": token, "$options": "i"}},
                                {"model": {"$regex": token, "$options": "i"}}
                            ])
                        all_candidates = await Car.find({"$or": token_conditions}).to_list()

                        # Score each candidate by how many tokens appear in brand+model
                        def score_car(c):
                            haystack = f"{c.brand} {c.model}".lower()
                            return sum(1 for t in tokens if t.lower() in haystack)

                        all_candidates.sort(key=score_car, reverse=True)
                        cars = [c for c in all_candidates if score_car(c) > 0]

                        if not cars:
                            context = f"Maaf, mobil '{car_name}' tidak ditemukan di sistem kami."
                        else:
                            normalized_input = re.sub(r"\s+", " ", car_name.lower()).strip()
                            exact_cars = [
                                c for c in cars
                                if re.sub(r"\s+", " ", f"{c.brand} {c.model}".lower()).strip() == normalized_input
                            ]

                            if not exact_cars:
                                from app.schemas.car import CarResponse
                                detected_brand = next(
                                    (
                                        c.brand for c in cars
                                        if re.search(rf"\b{re.escape(c.brand.lower())}\b", normalized_input)
                                    ),
                                    None
                                )
                                recommendation_source = cars
                                if detected_brand:
                                    recommendation_source, _, _ = await car_service.get_all_cars(
                                        page=1,
                                        limit=5,
                                        brand=detected_brand
                                    )
                                car_recommendations = [
                                    CarResponse.from_model(c).model_dump()
                                    for c in recommendation_source[:5]
                                ]
                                context = "Maaf data mobil yang kamu masukkan tidak lengkap, berikut adalah daftar mobil sesuai masukan brand mobil yang kamu masukkan untuk referensi."
                            else:
                                selected_car = exact_cars[0]
                                slots_for_date = await available_slot_service.get_available_slots(slot_date=slot_date)
                                
                                matched_slot = None
                                time_prefix = str(time_str).replace(".", ":")[:5] if time_str else ""
                                for slot in slots_for_date:
                                    if time_prefix and time_prefix in slot.time:
                                        matched_slot = slot
                                        break
                                
                                if matched_slot:
                                    from app.schemas.schedule import ScheduleCreate
                                    new_booking = await schedule_service.create_schedule(user, ScheduleCreate(
                                        car_id=str(selected_car.id), 
                                        slot_id=str(matched_slot.slot_id),
                                        email=user.email,
                                        phone=user.phone or "-",
                                        notes=notes or f"Pertemuan untuk mobil: {car_name}"
                                    ))
                                    context = "BERHASIL! Janji temu telah dibuat, silahkan cek page appointment."
                                else:
                                    if slots_for_date:
                                        available_slots = [s.model_dump(mode="json") for s in slots_for_date[:5]]
                                        context = f"Maaf, jadwal di tanggal {slot_date} jam {time_str} tidak tersedia. Berikut available_slot yang tersedia di tanggal tersebut:\n" + "\n".join([f"- Jam {s.time}" for s in slots_for_date[:5]])
                                    else:
                                        context = "Maaf pada tanggal tersebut admin tidak memiliki jadwal kosong untuk bertemu."

            elif intent == "CANCEL_BOOKING":
                schedule_id = params.get("schedule_id")
                if schedule_id:
                    success = await schedule_service.cancel_schedule(user, schedule_id)
                    context = "BERHASIL! Jadwal tersebut telah dibatalkan." if success else "Gagal membatalkan. Pastikan ID Jadwal benar dan itu milik Anda."
                else:
                    context = "Tolong berikan ID Jadwal yang ingin dibatalkan. Anda bisa tanya 'apa jadwal saya' untuk melihat ID-nya."

            else:
                if not context:
                    context = "Gunakan informasi inventaris relevan dan riwayat pengguna untuk menjawab." 
        except Exception as e:
            context = f"Terjadi kesalahan saat memproses permintaan: {str(e)}"

        if not car_recommendations and has_retrieval_data:
            relevant_cars = await self._retrieve_relevant_cars(message, limit=3)
            from app.schemas.car import CarResponse
            for c in relevant_cars:
                car_recommendations.append(CarResponse.from_model(c).model_dump())

        # 4. STEP 3: Generate Final Response
        DIRECT_REPLY_INTENTS = {"CREATE_BOOKING", "CANCEL_BOOKING", "MY_BOOKINGS", "GET_SLOTS"}

        if intent in DIRECT_REPLY_INTENTS and context:
            # For booking-related intents, use the structured context directly as the reply.
            # Do NOT call the AI model — it will hallucinate and override the correct message.
            reply = context
        elif intent == "SEARCH_CAR" and car_recommendations:
            reply = self._build_data_reply(context, car_recommendations, response_style, has_retrieval_data)
        else:
            system_prompt = f"""Kamu adalah Showroom AI, asisten virtual proaktif di Dealer Mobil Premium.
Nama Customer: {user.username}
Role Customer: {user.role}

KONTEN REAL-TIME (Gunakan data ini):
{context}

RETRIEVAL CONTEXT:
{rag_context}

PANDUAN JAWABAN:
- JIKA ditemukan data mobil/rekomendasi mobil, jawab singkat saja: \"Berikut data yang saya temukan sesuai permintaan Anda.\"
- Jawab sesuai keinginan user: jika user meminta ringkas, jawab ringkas; jika user meminta detail, jelaskan komprehensif.
- Gunakan gaya bahasa yang sopan, profesional, dan mudah dimengerti.
- Untuk hasil pencarian mobil, jangan jelaskan detail unit di teks reply karena detail sudah dikirim di car_recommendations.
- Bila tidak ada data yang relevan, akui keterbatasan dan tawarkan bantuan lanjutan.
- Jangan mengarang fakta yang tidak ada di CONTEXT atau RETRIEVAL CONTEXT.
- Bila diminta, berikan rekomendasi unit terbaik berdasarkan preferensi.

GAYA JAWABAN: {response_style}"""

            messages = [{"role": "system", "content": system_prompt}] + history_messages + [{"role": "user", "content": message}]
            reply = await self._call_ollama(messages)
            if not reply:
                reply = self._build_data_reply(context, car_recommendations, response_style, has_retrieval_data)

        # 5. Save History
        await self._add_to_history(session_id, user.id, "user", message)
        await self._add_to_history(session_id, user.id, "assistant", reply)

        return {
            "session_id": session_id,
            "reply": reply,
            "car_recommendations": car_recommendations,
            "available_slots": available_slots
        }

ai_chat_service = AIChatService()
