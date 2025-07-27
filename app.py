import json
import os
import random
from typing import List, Dict, Tuple

import streamlit as st
import streamlit.components.v1 as components

FLASHCARDS_FILE = "flashcards.json"

# ───────────────────────────────────────────────────────────────────────────────
# HELPERS (compatibility)
# ───────────────────────────────────────────────────────────────────────────────

def _do_rerun():
    """Rerun the Streamlit app, supporting both old (experimental_rerun) and new (rerun) APIs."""
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

# ───────────────────────────────────────────────────────────────────────────────
# DATA LAYER
# ───────────────────────────────────────────────────────────────────────────────

def load_all_flashcards() -> Dict[str, List[Dict[str, str]]]:
    """Return the whole DB (<user> -> [ {question, answer}, ... ])."""
    if not os.path.exists(FLASHCARDS_FILE):
        with open(FLASHCARDS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(FLASHCARDS_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return json.loads(content) if content else {}


def save_all_flashcards(data: Dict[str, List[Dict[str, str]]]):
    with open(FLASHCARDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_user_flashcards(username: str, data: Dict[str, List[Dict[str, str]]]):
    return data.get(username, [])


def add_flashcard(username: str, question: str, answer: str, data):
    data.setdefault(username, []).append({"question": question, "answer": answer})
    save_all_flashcards(data)


def delete_flashcard(username: str, index: int, data):
    data[username].pop(index)
    save_all_flashcards(data)


def edit_flashcard(username: str, index: int, question: str, answer: str, data):
    data[username][index] = {"question": question, "answer": answer}
    save_all_flashcards(data)

# ───────────────────────────────────────────────────────────────────────────────
# UI CONFIG
# ───────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="📘 Fiszki", page_icon="📘", layout="wide")
st.title("📘 Fiszki")

username = st.text_input("Wpisz swój nick (np. Methew):").strip().lower()

if not username:
    st.info("✍️ Podaj swój nick, aby rozpocząć.")
    st.stop()

# ───────────────────────────────────────────────────────────────────────────────
# PREP
# ───────────────────────────────────────────────────────────────────────────────

all_data = load_all_flashcards()
user_cards = get_user_flashcards(username, all_data)
show_all = st.checkbox("👥 Pokaż fiszki wszystkich użytkowników")

menu = st.radio(
    "Wybierz:",
    ["🎲 Ucz się", "➕ Dodaj fiszkę", "🔍 Wyszukaj", "📊 Statystyki"],
    horizontal=True,
)

# ───────────────────────────────────────────────────────────────────────────────
# LEARN MODE
# ───────────────────────────────────────────────────────────────────────────────

if st.button("Ballons"):
    st.balloons()

if menu == "🎲 Ucz się":

    def build_card_list() -> List[Dict]:
        if show_all:
            return [
                {**c, "owner": u, "u_index": i}
                for u, lst in all_data.items()
                for i, c in enumerate(lst)
            ]
        return [{**c, "owner": username, "u_index": i} for i, c in enumerate(user_cards)]

    # ─── session bootstrap ─
    if not st.session_state.get("session_active"):
        if st.button("🚀 Rozpocznij sesję"):
            st.session_state.session_cards = random.sample(build_card_list(), k=len(build_card_list()))
            st.session_state.session_pos = 0
            st.session_state.session_active = True
            st.session_state.show_answer = False
            st.session_state.skip_set = set()
            st.session_state.remaining_set = {
                (c["owner"], c["u_index"]) for c in st.session_state.session_cards
            }
    else:
        if st.button("🔄 Przeładuj listę"):
            st.session_state.session_cards = random.sample(build_card_list(), k=len(build_card_list()))
            st.session_state.session_pos = 0
            st.session_state.skip_set = set()
            st.session_state.show_answer = False
            st.session_state.remaining_set = {
                (c["owner"], c["u_index"]) for c in st.session_state.session_cards
            }

    # ─── active session ─
    if st.session_state.get("session_active"):
        if not st.session_state.remaining_set:
            st.success("Sesja zakończona – wszystkie fiszki zaliczone! 🎉")
            if st.button("Zakończ sesję"):
                st.session_state.session_active = False
            st.stop()

        cards = st.session_state.session_cards
        pos = st.session_state.session_pos
        if len(cards) - len(st.session_state.skip_set) == 0:
            st.success("Sesja zakończona – brak więcej fiszek!")
            if st.button("Zakończ sesję"):
                st.session_state.session_active = False
            st.stop()

        while pos in st.session_state.skip_set and pos < len(cards) - 1:
            pos += 1
        st.session_state.session_pos = pos
        card = cards[pos]
        card_key: Tuple[str, int] = (card["owner"], card["u_index"])

        st.subheader(f"Pytanie (od **{card['owner']}**) [{pos + 1}/{len(cards)}]")
        st.write(card["question"])

        # evaluation buttons before reveal
        def _advance():
            if st.session_state.session_pos < len(st.session_state.session_cards) - 1:
                st.session_state.session_pos += 1
            st.session_state.show_answer = False
            _do_rerun()

        colg, colm, colb = st.columns(3)
        if colg.button("✅ Dobrze", key=f"good_{pos}"):
            st.session_state.remaining_set.discard(card_key)
            _advance()
        if colm.button("😐 Średnio", key=f"mid_{pos}"):
            st.session_state.session_cards.append(card.copy())
            _advance()
        if colb.button("❌ Źle", key=f"bad_{pos}"):
            st.session_state.session_cards.extend([card.copy(), card.copy()])
            _advance()

        # navigation & reveal
        nav1, nav2, nav3, nav4 = st.columns([1.3, 1.1, 1.2, 1])
        if nav1.button("👁️ Pokaż odpowiedź"):
            st.session_state.show_answer = True
        if nav2.button("🚫 Nie pokazuj ponownie w tej sesji"):
            st.session_state.skip_set.add(pos)
            st.session_state.remaining_set.discard(card_key)
            st.session_state.show_answer = False
            if pos < len(cards) - 1:
                st.session_state.session_pos += 1
            _do_rerun()
        if nav3.button("⬅️ Poprzednia", disabled=(pos == 0)):
            st.session_state.session_pos -= 1
            st.session_state.show_answer = False
            _do_rerun()
        if nav4.button("➡️ Następna", disabled=(pos >= len(cards) - 1)):
            st.session_state.session_pos += 1
            st.session_state.show_answer = False
            _do_rerun()

        if st.session_state.show_answer:
            st.subheader("Odpowiedź:")
            st.success(card["answer"])

        st.divider()
        if st.button("🏁 Zakończ sesję"):
            st.session_state.session_active = False
            for k in [
                "session_cards",
                "skip_set",
                "session_pos",
                "show_answer",
                "remaining_set",
            ]:
                st.session_state.pop(k, None)
            st.success("Sesja zakończona.")

# ───────────────────────────────────────────────────────────────────────────────
# ADD NEW CARD
# ───────────────────────────────────────────────────────────────────────────────

elif menu == "➕ Dodaj fiszkę":
    st.markdown("**Wpisz pytanie → Enter → wpisz odpowiedź → Enter aby dodać.**")
    with st.form("add_card", clear_on_submit=True):
        col1, col2 = st.columns([2, 2])
        q = col1.text_input("Pytanie:", key="q_add", placeholder="Np. Stolica Polski?")
        a = col2.text_input("Odpowiedź:", key="a_add")
        if st.form_submit_button("✅ Dodaj fiszkę"):
            if q and a:
                add_flashcard(username, q, a, all_data)
                st.success("Dodano!")
            else:
                st.error("Wpisz oba pola.")
    # focus & enter
    components.html(
        """
        <script>
        (function(){
          const inputs = window.parent.document.querySelectorAll('input[type="text"]');
          if(inputs.length>=2){
            const q=inputs[inputs.length-2];
            const a=inputs[inputs.length-1];
            if(q.value===''){q.focus();}
            q.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();a.focus();}});
            a.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();[...window.parent.document.querySelectorAll('button')].find(b=>b.innerText.includes('Dodaj fiszkę'))?.click();}});
          }
        })();
        </script>
        """,
        height=0,
    )

# ───────────────────────────────────────────────────────────────────────────────
# SEARCH + INLINE EDIT/DELETE
# ───────────────────────────────────────────────────────────────────────────────

elif menu == "🔍 Wyszukaj":
    search = st.text_input("Wyszukaj frazę w pytaniach:")
    if search:
        found = []
        for user, cards in all_data.items():
            for idx, c in enumerate(cards):
                if search.lower() in c["question"].lower():
                    found.append({**c, "owner": user, "index": idx})

        if found:
            st.write(f"Znaleziono {len(found)} fiszek:")
            for item in found:
                editable = item["owner"] == username
                with st.expander(f"{item['question']}  (od {item['owner']})"):
                    if editable:
                        q_new = st.text_input(
                            "Pytanie:", item["question"], key=f"q_search_{item['owner']}_{item['index']}"
                        )
                        a_new = st.text_input(
                            "Odpowiedź:", item["answer"], key=f"a_search_{item['owner']}_{item['index']}"
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(
                                "💾 Zapisz", key=f"save_search_{item['owner']}_{item['index']}"
                            ):
                                edit_flashcard(item["owner"], item["index"], q_new, a_new, all_data)
                                st.success("Zmieniono!")
                                st.experimental_rerun()
                        with col2:
                            if st.button(
                                "🗑️ Usuń", key=f"delete_search_{item['owner']}_{item['index']}"
                            ):
                                delete_flashcard(item["owner"], item["index"], all_data)
                                st.success("Usunięto!")
                                st.experimental_rerun()
                    else:
                        st.markdown(f"**Pytanie:** {item['question']}")
                        st.markdown(f"**Odpowiedź:** _{item['answer']}_")
                        st.info("Możesz edytować tylko własne fiszki.")
        else:
            st.warning("Nic nie znaleziono. cosik")

# ───────────────────────────────────────────────────────────────────────────────
# STATS
# ───────────────────────────────────────────────────────────────────────────────

elif menu == "📊 Statystyki":
    st.write(f"📌 Masz **{len(user_cards)}** fiszek.")
    total = sum(len(cards) for cards in all_data.values())
    st.write(f"🌍 W systemie jest **{total}** fiszek od wszystkich użytkowników.")
    st.write("👤 Ranking użytkowników:")
    for user, cards in sorted(all_data.items(), key=lambda x: len(x[1]), reverse=True):
        st.markdown(f"- **{user}**: {len(cards)} fiszek")
