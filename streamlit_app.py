
import streamlit as st
import numpy as np
import trimesh
import os
import io

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

st.title("🛠 STL → G-code 변환기 (E값 포함, 폐곡선 이동 시 E0)")

uploaded_file = st.file_uploader("1️⃣ STL 파일 업로드", type=["stl"])
z_interval = st.number_input("2️⃣ Z 간격 (mm)", value=30.0, step=1.0)
feedrate = st.number_input("3️⃣ Feedrate (F)", value=2000)
ref_x = st.number_input("4️⃣ 기준 시작점 X", value=0.0)
ref_y = st.number_input("5️⃣ 기준 시작점 Y", value=0.0)
extrusion_amount = st.number_input("6️⃣ 압출량 (mm당 E)", value=1.0)
apply_e = st.checkbox("7️⃣ E값 적용", value=False)
m30_insert = st.checkbox("8️⃣ G-code 끝에 M30 삽입", value=False)


if uploaded_file and st.button("7️⃣ G-code 생성 실행"):
    ext = os.path.splitext(uploaded_file.name)[1][1:].lower()
    mesh = trimesh.load_mesh(uploaded_file, file_type=ext, force='mesh')

    z_min, z_max = mesh.bounds[:, 2]
    z_heights = np.arange(z_interval, int(z_max) + 1, z_interval)

    e_total = 0.0
    extrusion_factor = 0.05  # mm당 E 증가량
    ref_point = np.array([ref_x, ref_y])
    gcode_lines = ["; G-code with optional E extrusion and E0 after each loop", "G21", "G90", "M83"]

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
            gcode_lines.append(f"G1 Z{z:.3f} F{int(feedrate)}")

            for segment in segments_3D:
                shifted, new_start = shift_to_nearest_start(segment, ref_point)
                trimmed = trim_segment_end(shifted, trim_distance=30.0)
                start = trimmed[0]

                gcode_lines.append(f"G1 F{int(feedrate)}")

                for i in range(1, len(trimmed)):
                    p1 = trimmed[i - 1]
                    p2 = trimmed[i]
                    dist = np.linalg.norm(p2[:2] - p1[:2])
                    if apply_e:
                        e_val = dist * extrusion_amount
                    gcode_lines.append(f"G1 X{p2[0]:.3f} Y{p2[1]:.3f} E{e_val:.5f}")
                    else:
                        gcode_lines.append(f"G1 X{p2[0]:.3f} Y{p2[1]:.3f}")

                

    gcode_lines.append("M83")
    gcode_lines.append("G1 F3000")

    if m30_insert:
        gcode_lines.append("M30")

    gcode_output = "\n".join(gcode_lines)
    st.success("✅ G-code 생성 완료!")
    st.download_button("💾 G-code 다운로드", gcode_output, file_name="output.gcode", mime="text/plain")
