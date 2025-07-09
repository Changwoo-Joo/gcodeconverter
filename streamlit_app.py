
import streamlit as st

st.title("STL → G-code 변환기 (E값, 압출량, M30 옵션 설정 가능)")

uploaded_file = st.file_uploader("STL 파일 업로드", type=["stl"])

apply_e = st.checkbox("E값 적용 (압출량 계산)", value=False)
extrusion_factor = st.number_input("압출량 (mm당 E값)", min_value=0.0, value=1.0, step=0.1)
insert_m30 = st.checkbox("M30 코드 삽입 (종료)", value=False)

if uploaded_file:
    import trimesh
    import numpy as np
    from io import BytesIO
    import math

    mesh = trimesh.load_mesh(uploaded_file, file_type='stl', force='mesh')

import numpy as np
import trimesh
import os
import streamlit as st
from io import BytesIO

    
    
)

def trim_segment_end(segment, trim_distance=30.0):
    segment = np.array(segment)
    total_len = np.sum(np.linalg.norm(np.diff(segment, axis=0), axis=1))
    if total_len <= trim_distance:
        return segment
    trimmed = [segment[0]]
    accumulated = 0.0
    for i in range(1, len(segment)):
        p1 = segment[i - 1]
        p2 = segment[i]
        d = np.linalg.norm(p2 - p1)
        if accumulated + d >= total_len - trim_distance:
            ratio = (total_len - trim_distance - accumulated) / d
            new_p = p1 + (p2 - p1) * ratio
            trimmed.append(new_p)
            break
        else:
            trimmed.append(p2)
            accumulated += d
    return np.array(trimmed)

def shift_to_nearest_start(segment, ref_point):
    distances = np.linalg.norm(segment[:, :2] - ref_point, axis=1)
    nearest_idx = np.argmin(distances)
    shifted_segment = np.concatenate([segment[nearest_idx:], segment[1:nearest_idx + 1]], axis=0)
    return shifted_segment, segment[nearest_idx]

def main():
    def __init__(self):
        
        
        

        

        # st.write label("📂 STL → 💾 G-code 저장 (E값 포함, 폐구간 이동 시 E0)")
        layout.addWidget(self.label)

        self.load_btn = # QPushButton (replaced)("1️⃣ STL 파일 불러오기")
        self.load_btn.clicked.connect(self.load_stl)
        layout.addWidget(self.load_btn)

        self.export_btn = # QPushButton (replaced)("2️⃣ G-code 저장 위치 지정")
        self.export_btn.clicked.connect(self.choose_export_file)
        layout.addWidget(self.export_btn)

        z_layout = QHBoxLayout()
        z_layout.addWidget(# QLabel (replaced)("Z 간격(mm):"))
        self.z_input = # QLineEdit (replaced)("30")
        z_layout.addWidget(self.z_input)
        layout.addLayout(z_layout)

        f_layout = QHBoxLayout()
        f_layout.addWidget(# QLabel (replaced)("Feedrate (F):"))
        self.f_input = # QLineEdit (replaced)("2000")
        f_layout.addWidget(self.f_input)
        layout.addLayout(f_layout)

        ref_layout = QHBoxLayout()
        ref_layout.addWidget(# QLabel (replaced)("기준 시작점 X:"))
        self.ref_x_input = # QLineEdit (replaced)("0.0")
        ref_layout.addWidget(self.ref_x_input)
        ref_layout.addWidget(# QLabel (replaced)("Y:"))
        self.ref_y_input = # QLineEdit (replaced)("0.0")
        ref_layout.addWidget(self.ref_y_input)
        layout.addLayout(ref_layout)

        self.run_btn = # QPushButton (replaced)("3️⃣ G-code 생성 실행")
        self.run_btn.clicked.connect(self.export_gcode)
        layout.addWidget(self.run_btn)

        
        self.mesh = None
        self.export_path = ""

    def load_stl(self):
        path, _ = # 파일 업로드 handled by st.file_uploader "STL 파일 열기", "", "STL Files (*.stl)")
        if path:
            self.mesh = trimesh.load_mesh(path)
            st.write(f"✅ STL 로드 완료: {os.path.basename(path)}")

    def choose_export_file(self):
        path, _ = # 파일 저장 handled by st.download_button "G-code 파일로 저장", "", "G-code Files (*.gcode)")
        if path:
            if not path.lower().endswith('.gcode'):
                path += ".gcode"
            self.export_path = path
            st.write(f"💾 저장 위치: {os.path.basename(path)}")

    def export_gcode(self):
        if self.mesh is None or not self.export_path:
            st.write("⚠ STL과 저장 위치를 먼저 선택하세요.")
            return

        try:
            z_interval = float(self.z_input.text())
            feedrate = float(self.f_input.text())
            ref_point = np.array([float(self.ref_x_input.text()), float(self.ref_y_input.text())])
        except ValueError:
            st.write("⚠ 숫자 값을 정확히 입력하세요.")
            return

        mesh = self.mesh
        z_min, z_max = mesh.bounds[:, 2]
        z_heights = np.arange(z_interval, int(z_max) + 1, z_interval)

        e_total = 0.0
        extrusion_factor = 0.05  # mm당 E 증가량

        gcode_lines = ["; G-code with E extrusion and E0 after each loop", "G21", "G90", "G92 E0"]

        for z in z_heights:
            section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if section is not None:
                slice_2D, to_3D_matrix = section.to_2D()
                discrete_segments = slice_2D.discrete
                segments_3D = []
                for seg in discrete_segments:
                    seg = np.array(seg)
                    ones = np.ones((seg.shape[0], 1))
                    seg_hom = np.hstack([seg, np.zeros((seg.shape[0], 1)), ones])
                    seg_3D = (to_3D_matrix @ seg_hom.T).T[:, :3]
                    segments_3D.append(seg_3D)

                gcode_lines.append(f"\n; ---------- Z = {z} mm ----------")
                gcode_lines.append(f"G0 Z{z:.3f} F1500")

                for segment in segments_3D:
                    shifted, new_start = shift_to_nearest_start(segment, ref_point)
                    trimmed = trim_segment_end(shifted, trim_distance=30.0)
                    start = trimmed[0]

                    gcode_lines.append(f"G0 X{start[0]:.3f} Y{start[1]:.3f} F3000")
                    gcode_lines.append(f"G1 F{int(feedrate)}")

                    for i in range(1, len(trimmed)):
                        p1 = trimmed[i - 1]
                        p2 = trimmed[i]
                        dist = np.linalg.norm(p2[:2] - p1[:2])
                        e_total += dist * extrusion_factor if apply_e else 0
                        gcode_lines.append(f"G1 X{p2[0]:.3f} Y{p2[1]:.3f} E{e_total:.5f}")

                    # 폐곡선 종료 후 E0
                    gcode_lines.append("G1 E0 ; extrusion off before next loop")

        gcode_lines.append("G92 E0")
        gcode_lines.append("G1 F3000")

        with open(self.export_path, "w") as f:
            f.write("\n".join(gcode_lines))

        st.write("✅ G-code 생성 완료 (각 폐곡선 후 E0 포함)")

# 실행


if __name__ == "__main__":
    main()
    
    
    
    
