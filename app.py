import uuid
from html import escape

import streamlit as st

# ------------------------------------------------------------------ CSS ---
# 스타일은 모두 여기서 관리한다. 색은 투명도 기반 중립색 + 테마 포인트 컬러만 써서
# 라이트/다크 모드 모두에서 글자가 잘 보이게 한다.
ACCENT = "46, 158, 91"  # .streamlit/config.toml 의 primaryColor 와 같은 초록(RGB)

CSS = f"""
<style>
/* 기본 메뉴 / 푸터 / 데코레이션 숨김 */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {{
    display: none !important;
}}
[data-testid="stHeader"] {{ background: transparent; }}

.block-container {{ padding-top: 2rem; padding-bottom: 3rem; }}

/* 헤더: 제목 + 진행 현황 */
[data-testid="stMarkdownContainer"] p.app-title {{
    font-size: 2rem; font-weight: 700; line-height: 1.3; margin: 0 0 .25rem 0;
}}
[data-testid="stMarkdownContainer"] p.progress-text {{ font-weight: 600; margin: 0 0 .25rem 0; }}
[data-testid="stMarkdownContainer"] p.progress-done {{
    color: rgb({ACCENT}); font-weight: 600; margin: .25rem 0 0 0;
}}

/* 목록 행(카드) */
[class*="st-key-item_"], [class*="st-key-itemedit_"] {{
    border: 1px solid rgba(128, 128, 128, .25);
    border-radius: .75rem;
    padding: .4rem .75rem;
    background: rgba(128, 128, 128, .05);
}}
[class*="st-key-itemedit_"] {{
    border-color: rgb({ACCENT});
    background: rgba({ACCENT}, .12);
}}
/* 행 사이 간격을 일정하게 */
[data-testid="stVerticalBlock"] {{ gap: .6rem; }}
[class*="st-key-item_"] [data-testid="stVerticalBlock"] {{ gap: 0; }}
[class*="st-key-itemedit_"] [data-testid="stVerticalBlock"] {{ gap: .5rem; }}
/* 버튼 글자가 세로로 꺾이지 않게 */
[data-testid="stButton"] button p, [data-testid="stFormSubmitButton"] button p {{ white-space: nowrap; }}

/* 아이템 이름 / 수량 / 완료 상태 */
.item-name {{ font-size: 1.05rem; word-break: break-word; }}
.item-qty {{ opacity: .6; margin-left: .25rem; font-size: .95rem; }}
.item-name.done {{ text-decoration: line-through; opacity: .45; }}

/* 수정/삭제 아이콘 버튼: 작고 눈에 덜 띄게, 터치 영역은 충분히 */
[class*="st-key-editbtn_"] [data-testid="stBaseButton-secondary"], [class*="st-key-delbtn_"] [data-testid="stBaseButton-secondary"] {{
    min-width: 2.75rem; min-height: 2.75rem; padding: 0;
    border: none; background: transparent; opacity: .6; font-size: 1.1rem;
}}
[class*="st-key-editbtn_"] [data-testid="stBaseButton-secondary"]:hover, [class*="st-key-delbtn_"] [data-testid="stBaseButton-secondary"]:hover {{
    opacity: 1; background: rgba(128, 128, 128, .15);
}}
/* 수정/삭제 버튼의 글자는 화면에서 숨기고(스크린리더용으로만 유지) 아이콘만 보이게 */
[class*="st-key-editbtn_"] button p, [class*="st-key-delbtn_"] button p {{
    position: absolute; width: 1px; height: 1px; overflow: hidden;
    clip: rect(0 0 0 0); white-space: nowrap;
}}
/* 체크박스 터치 영역 (가로·세로 모두 44px) */
[class*="st-key-item_"] [data-testid="stCheckbox"] {{ min-width: 2.75rem; min-height: 2.75rem; }}
[class*="st-key-item_"] [data-testid="stCheckbox"] label {{
    width: 100%; min-height: 2.75rem; justify-content: center; align-items: center;
}}

/* 모바일: 컬럼이 세로로 쌓이지 않고 한 줄을 유지 */
[data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: .5rem; align-items: center; }}
[data-testid="stColumn"] {{ min-width: 0 !important; }}
[class*="st-key-item_"] [data-testid="stHorizontalBlock"] {{ gap: .25rem; }}
/* 목록 행: 체크박스/수정/삭제는 내용 폭, 이름 칸이 나머지를 차지 (좁은 화면에서 카드 밖으로 안 넘치게) */
[class*="st-key-item_"] [data-testid="stColumn"]:not(:nth-child(2)) {{ flex: 0 0 auto !important; width: auto !important; }}
[class*="st-key-item_"] [data-testid="stColumn"]:nth-child(2) {{ flex: 1 1 0 !important; width: auto !important; }}

/* 빈 상태 */
.empty-state {{ text-align: center; padding: 2.5rem 1rem; opacity: .75; }}
.empty-state .emoji {{ font-size: 2.5rem; display: block; margin-bottom: .5rem; }}

@media (max-width: 640px) {{
    .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
    [data-testid="stMarkdownContainer"] p.app-title {{ font-size: 1.6rem; }}
}}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------- 상태 ---
def init_state() -> None:
    """session_state 초기화."""
    st.session_state.setdefault("items", [])
    st.session_state.setdefault("editing_id", None)  # 편집 중인 아이템 id


MAX_NAME_LEN = 100  # 이름 최대 글자 수
MAX_QTY = 99  # 수량 최대값


def find_item(item_id: str) -> dict | None:
    return next((i for i in st.session_state["items"] if i["id"] == item_id), None)


# ------------------------------------------------------------ 콜백 함수 ---
def add_item() -> None:
    """추가 폼 제출 콜백. 폼 위젯 값은 session_state에서 읽는다."""
    name = st.session_state.get("new_name", "").strip()
    qty = int(st.session_state.get("new_qty", 1))
    if not name:
        st.session_state["flash_warning"] = "아이템 이름을 입력해주세요."
        return
    st.session_state["items"].append(
        {"id": str(uuid.uuid4()), "name": name, "qty": qty, "checked": False}
    )


def toggle_item(item_id: str) -> None:
    item = find_item(item_id)
    if item:
        item["checked"] = bool(st.session_state.get(f"chk_{item_id}", False))


def delete_item(item_id: str) -> None:
    st.session_state["items"] = [
        i for i in st.session_state["items"] if i["id"] != item_id
    ]
    if st.session_state["editing_id"] == item_id:
        st.session_state["editing_id"] = None


def delete_checked() -> None:
    st.session_state["items"] = [
        i for i in st.session_state["items"] if not i["checked"]
    ]
    editing = st.session_state["editing_id"]
    if editing and find_item(editing) is None:
        st.session_state["editing_id"] = None


def start_edit(item_id: str) -> None:
    item = find_item(item_id)
    if not item:
        return
    # 다른 항목을 편집 중이었고 저장 안 한 변경이 있으면 버려진다는 걸 알려준다
    prev = find_item(st.session_state["editing_id"]) if st.session_state["editing_id"] else None
    if prev and prev["id"] != item_id:
        pid = prev["id"]
        changed = (
            st.session_state.get(f"edit_name_{pid}", prev["name"]).strip() != prev["name"]
            or int(st.session_state.get(f"edit_qty_{pid}", prev["qty"])) != prev["qty"]
        )
        if changed:
            st.toast(f"'{prev['name']}'의 저장하지 않은 수정 내용은 버려졌어요.", icon="⚠️")
    # 편집 입력값을 현재 값으로 맞춰 둔다 (이전 취소/미저장 값이 남지 않도록)
    st.session_state[f"edit_name_{item_id}"] = item["name"]
    # 수량은 위젯 기본값(value)이 현재 수량이므로, 이전 위젯 상태만 지운다
    st.session_state.pop(f"edit_qty_{item_id}", None)
    st.session_state["editing_id"] = item_id


def cancel_edit() -> None:
    st.session_state["editing_id"] = None


def save_edit(item_id: str) -> None:
    item = find_item(item_id)
    if not item:
        st.session_state["editing_id"] = None
        return
    name = st.session_state.get(f"edit_name_{item_id}", "").strip()
    if not name:
        st.session_state["flash_warning"] = "이름을 비워둘 수 없어요."
        return  # 편집 모드 유지
    item["name"] = name
    item["qty"] = int(st.session_state.get(f"edit_qty_{item_id}", item["qty"]))
    st.session_state["editing_id"] = None


# ------------------------------------------------------------- 렌더링 ---
def render_header() -> None:
    items = st.session_state["items"]
    total = len(items)
    done = sum(1 for i in items if i["checked"])

    with st.container():
        st.markdown('<p class="app-title">🛒 쇼핑리스트</p>', unsafe_allow_html=True)
        st.markdown(
            f'<p class="progress-text">{done} / {total} 완료</p>',
            unsafe_allow_html=True,
        )
        st.progress(done / total if total else 0.0)
        if total and done == total:
            st.markdown(
                '<p class="progress-done">장보기 완료! 🎉</p>', unsafe_allow_html=True
            )


def render_form() -> None:
    with st.form("add_form", clear_on_submit=True):
        col_name, col_qty, col_btn = st.columns([4, 3, 3], vertical_alignment="bottom")
        col_name.text_input(
            "아이템 이름", key="new_name", placeholder="예: 우유", max_chars=MAX_NAME_LEN
        )
        col_qty.number_input(
            "수량", min_value=1, max_value=MAX_QTY, value=1, step=1, key="new_qty"
        )
        col_btn.form_submit_button(
            "추가", on_click=add_item, use_container_width=True, type="primary"
        )

    warning = st.session_state.pop("flash_warning", None)
    if warning:
        st.warning(warning)


def render_view_row(item: dict) -> None:
    iid = item["id"]
    with st.container(key=f"item_{iid}"):
        c_chk, c_name, c_edit, c_del = st.columns(
            [0.8, 7.4, 1.2, 1.2], vertical_alignment="center"
        )
        c_chk.checkbox(
            "완료",
            value=item["checked"],
            key=f"chk_{iid}",
            on_change=toggle_item,
            args=(iid,),
            label_visibility="collapsed",
        )
        # 사용자 입력은 반드시 escape 해서 HTML로 넣는다 (XSS / 마크다운 깨짐 방지)
        cls = "item-name done" if item["checked"] else "item-name"
        c_name.html(
            f'<span class="{cls}">{escape(item["name"])}'
            f'<span class="item-qty">×{item["qty"]}</span></span>'
        )
        # 라벨 텍스트는 CSS로 숨겨 스크린리더에만 읽히게 하고, 화면에는 아이콘만 보인다
        c_edit.button(
            "수정", icon="✏️", key=f"editbtn_{iid}", on_click=start_edit, args=(iid,), help="수정"
        )
        c_del.button(
            "삭제", icon="🗑️", key=f"delbtn_{iid}", on_click=delete_item, args=(iid,), help="삭제"
        )


def render_edit_row(item: dict) -> None:
    iid = item["id"]
    with st.container(key=f"itemedit_{iid}"):
        # 좁은 화면에서도 깨지지 않도록 두 줄: 이름 / (수량 + 저장 + 취소)
        st.text_input(
            "이름", key=f"edit_name_{iid}", label_visibility="collapsed",
            placeholder="이름", max_chars=MAX_NAME_LEN,
        )
        c_qty, c_save, c_cancel = st.columns([3, 2, 2], vertical_alignment="center")
        # value=현재 수량: 칸을 비우면 기존 수량으로 되돌아간다 (1로 바뀌지 않음)
        c_qty.number_input(
            "수량", min_value=1, max_value=MAX_QTY, value=min(item["qty"], MAX_QTY), step=1,
            key=f"edit_qty_{iid}", label_visibility="collapsed",
        )
        c_save.button(
            "저장", key=f"save_{iid}", on_click=save_edit, args=(iid,),
            type="primary", use_container_width=True,
        )
        c_cancel.button(
            "취소", key=f"cancel_{iid}", on_click=cancel_edit, use_container_width=True
        )


def render_list() -> None:
    items = st.session_state["items"]
    if not items:
        st.markdown(
            '<div class="empty-state"><span class="emoji">🛍️</span>'
            "아직 아이템이 없어요.<br>위에서 추가해보세요!</div>",
            unsafe_allow_html=True,
        )
        return

    # 미체크가 위, 체크가 아래 (sorted는 안정 정렬이라 추가 순서 유지)
    for item in sorted(items, key=lambda i: i["checked"]):
        if st.session_state["editing_id"] == item["id"]:
            render_edit_row(item)
        else:
            render_view_row(item)

    has_checked = any(i["checked"] for i in items)
    st.button("체크된 항목 모두 삭제", on_click=delete_checked, disabled=not has_checked)


def main() -> None:
    st.set_page_config(page_title="쇼핑리스트", page_icon="🛒", layout="centered")
    inject_css()
    init_state()
    render_header()
    render_form()
    render_list()


main()
