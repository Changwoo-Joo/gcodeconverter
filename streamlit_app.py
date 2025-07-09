
import streamlit as st
import trimesh
import numpy as np
from io import StringIO

st.title("STL → G-code 변환기")

uploaded_file = st.file_uploader("STL 파일을 업로드하세요", type=["stl"])

use_e = st.checkbox("E값 적용 (상대 압출 방식, M83)")
extrusion_per_mm = st.number_input("압출량 (mm당 E값)", value=1.0, step=0.1)
add_m30 = st.checkbox("M30 코드 삽입")
z_height = st.number_input("Z 슬라이스 높이 (mm)", value=30.0, step=1.0)
feedrate = st.number_input("Feedrate (이송속도)", value=2000, step=100)
trim_distance = st.number_input("Trim 거리 (종료점 앞 거리, mm)", value=30.0, step=1.0)

if uploaded_file:
    mesh = trimesh.load_mesh(uploaded_file, force='mesh')
    bounds = mesh.bounds
    minx, miny, _ = bounds[0]

    slices = np.arange(0, bounds[1][2], z_height)
    gcode = StringIO()
    gcode.write("; G-code with optional E extrusion and E0 after each loop\n")
    gcode.write("G21\nG90\n")
    if use_e:
        gcode.write("M83\n")
    gcode.write("G92 E0\n")

    for z in slices:
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section is None:
            continue
        slice_2D, _ = section.to_planar()
        paths = slice_2D.discrete

        for path in paths:
            total_len = np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1))
            if total_len < trim_distance:
                continue

            trimmed_len = 0
            gcode.write(f"; ---------- Z = {z:.2f} mm ----------\n")
            gcode.write(f"G1 Z{z:.3f} F{feedrate:.0f}\n")

            for i in range(len(path)):
                p1 = path[i]
                p2 = path[(i + 1) % len(path)]
                move_vec = np.array(p2) - np.array(p1)
                dist = np.linalg.norm(move_vec)
                trimmed_len += dist

                if trimmed_len >= total_len - trim_distance:
                    break

                x, y = p2
                x -= minx
                y -= miny

                if use_e:
                    e_value = extrusion_per_mm
                    gcode.write(f"G1 X{x:.3f} Y{y:.3f} E{e_value:.5f} F{feedrate:.0f}\n")
                else:
                    gcode.write(f"G1 X{x:.3f} Y{y:.3f} F{feedrate:.0f}\n")

    if add_m30:
        gcode.write("M30\n")

    st.download_button("💾 G-code 다운로드", gcode.getvalue(), file_name="output.gcode")
