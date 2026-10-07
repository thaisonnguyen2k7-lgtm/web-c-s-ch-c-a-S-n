import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
import PyPDF2
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

st.set_page_config(page_title="App Đọc Sách AI", page_icon="🎧", layout="centered")
st.title("🎧 Ứng Dụng Đọc Sách AI (Bản Nâng Cấp)")
st.write("Hỗ trợ đọc file: **TXT, PDF, EPUB**")

VOICES = {
    "Giọng Nữ (Hoài My - Trầm ấm, tự nhiên)": "vi-VN-HoaiMyNeural",
    "Giọng Nam (Nam Minh - Rõ ràng, mạnh mẽ)": "vi-VN-NamMinhNeural"
}

voice_choice = st.selectbox("1. Chọn giọng đọc:", list(VOICES.keys()))
# Thêm pdf và epub vào danh sách file cho phép tải lên
uploaded_file = st.file_uploader("2. 📂 Chọn file sách (txt, pdf, epub) của bạn", type=["txt", "pdf", "epub"])

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

# ---- ĐỌC NỘI DUNG FILE TẢI LÊN ----
text_input = ""
if uploaded_file is not None:
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    with st.spinner(f"Đang trích xuất văn bản từ file {file_extension.upper()}..."):
        try:
            if file_extension == "txt":
                text_input = uploaded_file.read().decode("utf-8")
                
            elif file_extension == "pdf":
                text_input = extract_text_from_pdf(uploaded_file)
                
            elif file_extension == "epub":
                # EPUB cần lưu tạm ra ổ cứng để đọc
                with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp_epub:
                    tmp_epub.write(uploaded_file.getvalue())
                    tmp_epub_path = tmp_epub.name
                text_input = extract_text_from_epub(tmp_epub_path)
                os.remove(tmp_epub_path) # Xóa file tạm
                
        except Exception as e:
            st.error(f"Lỗi khi đọc file: {e}")

text = st.text_area("Nội dung sách (bạn có thể chỉnh sửa trước khi đọc):", value=text_input, height=250)

# ---- XỬ LÝ ÂM THANH ----
async def tao_audio(text, voice, file_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(file_path)

if st.button("▶️ Tạo Sách Nói", use_container_width=True):
    if text.strip() == "":
        st.warning("⚠️ Vui lòng tải file sách hoặc nhập văn bản trước nhé!")
    else:
        # Nếu sách quá dài, AI sẽ mất nhiều thời gian, cảnh báo cho người dùng
        if len(text) > 5000:
            st.info("Sách khá dài, AI có thể mất 1-2 phút để tạo âm thanh. Bạn vui lòng kiên nhẫn nhé!")
            
        with st.spinner("🤖 AI đang phân tích và tạo giọng đọc..."):
            try:
                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                temp_audio.close()
                asyncio.run(tao_audio(text, VOICES[voice_choice], temp_audio.name))
                st.success("🎉 Đã tạo xong! Bạn có thể nghe ngay hoặc tải về.")
                st.audio(temp_audio.name, format="audio/mp3")
                
                with open(temp_audio.name, "rb") as file:
                    st.download_button(
                        label="⬇️ Tải file âm thanh này về máy (.mp3)",
                        data=file, file_name="sach_noi_ai.mp3", mime="audio/mp3", use_container_width=True
                    )
            except Exception as e:
                st.error(f"Đã xảy ra lỗi: {e}")
