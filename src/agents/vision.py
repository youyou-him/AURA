# src/agents/vision.py
import json
import os
import base64
import io
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

# 1. 환경 변수 및 경로 설정
current_file_path = os.path.abspath(__file__)
gpt_dir = os.path.dirname(current_file_path)
env_path = os.path.join(gpt_dir, "..", "..", ".env") 
load_dotenv(dotenv_path=env_path)

# 2. API 키 설정
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    # 키가 없을 경우 경고 메시지 출력 (운영 환경에 따라 Raise 가능)
    print("❌ [Vision] 에러: GOOGLE_API_KEY를 찾을 수 없습니다.")
else:
    genai.configure(api_key=api_key)

def run_vision(state):
    """
    [Unified Structure Refactor]
    state['articles']를 순회하며 각 기사의 이미지를 분석하고 결과를 해당 기사 객체에 저장합니다.
    """
    print("--- [Vision Agent] 이미지 정밀 분석 시작 (Unified) ---")
    
    articles = state.get("articles", {})
    if not articles:
        print("⚠️ 분석할 기사(Articles)가 없습니다.")
        return state

    # 모델 설정 (Gemini 1.5 Flash 권장)
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
    except:
        model = genai.GenerativeModel('gemini-2.5-flash') # Fallback

    # 각 기사별 순회
    for a_id, article in articles.items():
        image_data = article.get("image_path") # Base64 string
        user_request = article.get("request", "")
        title = article.get("title", "")
        
        # 이미지가 없으면 빈 분석 결과 저장하고 Skip
        if not image_data:
            print(f"⚠️ [ID:{a_id}] 이미지가 없습니다. Vision 분석을 건너뜁니다.")
            article["vision_analysis"] = {
                "layout_strategy": {"recommendation": "Separated", "reason": "No Image"},
                "metadata": {"mood": "General"},
                "safe_areas": []
            }
            continue

        print(f"📸 이미지 분석 중... (ID: {a_id})")

        # 프롬프트 구성
        relevant_text = user_request or title
        prompt = f"""
        You are the 'Chief Art Director'. 
        Request: "{relevant_text}"

        **[TASK: Step-by-Step Layout Decision]**
        Follow this exact order of thinking to decide "Overlay" vs "Separated".

        1. Identify the 'HERO SUBJECT'.
        2. Analyze Hero's Dominance (Central Portrait/Macro shot/Size > 50%? -> 'Separated').
        3. Evaluate Background (Clean Space/Uniform Prop? -> 'Overlay').

        **[OUTPUT FORMAT: JSON ONLY]**
        Generate a JSON object for the 'vision_analysis' key with the following 4 keys.
        Strictly follow the structure below to pass the Data Integrity Check.

        {{
            "thought_process": [
                "Step 1: Identify the main subject...",
                "Step 2: Check dominance and size...",
                "Step 3: Analyze background and safe area...",
                "Final Decision: 'Overlay' or 'Separated' based on logic."
            ],
            "layout_strategy": {{
                "recommendation": "Overlay" or "Separated",
                "reason": "Clear and detailed visual rationale for the choice"
            }},
            "metadata": {{
                "mood": "Visual mood (e.g., Luxury, Bright, Moody)",
                "dominant_colors": ["#Hex1", "#Hex2", "#Hex3"],
                "lighting": "Description of lighting (e.g., Soft studio light)"
            }},
            "safe_areas": [[ymin, xmin, ymax, xmax]] 
        }}

        - If recommendation is 'Separated', 'safe_areas' must be [].
        - RETURN ONLY RAW JSON. NO MARKDOWN.
        """

        try:
            # Base64 Decoding
            payload = image_data
            if payload.startswith("data:image"):
                payload = payload.split(",", 1)[-1]
                
            img_bytes = base64.b64decode(payload)
            img = Image.open(io.BytesIO(img_bytes))
            
            # Gemini Call
            response = model.generate_content([prompt, img])
            
            # JSON Parsing
            json_res = response.text.replace("```json", "").replace("```", "").strip()
            result_dict = json.loads(json_res)
            
            # ✅ 결과 저장 (Unified Schema)
            # state["articles"][id]["vision_analysis"] 에 직접 할당
            article["vision_analysis"] = result_dict
            
        except Exception as e:
            print(f"❌ Vision Error (ID: {a_id}): {e}")
            # 에러 발생 시 Fallback
            article["vision_analysis"] = {
                "layout_strategy": {"recommendation": "Separated", "reason": "Analysis Error"},
                "metadata": {"mood": "General", "dominant_colors": ["#FFFFFF", "#000000"]},
                "safe_areas": []
            }

    # 변경된 state 반환 (LangGraph가 병합)
    return {"articles": articles}