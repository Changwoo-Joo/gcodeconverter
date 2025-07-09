import numpy as np
import trimesh
import os
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QWidget, QVBoxLayout, QPushButton,
    QLabel, QHBoxLayout, QLineEdit
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

class GcodeExporter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STL → G-code (E0 포함, Z/F/원점 조절 가능)")
        self.setGeometry(300, 300, 520, 320)

        layout = QVBoxLayout()

        self.label = QLabel("📂 STL → 💾 G-code 저장 (E값 포함, 폐구간 이동 시 E0)")
        layout.addWidget(self.label)

        self.load_btn = QPushButton("1️⃣ STL 파일 불러오기")
        self.load_btn.clicked.connect(self.load_stl)
        layout.addWidget(self.load_btn)

        self.export_btn = QPushButton("2️⃣ G-code 저장 위치 지정")
        self.export_btn.clicked.connect(self.choose_export_file)
        layout.addWidget(self.export_btn)

        z_layout = QHBoxLayout()
        z_layout.addWidget(QLabel("Z 간격(mm):"))
        self.z_input = QLineEdit("30")
        z_layout.addWidget(self.z_input)
        layout.addLayout(z_layout)

        f_layout = QHBoxLayout()
        f_layout.addWidget(QLabel("Feedrate (F):"))
        self.f_input = QLineEdit("2000")
        f_layout.addWidget(self.f_input)
        layout.addLayout(f_layout)

        ref_layout = QHBoxLayout()
        ref_layout.addWidget(QLabel("기준 시작점 X:"))
        self.ref_x_input = QLineEdit("0.0")
        ref_layout.addWidget(self.ref_x_input)
        ref_layout.addWidget(QLabel("Y:"))
        self.ref_y_input = QLineEdit("0.0")
        ref_layout.addWidget(self.ref_y_input)
        layout.addLayout(ref_layout)

        self.run_btn = QPushButton("3️⃣ G-code 생성 실행")
        self.run_btn.clicked.connect(self.export_gcode)
        layout.addWidget(self.run_btn)

        self.setLayout(layout)
        self.mesh = None
        self.export_path = ""

    def load_stl(self):
        path, _ = QFileDialog.getOpenFileName(self, "STL 파일 열기", "", "STL Files (*.stl)")
        if path:
            self.mesh = trimesh.load_mesh(path)
            self.label.setText(f"✅ STL 로드 완료: {os.path.basename(path)}")

    def choose_export_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "G-code 파일로 저장", "", "G-code Files (*.gcode)")
        if path:
            if not path.lower().endswith('.gcode'):
                path += ".gcode"
            self.export_path = path
            self.label.setText(f"💾 저장 위치: {os.path.basename(path)}")

    def export_gcode(self):
        if self.mesh is None or not self.export_path:
            self.label.setText("⚠ STL과 저장 위치를 먼저 선택하세요.")
            return

        try:
            z_interval = float(self.z_input.text())
            feedrate = float(self.f_input.text())
            ref_point = np.array([float(self.ref_x_input.text()), float(self.ref_y_input.text())])
        except ValueError:
            self.label.setText("⚠ 숫자 값을 정확히 입력하세요.")
            return

        mesh = self.mesh
        bounds = mesh.bounds
        min_x, min_y = bounds[0][0], bounds[0][1]
        mesh.apply_translation([-min_x, -min_y, 0])

        z_min, z_max = mesh.bounds[:, 2]
        z_heights = np.arange(z_interval, int(z_max) + 1, z_interval)

        e_total = 0.0
        extrusion_factor = 1.0  # mm당 E 증가량

        gcode_lines = ["; G-code with E extrusion and E0 after each loop", "G21", "G90", "G92 E0", "M83"]

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
                        
                        gcode_lines.append(f"G1 X{p2[0]:.3f} Y{p2[1]:.3f} E1")

                    # 폐곡선 종료 후 E0
                    gcode_lines.append("G1 E0 ; extrusion off before next loop")

        gcode_lines.append("G92 E0")
        gcode_lines.append("G1 F3000")

        with open(self.export_path, "w") as f:
            f.write("\n".join(gcode_lines))

        self.label.setText("✅ G-code 생성 완료 (각 폐곡선 후 E0 포함)")

# 실행
if __name__ == "__main__":
    app = QApplication([])
    gui = GcodeExporter()
    gui.show()
    app.exec_()
