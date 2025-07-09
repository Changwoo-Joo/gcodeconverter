import streamlit as st
import numpy as np
import trimesh
import tempfile
import io
import math

st.title("🛠 STL → G-code 변환기 (상대 압출, G1 Z이동)")

uploaded_file = st.file_uploader("1️⃣ STL 파일 업로드", type=["stl"])
layer_height = st.number_input("2️⃣ 레이어 높이 (mm)", value=15.0)
feedrate = st.number_input("3️⃣ 이동 속도 (F값)", value=2000)
start_x = st.number_input("4️⃣ 시작 X 좌표", value=0.0)
start_y = st.number_input("5️⃣ 시작 Y 좌표", value=0.0)
extrusion_amount = st.number_input("6️⃣ 압출량 (mm당 E)", value=1.0)
apply_e = st.checkbox("7️⃣ E값 적용", value=False)
m30_insert = st.checkbox("8️⃣ G-code 끝에 M30 삽입", value=False)

if uploaded_file is not None:
    mesh = trimesh.load_mesh(uploaded_file, file_type='stl', force='mesh')
    bounds = mesh.bounds
    z_min, z_max = bounds[0][2], bounds[1][2]
    layers = np.arange(z_min + layer_height, z_max, layer_height)

    gcode_lines = ["; G-code using relative extrusion (M83)", "G21", "G90", "M83"]

    for z in layers:
        gcode_lines.append(f"\n; ---------- Z = {z:.3f} mm ----------")
        gcode_lines.append(f"G1 Z{z:.3f} F{int(feedrate)}")

        slice_2D = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if slice_2D is None:
            continue
        slice_2D = slice_2D.to_planar()

        if hasattr(slice_2D, 'discrete'):
            discrete_segments = slice_2D.discrete
        else:
            continue

        for path in discrete_segments:
            if len(path) < 2:
                continue

            start = path[0]
            gcode_lines.append(f"G1 X{start[0]:.3f} Y{start[1]:.3f} F{int(feedrate)}")

            for i in range(1, len(path)):
                p1, p2 = path[i - 1], path[i]
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                dist = math.sqrt(dx**2 + dy**2)

                if apply_e:
                    e_val = dist * extrusion_amount
                    gcode_lines.append(f"G1 X{p2[0]:.3f} Y{p2[1]:.3f} E{e_val:.5f}")
                else:
                    gcode_lines.append(f"G1 X{p2[0]:.3f} Y{p2[1]:.3f}")

    if m30_insert:
        gcode_lines.append("M30")

    gcode_output = "\n".join(gcode_lines)
    st.download_button("💾 G-code 다운로드", gcode_output, file_name="output.gcode", mime="text/plain")