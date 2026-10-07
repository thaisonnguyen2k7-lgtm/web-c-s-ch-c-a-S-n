import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
import pdfplumber
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re

# ---- CẤU HÌNH TRANG LỚN ----
st.set_page_config(page_title="Reader & AudioBook AI", page_icon="📖", layout="wide", initial_sidebar_state="collapsed")

if 'theme' not in st.session_state:
    st.session_state.theme = 'Mặc định (Trắng dịu)'
if 'font_size' not in st.session_state:
    st.session_state.font_size = 18

THEMES = {
    'Mặc định (Trắng dịu)': {'bg': '#fcfcfc', 'text': '#333333'},
    'Sepia (Vàng ấm bảo vệ mắt)': {'bg': '#f4ecd8', 'text': '#5b4636'},
    'Dark Mode (Đọc ban đêm)': {'bg': '#1e1e1e', 'text': '#e0e0e0'}
}

current_theme = THEMES[st.session_state.theme]

st.markdown(f"""
    <style>
    .reading-box {{
        background-color: {current_theme['bg']};
        color: {current_theme['text']};
        padding: 40px;
        border-radius: 12px;
        font-family: 'Georgia', serif;
        font-size: {st.session_state.font_size}px;
        line-height: 1.8;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        height: 70vh;
        overflow-y: scroll;
        margin-bottom: 20px;
        text-align: justify; /* Căn đều 2 bên cho đẹp */
    }}
    div.stButton > button {{
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border-radius: 12px;
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

# ---- BỘ LỌC DỌN DẸP VĂN BẢN (CHỐNG NHẢY CHỮ) ----
def clean_text(text):
    # 1. Nối các câu bị ngắt xuống dòng vô cớ ở giữa đoạn
    # Nếu dòng kết thúc không phải dấu chấm, phẩy, hỏi, than -> nối với dòng dưới
    text = re.sub(r'([^\.\!\?\:\;\,])\n([a-zà-ỹ])', r'\1 \2', text)
    
    # 2. Xóa các khoảng trắng lặp lại (ví dụ: "chữ     bị    nhảy")
    text = re.sub(r' +', ' ', text)
    
    # 3. Tách các câu bị dính liền do lỗi PDF (ví dụ: "chấm.Viết")
    text = re.sub(r'([a-zà-ỹ])\.([A-ZÀ-Ỹ])', r'\1. \2', text)
    
    # 4. Xóa các ký tự ngắt trang, ký tự lạ
    text = text.replace('\x0c', '')
    
    return text.strip()

# ---- CÁC HÀM XỬ LÝ FILE MỚI ----
def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # layout=True giúp giữ đúng thứ tự cột, đoạn văn
            page_text = page.extract_text(layout=True) 
            if page_text:
                text += page_text + "\n"
    return clean_text(text)

def extract_text_from_epub(file_path):
    book = epub.read_epub(file_path)
    text = ""
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_body_content(), 'html.parser')
        text += soup.get_text() + "\n"
    return clean_text(text)

async def tao_audio(text, voice, file_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(file_path)

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    uploaded_file = st.file_uploader("📂 Tải sách (TXT, PDF, EPUB)", type=["txt", "pdf", "epub"], label_visibility="collapsed")

with col2:
    cols_control = st.columns([2, 1])
    with cols_control[0]:
        selected_theme = st.selectbox("🎨 Chế độ đọc:", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme))
        if selected_theme != st.session_state.theme:
            st.session_state.theme = selected_theme
            st.rerun()
            
    with cols_control[1]:
        new_size = st.number_input("Cỡ chữ:", min_value=12, max_value=36, value=st.session_state.font_size, step=2)
        if new_size != st.session_state.font_size:
            st.session_state.font_size = new_size
            st.rerun()

with col3:
    VOICES = {"Giọng Nữ (Hoài My)": "vi-VN-HoaiMyNeural", "Giọng Nam (Nam Minh)": "vi-VN-NamMinhNeural"}
    voice_choice = st.selectbox("🗣️ Chọn giọng đọc:", list(VOICES.keys()))

st.markdown("---")

text_input = ""
if uploaded_file is None:
    st.info("👈 Bắt đầu bằng cách tải một cuốn sách hoặc file tài liệu của bạn ở góc trên bên trái.")
else:
    file_extension = uploaded_file.name.split('.')[-1].lower()
    with st.spinner("⏳ Đang dọn dẹp và sắp xếp lại văn bản..."):
        try:
            if file_extension == "txt":
                text_input = clean_text(uploaded_file.read().decode("utf-8"))
            else:
                # PDF và EPUB cần lưu tạm để pdfplumber và ebooklib đọc
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                if file_extension == "pdf":
                    text_input = extract_text_from_pdf(tmp_file_path)
                elif file_extension == "epub":
                    text_input = extract_text_from_epub(tmp_file_path)
                    
                os.remove(tmp_file_path)
        except Exception as e:
            st.error(f"Lỗi đọc file: {e}")

    if text_input:
        main_col1, main_col2 = st.columns([6, 4])
        
        with main_col1:
            st.markdown(f'<div class="reading-box">{text_input.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
            
        with main_col2:
            st.subheader("🎧 Trình phát Audio Siêu Tốc")
            doan_sach_muon_nghe = st.text_area(
                "Copy đoạn sách ở khung bên trái dán vào đây (Dưới 3000 chữ sẽ tạo trong 5 giây).", 
                height=250, 
                placeholder="Dán đoạn sách bạn muốn nghe vào đây..."
            )
            
            if st.button("▶️ TẠO SÁCH NÓI", use_container_width=True):
                if not doan_sach_muon_nghe.strip():
                    st.warning("⚠️ Vui lòng dán đoạn sách bạn muốn nghe vào ô trống phía trên!")
                else:
                    if len(doan_sach_muon_nghe) > 5000:
                        st.warning("Đoạn văn này khá dài, có thể mất khoảng 30s - 1 phút. Để siêu tốc, hãy dán từng chương một!")
                    
                    with st.spinner("🤖 Đang chuyển thành giọng nói..."):
                        try:
                            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                            temp_audio.close()
                            
                            asyncio.run(tao_audio(clean_text(doan_sach_muon_nghe), VOICES[voice_choice], temp_audio.name))
                            
                            st.success("Hoàn tất!")
                            st.audio(temp_audio.name, format="audio/mp3")
                            
                            with open(temp_audio.name, "rb") as file:
                                st.download_button(
                                    label="⬇️ Tải file Audio",
                                    data=file, file_name="sach_noi.mp3", mime="audio/mp3", use_container_width=True
                                )
                        except Exception as e:
                            st.error(f"Lỗi xử lý âm thanh: {e}")
