# streamlit_app.py
import streamlit as st
import tempfile
import os

st.title("STL → G-code 변환기 (Streamlit Wrapper)")

st.markdown(
    """이 애플리케이션은 PyQt5 GUI 기반의 `Slicing New.py`를
    **변경 없이** 실행하도록 돕기 위한 Streamlit 래퍼입니다.
    Streamlit Cloud 환경에서는 PyQt5 GUI 창을 직접 띄울 수 없기 때문에,
    사용자는 업로드한 파이썬 파일을 **로컬**에서 실행해야 합니다.
    """
)

uploaded_file = st.file_uploader(
    "🗂 변환기 코드 업로드 (`Slicing New.py`)", type=["py"], accept_multiple_files=False
)

if uploaded_file:
    st.success("✅ 파일 업로드 완료")

    # 임시 저장 후 다운로드 링크 제공
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())

    st.info(
        "⚠ **Streamlit Cloud 환경**에서는 PyQt5 GUI가 표시되지 않습니다. "
        "아래 버튼으로 파일을 다운로드하여 **로컬 PC**에서 "
        "`python Slicing New.py` 명령으로 실행해 주세요."
    )

    st.download_button(
        label="🔽 'Slicing New.py' 다운로드",
        data=open(file_path, "rb").read(),
        file_name=uploaded_file.name,
        mime="text/x-python",
    )
