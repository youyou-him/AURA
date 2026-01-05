import operator
from typing import Annotated, TypedDict, Union, List
from langgraph.graph import StateGraph, END
import os  
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

from PIL import Image, ImageDraw 
from src.agents.vision import run_vision_analysis
from src.agents.planner import run_planner

# 1. 상태(State) 정의
class MagazineState(TypedDict):
    user_input: str
    is_safe: bool = True
    vision_result: str = ""
    editor_result: str = ""
    strategy: str = ""
    html_code: str = ""
    critique_score: int = 0
    image_path: str
    retry_count: Annotated[int, operator.add] = 0 

# 2. 노드(Nodes) 정의
def intent_router(state: MagazineState):
    print("--- (1) 의도 파악 중 ---")
    if "만들어" in state["user_input"]:
        return {"user_input": state["user_input"]}
    return {"user_input": "chitchat"}

def safety_filter(state: MagazineState):
    print("--- (2) 유해성 검사 중 ---")
    is_safe = "나쁜말" not in state["user_input"]
    return {"is_safe": is_safe}

def vision_agent(state: MagazineState):
    print("--- (3) 사진 분석 중 (Parallel) ---")
    return run_vision_analysis(state)

def editor_agent(state: MagazineState):
    print("--- (4) 원고 작성 중 (Parallel) ---")
    return {"editor_result": "이것은 잡지의 멋진 원고입니다."}

def art_director(state: MagazineState):
    print("--- (5) 전략 수립 중 ---")
    # 병렬 노드들이 끝난 후 실행됨
    return {"strategy": "모던 & 미니멀 레이아웃 결정"}

def publisher(state: MagazineState):
    print(f"--- (6) HTML 코딩 중 (시도 횟수: {state['retry_count'] + 1}) ---")
    return {"html_code": "<html>...</html>", "retry_count": 1}

def critique(state: MagazineState):
    print("--- (7) 품질 검수 중 ---")
    score = 100 if state["retry_count"] >= 2 else 40
    return {"critique_score": score}

def ux_formatter(state: MagazineState):
    print("--- (8) 최종 변환 중 ---")
    return {"html_code": "✨ 최종 최적화된 HTML ✨"}

def fallback(state: MagazineState):
    print("--- (9) 일반 대화 또는 거절 응답 ---")
    return {}

# 3. 그래프(Graph) 구성
workflow = StateGraph(MagazineState)

# 노드 추가
workflow.add_node("intent_router", intent_router)
workflow.add_node("safety_filter", safety_filter)
workflow.add_node("vision_agent", vision_agent)
workflow.add_node("editor_agent", editor_agent)
workflow.add_node("planner", run_planner)
workflow.add_node("art_director", art_director)
workflow.add_node("publisher", publisher)
workflow.add_node("critique", critique)
workflow.add_node("ux_formatter", ux_formatter)
workflow.add_node("fallback", fallback)

# 엣지 연결
workflow.set_entry_point("intent_router")

# (1) Intent Router 조건부 분기
workflow.add_conditional_edges(
    "intent_router",
    lambda x: "create" if "만들어" in x["user_input"] else "fallback",
    {"create": "safety_filter", "fallback": "fallback"}
)

# [수정된 부분] (2) Safety Filter 조건부 분기 (병렬 처리 로직 변경)
# 딕셔너리 매핑 대신, 함수가 직접 실행할 노드 리스트를 반환하게 함
def route_after_safety(state):
    if state["is_safe"]:
        # 안전하면 병렬로 실행할 노드들의 리스트 반환
        return ["vision_agent", "editor_agent"]
    else:
        # 안전하지 않으면 단일 노드 반환 (리스트로 감싸도 되고 안 해도 됨)
        return "fallback"

workflow.add_conditional_edges(
    "safety_filter",
    route_after_safety
    # path_map(딕셔너리) 생략: 함수 리턴값이 실제 노드 이름과 일치하므로 필요 없음
)

# 병렬 처리된 결과를 합치기 (Fan-in)
# vision_agent와 editor_agent가 모두 끝나면 art_director가 실행됨
workflow.add_edge("vision_agent", "art_director")
workflow.add_edge("editor_agent", "art_director")

workflow.add_edge("art_director", "publisher")
workflow.add_edge("publisher", "critique")

# (7) Critique 루프 분기
workflow.add_conditional_edges(
    "critique",
    lambda x: "pass" if x["critique_score"] >= 80 else "fail",
    {"pass": "ux_formatter", "fail": "publisher"}
)

workflow.add_edge("ux_formatter", END)
workflow.add_edge("fallback", END)

# 앱 컴파일
app = workflow.compile()

# # 정상 케이스 테스트
# print("=== 테스트 시작 ===")
# inputs = {
#     "user_input": "힙한 나이키 화보 스타일로 만들어줘", 
#         "image_path": temp_filename, # 규리님이 가지고 계신 사진 경로
#         "is_safe": True, 
#         "retry_count": 0
#     }
# for output in app.stream(inputs):
#     # stream 출력은 각 노드의 수행 결과를 보여줌
#     for key, value in output.items():
#         print(f"✅ Node '{key}': {value}")
#     print("-" * 20)


# --- 4. Streamlit UI 적용 ---
st.set_page_config(page_title="AI Magazine Generator Test", layout="wide")
st.title("🤖 Magazine Agent Lab (Vision 집중 테스트)")

with st.sidebar:
    st.header("입력 설정")
    user_input = st.text_area("요청사항", "힙한 나이키 화보 스타일로 만들어줘")
    uploaded_file = st.file_uploader("이미지 업로드", type=['png', 'jpg', 'jpeg'])
    start_btn = st.button("매거진 생성 시작! 🚀")

if start_btn:
    if uploaded_file:
        # 1. 파일 임시 저장 (vision_agent가 image_path를 사용하므로)
        temp_filename = f"temp_{uploaded_file.name}"
        with open(temp_filename, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        # 2. 초기 상태 설정
        initial_state = {
            "user_input": user_input,
            "image_path": temp_filename,
            "is_safe": True,
            "retry_count": 0
        }

        final_html = None

        # 3. 에이전트 실행 및 로그 시각화
        with st.status("🔍 Vision Agent가 이미지를 심층 분석 중입니다...", expanded=True) as status:
            for step in app.stream(initial_state):
                for node_name, node_output in step.items():
                    # 👈 규리님이 만든 Vision Agent가 완료되었을 때
                    if node_name == "vision_agent":
                        st.success("✅ Vision Agent: 고급 디자인 지능 데이터 추출 완료")
                        res_str = node_output.get("vision_result", "{}")
                        
                        try:
                            res_json = json.loads(res_str)
                            metadata = res_json.get("metadata", {}) # 안전하게 메타데이터 가져오기

                            st.divider()
                            st.header("📊 Vision Agent 최종 분석 보고서")

                            # 1. 시각화 (Safe Zone)
                            st.subheader("📍 Safe Zone 시각화 확인")
                            raw_img = Image.open(initial_state["image_path"]).convert("RGB")
                            draw = ImageDraw.Draw(raw_img)
                            w, h = raw_img.size
                            zones = res_json.get('space_analysis', [])
                            for i, box in enumerate(zones):
                                ymin, xmin, ymax, xmax = box
                                draw.rectangle([xmin*w/1000, ymin*h/1000, xmax*w/1000, ymax*h/1000], outline="#00FF00", width=5)
                            st.image(raw_img, caption="그린 박스는 텍스트 배치를 위한 최적의 여백입니다.")

                            # 2. 디자인 가이드 (New!)
                            st.subheader("🎨 Design Intelligence")
                            guide = metadata.get("design_guide", {})
                            comp = metadata.get("composition_analysis", {})
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.write("**Typography**")
                                st.info(f"Contrast: {guide.get('text_contrast', 'N/A')}\n\nFont: {guide.get('font_recommendation', 'N/A')}")
                            with col2:
                                st.write("**Composition**")
                                st.info(f"Weight: {comp.get('visual_weight', 'N/A')}\n\nGaze: {comp.get('gaze_direction', 'N/A')}")
                            with col3:
                                st.write("**Texture & Season**")
                                text_cont = metadata.get("texture_context", {})
                                st.info(f"Texture: {text_cont.get('dominant_texture', 'N/A')}\n\nSeason: {text_cont.get('seasonal_vibe', 'N/A')}")

                            # 3. 기본 정보 (무드, 색상, 조명)
                            st.subheader("🌈 Mood & Colors")
                            m_col1, m_col2 = st.columns([2, 1])
                            with m_col1:
                                moods = metadata.get("mood", [])
                                st.write(f"**Mood:** {', '.join(moods) if isinstance(moods, list) else moods}")
                                # lighting이 없을 경우를 대비해 기본값 설정
                                st.write(f"**Lighting:** {metadata.get('lighting', '분석되지 않음')}") 
                            with m_col2:
                                hex_colors = metadata.get("hex_colors", [])
                                c_cols = st.columns(len(hex_colors))
                                for i, color in enumerate(hex_colors):
                                    c_cols[i].color_picker(f"C{i+1}", color, disabled=True, key=f"c_{i}")

                        except Exception as e:
                            st.error(f"데이터 렌더링 중 에러 발생: {e}")
                            st.code(res_str)