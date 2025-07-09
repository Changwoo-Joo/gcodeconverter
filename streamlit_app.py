
import streamlit as st
import numpy as np
import trimesh
import math
from io import StringIO

st.title("STL → G-code 변환기")

uploaded_file = st.file_uploader("STL 파일을 업로드하세요", type=["stl"])

apply_e = st.checkbox("E값 적용 (상대 압출 방식, M83)", value=False)
extrusion_factor = st.number_input("압출량 (mm당 E값)", min_value=0.0, value=1.0, step=0.1)
insert_m30 = st.checkbox("M30 코드 삽입", value=False)
z_height = st.number_input("Z 슬라이스 높이 (mm)", min_value=0.1, value=30.0, step=0.1)
feedrate = st.number_input("Feedrate (이송속도)", min_value=1, value=2000, step=100)

if uploaded_file:
    mesh = trimesh.load_mesh(uploaded_file, file_type='stl', force='mesh')
    bounds = mesh.bounds
    z_min, z_max = bounds[0][2], bounds[1][2]
    gcode_lines = []

    gcode_lines.append("; G-code with optional E extrusion and E0 after each loop")
    gcode_lines.append("G21")  # mm
    gcode_lines.append("G90")  # absolute positioning
    gcode_lines.append("M83" if apply_e else "M82")  # extrusion mode

    z_values = np.arange(z_min + z_height, z_max, z_height)
    for z in z_values:
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section is None:
            continue
        slice_2D, _ = section.to_planar()
        paths = slice_2D.discrete
        for path in paths:
            e_value = 0
            for i, point in enumerate(path):
                x, y = point
                if i == 0:
                    gcode_lines.append(f"G1 Z{z:.3f} F{feedrate}")
                    gcode_lines.append(f"G1 X{x:.3f} Y{y:.3f} F{feedrate}")
                else:
                    prev = path[i - 1]
                    dist = math.dist(prev, point)
                    e_value = extrusion_factor * dist if apply_e else 0
                    gline = f"G1 X{x:.3f} Y{y:.3f}"
                    if apply_e:
                        gline += f" E{e_value:.5f}"
                    gline += f" F{feedrate}"
                    gcode_lines.append(gline)
            if apply_e:
                gcode_lines.append("G1 E0")

    if insert_m30:
        gcode_lines.append("M30")

    gcode_text = "\n".join(gcode_lines)
    st.download_button("💾 G-code 다운로드", gcode_text, file_name="output.gcode")
