import os
import sys

# 현재 파일의 부모의 부모 폴더(Final-Project)를 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.normpath(os.path.join(current_dir, "../../"))
sys.path.append(project_root)

# 이제 src 모듈을 정상적으로 불러올 수 있습니다.
from src.agents.publisher import PublisherAgent

# 1. 에이전트 객체 생성
agent = PublisherAgent()

# 2. 가상의 상태 데이터 (기존 magazine_state와 images를 합친 형태)
test_state = {
    "style": { "primary_color": "#FF8A00", "font_family": "font-serif", "bg_color": "#F8FAFC" },
    "content": {
        "title": "2026 SKINCARE",
        "page": 24,
        "blocks": [
            { "type": "hero_cover", "img_id": "사진4-1.png", "headline": "SKINCARE SPECIAL" }
        ]
    },
    "images": { "사진4-1.png": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=" },
    "meta": { "editor": "김지혜", "photographer": "이민섭" }
}
agent = PublisherAgent()
# 3. 에이전트 실행
final_state = agent.run(test_state)
# Final-project/output 에 파일 생성
