import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
import PyPDF2
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

# ---- CẤU HÌNH TRANG LỚN ----
st.set_page_config(page_title="Reader & AudioBook AI", page_icon="📖", layout="wide", initial_sidebar_state="collapsed")

# ---- QUẢN LÝ TRẠNG THÁI (LƯU GIAO DIỆN) ----
if 'theme' not in st.session_state:
    st.session_state.theme = 'Mặc định (Trắng dịu)'
if 'font_size' not in st.session_state:
    st.session_state.font_size = 18

# ---- CÁC THEME BẢO VỆ MẮT ----
THEMES = {
    'Mặc định (Trắng dịu)': {'bg': '#fcfcfc', 'text': '#333333'},
    'Sepia (Vàng ấm bảo vệ mắt)': {'bg': '#f4ecd8', 'text': '#5b4636'},
    'Dark Mode (Đọc ban đêm)': {'bg': '#1e1e1e', 'text': '#e0e0e0'}
}

current_theme = THEMES[st.session_state.theme]

# ---- CSS TÙY CHỈNH THEO THEME VÀ NÚT BẤM ----
st.markdown(f"""
    <style>
    /* CSS cho khung đọc sách chính */
    .reading-box {{
        background-color: {current_theme['bg']};
        color: {current_theme['text']};
        padding: 40px;
        border-radius: 12px;
        font-family: 'Georgia', serif;
        font-size: {st.session_state.font_size}px;
        line-height: 1.8;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        height: 65vh; /* Độ cao khung cuộn = 65% màn hình */
        overflow-y: scroll;
        margin-bottom: 20px;
    }}
    
    /* Làm đẹp nút Tạo Audio */
    div.stButton > button {{
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border-radius: 30px;
        border: none;
        padding: 10px 24px;
        font-size: 16px;
        font-weight: bold;
        transition: all 0.3s ease;
    }}
    div.stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
    }}
    </style>
""", unsafe_allow_html=True)

# ---- CÁC HÀM XỬ LÝ FILE ----
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def extract_text_from_epub(file_path):
    book = epub.read_epub(file_path)
    text = ""
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_body_content(), 'html.parser')
        text += soup.get_text() + "\n"
    return text

async def tao_audio(text, voice, file_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(file_path)


# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================

# 1. THANH ĐIỀU KHIỂN TRÊN CÙNG (CHIA 3 CỘT)
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    uploaded_file = st.file_uploader("📂 Tải sách (TXT, PDF, EPUB)", type=["txt", "pdf", "epub"], label_visibility="collapsed")

with col2:
    # Bộ điều khiển bảo vệ mắt
    cols_control = st.columns([2, 1])
    with cols_control[0]:
        selected_theme = st.selectbox("🎨 Chế độ đọc:", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme))
        if selected_theme != st.session_state.theme:
            st.session_state.theme = selected_theme
            st.rerun()
            
    with cols_control[1]:
        new_size = st.number_input("Tăng/Giảm cỡ chữ:", min_value=12, max_value=36, value=st.session_state.font_size, step=2)
        if new_size != st.session_state.font_size:
            st.session_state.font_size = new_size
            st.rerun()

with col3:
    # Cấu hình giọng đọc
    VOICES = {"Giọng Nữ (Hoài My)": "vi-VN-HoaiMyNeural", "Giọng Nam (Nam Minh)": "vi-VN-NamMinhNeural"}
    voice_choice = st.selectbox("🗣️ Chọn giọng đọc:", list(VOICES.keys()))

st.markdown("---")

# 2. KHU VỰC HIỂN THỊ SÁCH VÀ NGHE AUDIO
text_input = ""

if uploaded_file is None:
    st.info("👈 Bắt đầu bằng cách tải một cuốn sách hoặc file tài liệu của bạn ở góc trên bên trái.")
else:
    # Xử lý nội dung file
    file_extension = uploaded_file.name.split('.')[-1].lower()
    with st.spinner("⏳ Đang tải nội dung..."):
        try:
            if file_extension == "txt":
                text_input = uploaded_file.read().decode("utf-8")
            elif file_extension == "pdf":
                text_input = extract_text_from_pdf(uploaded_file)
            elif file_extension == "epub":
                with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp_epub:
                    tmp_epub.write(uploaded_file.getvalue())
                    tmp_epub_path = tmp_epub.name
                text_input = extract_text_from_epub(tmp_epub_path)
                os.remove(tmp_epub_path)
        except Exception as e:
            st.error(f"Lỗi: {e}")

    if text_input:
        # Cột trái (Khu vực cuộn để tự đọc) và Cột phải (Điều khiển Audio)
        main_col1, main_col2 = st.columns([7, 3])
        
        with main_col1:
            # Render khung đọc sách cuộn
            st.markdown(f'<div class="reading-box">{text_input.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
            
        with main_col2:
            st.subheader("🎧 Trình phát Audio")
            st.write("Nhấn nút dưới đây để AI đọc đoạn sách bên cạnh cho bạn nghe.")
            
            if st.button("▶️ TẠO SÁCH NÓI", use_container_width=True):
                if len(text_input) > 5000:
                    st.warning("Đoạn sách hơi dài, bạn chờ khoảng 1-2 phút nhé!")
                
                with st.spinner("🤖 Đang chuyển thành giọng nói..."):
                    try:
                        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                        temp_audio.close()
                        
                        asyncio.run(tao_audio(text_input, VOICES[voice_choice], temp_audio.name))
                        
                        st.success("Hoàn tất!")
                        st.audio(temp_audio.name, format="audio/mp3")
                        
                        with open(temp_audio.name, "rb") as file:
                            st.download_button(
                                label="⬇️ Tải file Audio (.mp3) để nghe offline",
                                data=file, file_name="sach_noi.mp3", mime="audio/mp3", use_container_width=True
                            )
                    except Exception as e:
                        st.error(f"Lỗi xử lý âm thanh: {e}")
