
import streamlit as st
import trimesh
import numpy as np

st.title("STL → G-code 변환기")

uploaded_file = st.file_uploader("STL 파일을 업로드하세요", type=["stl"])

apply_e = st.checkbox("E값 적용 (상대 압출 방식, M83)")
extrusion_amount = st.number_input("압출량 (mm당 E값)", min_value=0.0, value=1.0, step=0.1)
insert_m30 = st.checkbox("M30 코드 삽입")
z_height = st.number_input("Z 슬라이스 높이 (mm)", min_value=0.01, value=30.0, step=1.0)
feedrate = st.number_input("Feedrate (이송속도)", min_value=1, value=2000, step=100)
trim_length = st.number_input("Trim 거리 (시작점 → 종료점 거리, mm)", min_value=0.0, value=30.0, step=1.0)

if uploaded_file:
    mesh = trimesh.load_mesh(uploaded_file, file_type='stl', force='mesh')
    bounds = mesh.bounds
    min_xy = bounds[0][:2]
    z_min, z_max = bounds[0][2], bounds[1][2]

    z_slices = np.arange(z_min, z_max + z_height, z_height)
    lines = []

    if apply_e:
        lines.append("M83")
    lines.append("G21")
    lines.append("G90")

    for z in z_slices:
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section is None:
            continue
        slice_2D, _ = section.to_planar()
        discrete_segments = slice_2D.discrete

        lines.append(f"; ---------- Z = {z:.2f} mm ----------")
        lines.append(f"G1 Z{z:.3f} F{feedrate}")

        for loop in discrete_segments:
            if len(loop) < 2:
                continue

            distances = np.linalg.norm(np.diff(loop, axis=0), axis=1)
            cum_distances = np.cumsum(distances)
            total_length = cum_distances[-1]

            # Trim 적용 여부
            if trim_length > 0.0 and total_length > trim_length:
                cutoff_index = np.searchsorted(cum_distances, total_length - trim_length)
                loop = loop[:cutoff_index + 1]

            loop -= min_xy
            loop = loop.astype(float)

            if apply_e:
                lines.append(f"G1 X{loop[0][0]:.3f} Y{loop[0][1]:.3f} E0.0")
            else:
                lines.append(f"G1 X{loop[0][0]:.3f} Y{loop[0][1]:.3f}")

            for i in range(1, len(loop)):
                x, y = loop[i]
                if apply_e:
                    lines.append(f"G1 X{x:.3f} Y{y:.3f} E{extrusion_amount:.5f}")
                else:
                    lines.append(f"G1 X{x:.3f} Y{y:.3f}")

    if insert_m30:
        lines.append("M30")

    gcode = "\n".join(lines)
    st.download_button("G-code 다운로드", gcode, file_name="output.gcode")
