import numpy as np
import trimesh
import os
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QWidget, QVBoxLayout, QPushButton,
    QLabel, QHBoxLayout, QLineEdit, QCheckBox
)

# ------------------------------------------------------------
#  Helper functions
# ------------------------------------------------------------
def trim_segment_end(segment, trim_distance=30.0):
    segment = np.array(segment)
    total_len = np.sum(np.linalg.norm(np.diff(segment, axis=0), axis=1))
    if total_len <= trim_distance:
        return segment
    trimmed = [segment[0]]
    acc = 0.0
    for i in range(1, len(segment)):
        p1, p2 = segment[i - 1], segment[i]
        d = np.linalg.norm(p2 - p1)
        if acc + d >= total_len - trim_distance:
            r = (total_len - trim_distance - acc) / d
            trimmed.append(p1 + (p2 - p1) * r)
            break
        trimmed.append(p2)
        acc += d
    return np.array(trimmed)

def simplify_segment(segment, min_dist):
    simplified = [segment[0]]
    for pt in segment[1:-1]:
        if np.linalg.norm(pt[:2] - simplified[-1][:2]) >= min_dist:
            simplified.append(pt)
    simplified.append(segment[-1])
    return np.array(simplified)

def shift_to_nearest_start(segment, ref_point):
    idx = np.argmin(np.linalg.norm(segment[:, :2] - ref_point, axis=1))
    return np.concatenate([segment[idx:], segment[1:idx + 1]], axis=0), segment[idx]

# ------------------------------------------------------------
#  GUI
# ------------------------------------------------------------
class GcodeExporter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STL → G-code (통합 버전)")
        self.setGeometry(300, 300, 620, 570)

        lay = QVBoxLayout()
        self.label = QLabel("📂 STL → 💾 G-code (옵션 선택 후 ‘3️⃣’ 실행)")
        lay.addWidget(self.label)

        # 파일 로드/저장
        self.load_btn = QPushButton("1️⃣ STL 파일 불러오기")
        self.load_btn.clicked.connect(self.load_stl)
        lay.addWidget(self.load_btn)

        self.export_btn = QPushButton("2️⃣ G-code 저장 위치 지정")
        self.export_btn.clicked.connect(self.choose_export_file)
        lay.addWidget(self.export_btn)

        # Z 간격
        z_lay = QHBoxLayout(); z_lay.addWidget(QLabel("Z 간격(mm):"))
        self.z_input = QLineEdit("30"); z_lay.addWidget(self.z_input); lay.addLayout(z_lay)

        # Feedrate
        f_lay = QHBoxLayout(); f_lay.addWidget(QLabel("Feedrate (F):"))
        self.f_input = QLineEdit("2000"); f_lay.addWidget(self.f_input); lay.addLayout(f_lay)

        # 기준 시작점
        ref_lay = QHBoxLayout()
        ref_lay.addWidget(QLabel("기준 시작점 X:")); self.ref_x = QLineEdit("0.0"); ref_lay.addWidget(self.ref_x)
        ref_lay.addWidget(QLabel("Y:")); self.ref_y = QLineEdit("0.0"); ref_lay.addWidget(self.ref_y)
        lay.addLayout(ref_lay)

        # 옵션 ─ E, 시작E, E0
        self.e_checkbox = QCheckBox("E값 삽입 (경로 상대)"); lay.addWidget(self.e_checkbox)
        self.start_e_checkbox = QCheckBox("폐곡선 시작점 E값 삽입"); lay.addWidget(self.start_e_checkbox)
        start_e_lay = QHBoxLayout()
        start_e_lay.addWidget(QLabel("시작점 E값:"))
        self.start_e_input = QLineEdit("0.1"); start_e_lay.addWidget(self.start_e_input)
        lay.addLayout(start_e_lay)
        self.e0_checkbox = QCheckBox("폐곡선 종료 시 E0 삽입"); lay.addWidget(self.e0_checkbox)

        # 노즐 반지름(트리밍)
        trim_lay = QHBoxLayout()
        trim_lay.addWidget(QLabel("노즐 반지름(mm):"))
        self.trim_input = QLineEdit("30.0"); trim_lay.addWidget(self.trim_input)
        lay.addLayout(trim_lay)

        # 최소 점 간 거리
        spacing_lay = QHBoxLayout()
        spacing_lay.addWidget(QLabel("최소 점 간 거리(mm):"))
        self.spacing_input = QLineEdit("3.0"); spacing_lay.addWidget(self.spacing_input)
        lay.addLayout(spacing_lay)

        # 레이어-시작점 최단거리 옵션
        self.auto_start_checkbox = QCheckBox("이전 레이어 시작점 기준 최단거리 위치에서 다음 레이어 시작")
        lay.addWidget(self.auto_start_checkbox)

        # M30
        self.m30_checkbox = QCheckBox("종료 시 M30 추가"); lay.addWidget(self.m30_checkbox)

        # 실행
        self.run_btn = QPushButton("3️⃣ G-code 생성 실행")
        self.run_btn.clicked.connect(self.export_gcode)
        lay.addWidget(self.run_btn)

        self.setLayout(lay)
        self.mesh, self.export_path = None, ""

    # ------------- 파일 I/O ------------- #
    def load_stl(self):
        path, _ = QFileDialog.getOpenFileName(self, "STL 파일 열기", "", "STL Files (*.stl)")
        if path:
            self.mesh = trimesh.load_mesh(path)
            self.label.setText(f"✅ STL 로드 완료: {os.path.basename(path)}")

    def choose_export_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "G-code 파일로 저장", "", "G-code Files (*.gcode)")
        if path:
            if not path.lower().endswith(".gcode"):
                path += ".gcode"
            self.export_path = path
            self.label.setText(f"💾 저장 위치: {os.path.basename(path)}")

    # ------------- G-code 생성 ------------- #
    def export_gcode(self):
        if self.mesh is None or not self.export_path:
            self.label.setText("⚠ STL과 저장 위치를 먼저 선택하세요.")
            return

        # 입력값 파싱
        try:
            z_int        = float(self.z_input.text())
            feed         = int(float(self.f_input.text()))
            ref_pt_user  = np.array([float(self.ref_x.text()), float(self.ref_y.text())])
            start_e_val  = float(self.start_e_input.text())
            trim_dist    = float(self.trim_input.text())
            min_spacing  = float(self.spacing_input.text())
        except ValueError:
            self.label.setText("⚠ 숫자 값을 정확히 입력하세요.")
            return

        # 옵션 플래그
        e_on        = self.e_checkbox.isChecked()
        start_e_on  = self.start_e_checkbox.isChecked() and e_on
        e0_on       = self.e0_checkbox.isChecked() and e_on
        auto_start  = self.auto_start_checkbox.isChecked()
        extrusion_k = 0.05  # mm당 E증가

        # 기본 헤더
        g = ["; *** Generated by STL→G-code Exporter (통합) ***", "G21", "G90"]
        if e_on:
            g.append("M83")

        z_max = self.mesh.bounds[1, 2]
        prev_start_xy = None  # 이전 레이어 시작점 저장

        # 레이어 루프
        for z in np.arange(z_int, int(z_max) + 1, z_int):
            sec = self.mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if sec is None:
                continue
            slice2D, to3D = sec.to_2D()
            segments = []
            for seg in slice2D.discrete:
                seg = np.array(seg)
                seg3d = (to3D @ np.hstack([seg, np.zeros((len(seg), 1)), np.ones((len(seg), 1))]).T).T[:, :3]
                segments.append(seg3d)

            if not segments:
                continue
            g.append(f"\n; ---------- Z = {z:.1f} mm ----------")

            # ----------- 레이어 시작점 선택 ----------- #
            if auto_start and prev_start_xy is not None:
                dists = [np.linalg.norm(s[0][:2] - prev_start_xy) for s in segments]
                first_idx = int(np.argmin(dists))
                segments = segments[first_idx:] + segments[:first_idx]
                ref_pt_layer = prev_start_xy
            else:
                ref_pt_layer = ref_pt_user

            # 세그먼트 처리
            for i_seg, seg3d in enumerate(segments):
                shifted, _ = shift_to_nearest_start(seg3d, ref_pt_layer)
                trimmed     = trim_segment_end(shifted, trim_dist)
                simplified  = simplify_segment(trimmed, min_spacing)
                start       = simplified[0]

                # 시작점 이동
                g.append(f"G01 F{feed}")
                if start_e_on:
                    g.append(f"G01 X{start[0]:.3f} Y{start[1]:.3f} Z{z:.3f} E{start_e_val:.5f}")
                else:
                    g.append(f"G01 X{start[0]:.3f} Y{start[1]:.3f} Z{z:.3f}")

                # 실제 경로
                for p1, p2 in zip(simplified[:-1], simplified[1:]):
                    dist = np.linalg.norm(p2[:2] - p1[:2])
                    if e_on:
                        g.append(f"G01 X{p2[0]:.3f} Y{p2[1]:.3f} E{dist * extrusion_k:.5f}")
                    else:
                        g.append(f"G01 X{p2[0]:.3f} Y{p2[1]:.3f}")

                if e0_on:
                    g.append("G01 E0")

                # 첫 세그먼트였으면 prev_start_xy 업데이트
                if i_seg == 0:
                    prev_start_xy = start[:2]

        g.append(f"G01 F{feed}")
        if self.m30_checkbox.isChecked():
            g.append("M30")

        # 파일 저장
        with open(self.export_path, "w") as f:
            f.write("\n".join(g))
        self.label.setText("✅ G-code 생성 완료")

# ------------------------------------------------------------
#  실행
# ------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication([])
    exporter = GcodeExporter()
    exporter.show()
    app.exec_()
