
import streamlit as st
import trimesh
import numpy as np
import io

st.title("3D G-code Generator (Fixed Version)")
uploaded_file = st.file_uploader("STL 파일 업로드", type=['stl'])

z_height = st.number_input("Z 슬라이싱 높이(mm)", value=30.0, step=1.0)
feedrate = st.number_input("Feedrate (F)", value=2000)
extrude_amount = st.number_input("압출량 (E/mm)", value=1.0)
use_e = st.checkbox("E값 적용", value=False)
insert_m30 = st.checkbox("M30 코드 삽입", value=False)
trim_distance = st.number_input("Trim 거리 (mm)", value=30.0)

if uploaded_file:
    mesh = trimesh.load_mesh(uploaded_file, file_type='stl', force='mesh')
    mesh.apply_translation(-mesh.bounds[0])  # 음수 좌표 제거

    z_values = np.arange(mesh.bounds[0][2], mesh.bounds[1][2], z_height)

    gcode = []
    gcode.append("; G-code with optional E extrusion")
    gcode.append("G21")
    gcode.append("G90")
    if use_e:
        gcode.append("M83")

    for z in z_values:
        gcode.append(f"; ---------- Z = {z:.1f} mm ----------")
        gcode.append(f"G1 Z{z:.3f} F{feedrate}")
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section is None:
            continue
        slice_2D, _ = section.to_planar()
        paths = slice_2D.discrete
        for path in paths:
            if len(path) < 2:
                continue
            total_dist = sum(np.linalg.norm(np.array(path[i + 1]) - np.array(path[i])) for i in range(len(path) - 1))
            trim = min(trim_distance, total_dist - 1e-6)
            dist_accum = 0
            for i in range(len(path) - 1):
                p1 = np.array(path[i])
                p2 = np.array(path[i + 1])
                segment = p2 - p1
                dist = np.linalg.norm(segment)
                if i == 0:
                    gcode.append(f"G1 X{p1[0]:.3f} Y{p1[1]:.3f} F{feedrate}")
                dist_accum += dist
                if dist_accum >= (total_dist - trim):
                    break
                line = f"G1 X{p2[0]:.3f} Y{p2[1]:.3f}"
                if use_e:
                    line += f" E{extrude_amount:.5f}"
                line += f" F{feedrate}"
                gcode.append(line)

    if insert_m30:
        gcode.append("M30")

    gcode_text = "\n".join(gcode)
    st.download_button("G-code 다운로드", gcode_text, file_name="output.gcode")
