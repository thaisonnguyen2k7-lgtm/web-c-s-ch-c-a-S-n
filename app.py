import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import fitz  # PyMuPDF

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
        text-align: justify;
    }}
    div.stButton > button {{
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border-radius: 12px;
        border: none;
        padding: 10px 24px;
        font-size: 16px;
        font-weight: bold;
    }}
    </style>
""", unsafe_allow_html=True)

# ---- BỘ XỬ LÝ EPUB ĐẶC TRỊ NHẢY CHỮ ----
def extract_text_from_epub(file_path):
    book = epub.read_epub(file_path)
    chapters = []
    
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        # Đọc lõi HTML của sách
        soup = BeautifulSoup(item.get_body_content(), 'html.parser')
        
        # 1. Xóa các thẻ rác (CSS, scripts) không phải văn bản
        for r in soup(['script', 'style', 'head', 'title', 'meta']):
            r.extract()
            
        # 2. Xử lý chính xác các ngắt dòng của HTML
        for br in soup.find_all("br"):
            br.replace_with("\n") # Đổi thẻ ngắt dòng thành ký tự xuống dòng
            
        # Thêm dấu xuống dòng sau mỗi đoạn văn (p, div, tiêu đề)
        for block in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"]):
            block.insert_after(soup.new_string("\n\n"))
            
        # 3. Hút toàn bộ chữ ra (các chữ có hiệu ứng in đậm/nghiêng sẽ được nối bằng khoảng trắng)
        text = soup.get_text(separator=' ')
        
        # 4. Dọn dẹp khoảng trắng để chữ xếp hàng ngay ngắn
        lines = text.split('\n')
        # Gom các khoảng trắng thừa ở mỗi dòng
        cleaned_lines = [' '.join(line.split()) for line in lines]
        text = '\n'.join(cleaned_lines)
        
        # Gom nhiều dấu xuống dòng liên tiếp thành tối đa 2 dấu (tạo khoảng cách đoạn văn)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        if text.strip():
            chapters.append(text.strip())
            
    return '\n\n'.join(chapters)

# ---- XỬ LÝ PDF (Giữ nguyên dùng PyMuPDF) ----
def extract_text_from_pdf(file_path):
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            blocks = page.get_text("blocks")
            for block in blocks:
                block_text = block[4].replace('\n', ' ')
                block_text = re.sub(r' +', ' ', block_text)
                text += block_text.strip() + "\n\n"
    return text.strip()

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
    st.info("👈 Bắt đầu bằng cách tải một cuốn sách (EPUB, PDF, TXT) ở góc trên bên trái.")
else:
    file_extension = uploaded_file.name.split('.')[-1].lower()
    with st.spinner("⏳ Đang giải mã và định dạng lại cấu trúc sách..."):
        try:
            if file_extension == "txt":
                text_input = uploaded_file.read().decode("utf-8")
            else:
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
                "Copy đoạn sách ở khung bên trái dán vào đây.", 
                height=250, 
                placeholder="Dán đoạn sách bạn muốn nghe vào đây..."
            )
            
            if st.button("▶️ TẠO SÁCH NÓI", use_container_width=True):
                if not doan_sach_muon_nghe.strip():
                    st.warning("⚠️ Vui lòng dán đoạn sách bạn muốn nghe vào ô trống phía trên!")
                else:
                    with st.spinner("🤖 Đang chuyển thành giọng nói..."):
                        try:
                            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                            temp_audio.close()
                            
                            asyncio.run(tao_audio(doan_sach_muon_nghe, VOICES[voice_choice], temp_audio.name))
                            
                            st.success("Hoàn tất!")
                            st.audio(temp_audio.name, format="audio/mp3")
                            
                            with open(temp_audio.name, "rb") as file:
                                st.download_button(
                                    label="⬇️ Tải file Audio",
                                    data=file, file_name="sach_noi.mp3", mime="audio/mp3", use_container_width=True
                                )
                        except Exception as e:
                            st.error(f"Lỗi xử lý âm thanh: {e}")
