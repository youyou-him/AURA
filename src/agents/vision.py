import json
import os
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

# 1. 환경 변수 및 경로 설정
current_file_path = os.path.abspath(__file__)
tests_dir = os.path.dirname(current_file_path)
# .env 파일 위치는 프로젝트 구조에 맞게 조정하세요 (예: 상위 폴더 등)
env_path = os.path.join(tests_dir, "..", "..", ".env") 
load_dotenv(dotenv_path=env_path)

# 2. API 키 설정
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ [Vision] 에러: GOOGLE_API_KEY를 찾을 수 없습니다. .env 파일을 확인하세요.")
else:
    genai.configure(api_key=api_key)

def run_vision_analysis(state):
    print("--- [Vision Agent] 이미지 정밀 분석 시작 (Gemini) ---")
    
    # State에서 이미지 경로와 사용자 텍스트 가져오기
    image_path = state.get("image_path")
    user_text = state.get("user_input", "")

    # 모델 설정 (Gemini 1.5 Flash 권장, 없으면 Pro 사용)
    # user_text에 언급된 2.5 모델은 아직 정식 사용이 어려울 수 있어 1.5로 설정합니다.
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
    except:
        model = genai.GenerativeModel('gemini-2.5-flash')

    # 👇 [수정됨] 요청하신 프롬프트를 영어로 번역하여 적용했습니다.
    prompt = f"""
    You are the 'Chief Art Director'. 
    
    **[TASK: Step-by-Step Layout Decision]**
    Follow this exact order of thinking to decide "Overlay" vs "Separated".

    **STEP 1: Identify the 'HERO SUBJECT' (The Star)**
    - Read request: "{user_text}".
    - Find the Main Subject (Person, Watch, Bag).
    - **IGNORE** the background cleanliness for a moment. Focus ONLY on the Hero.

    **STEP 2: Analyze Hero's Dominance (The FATAL Check)**
    - **Is it a Person?** If yes, does the person occupy the **Center** of the image? -> If YES, STOP. Choose **'SEPARATED'**. (Never overlay text on a central portrait).
    - **Is it a Product?** Is it a "Macro Shot" (zoomed in extremely close)? -> If YES, STOP. Choose **'SEPARATED'**.
    - **Size Check:** Does the Hero Subject take up more than 50% of the image width/height? -> If YES, mostly **'SEPARATED'**.

    **STEP 3: Evaluate Background/Props (Only if Step 2 didn't stop you)**
    - Now look at the background.
    - **Case A (Prop as Canvas):** Is the Hero small, sitting on a huge uniform object (like a watch on a big white shell)? -> Choose **'OVERLAY'**.
    - **Case B (Clean Space):** Is the Hero off-center (Left/Right), leaving a huge empty sky/wall? -> Choose **'OVERLAY'**.

    **[Decision Logic Summary]**
    1. **Portrait/Central Human** = **SEPARATED** (Priority 1)
    2. **Zoomed-in Product** = **SEPARATED** (Priority 2)
    3. **Small Hero + Big Uniform Prop** = **OVERLAY** (Priority 3)
    4. **Small Hero + Clean Sky/Wall** = **OVERLAY** (Priority 4)

    **[JSON Data Structure]**
    1. thought_process: [
        "Step 1: Hero is 'Man'...",
        "Step 2: The Man is located in the center and fills 70% of the frame...",
        "Step 3: Background is white, BUT Step 2 (Central Portrait) overrides it...",
        "Step 4: Decision 'Separated' to protect the subject."
       ]
    2. layout_strategy:
        - recommendation: "Overlay" or "Separated"
        - reason: "Central portrait requires separation despite clean background."
    3. metadata: 
        - mood, hex_colors, lighting
        - design_guide: text_contrast, font_recommendation
    4. space_analysis: [[ymin, xmin, ymax, xmax], ...] (Return [] if Separated)

    RETURN ONLY RAW JSON. NO MARKDOWN.

    **[JSON Response Example]**
    {{
        "thought_process": [
            "Step 1: User request is about a 'Watch'.",
            "Step 2: Found the Watch on the right side.",
            "Step 3: The large object on the left is a white Seashell (Prop).",
            "Step 4: The shell's surface is white and smooth.",
            "Step 5: Choosing 'Overlay' to place text on the shell."
        ],
        "layout_strategy": {{
            "recommendation": "Overlay",
            "reason": "Although the shell is large, it serves as a smooth, uniform background prop for the watch (Hero)."
        }},
        "metadata": {{
            "mood": "Oceanic, Luxury",
            "hex_colors": ["#F5F5F5", "#003366", "#111111"],
            "lighting": "Soft studio light",
            "design_guide": {{
                "text_contrast": "Dark",
                "font_recommendation": "Sans-serif"
            }},
            "composition_analysis": {{
                "visual_weight": "Right-heavy (Watch)",
                "gaze_direction": "Left"
            }},
            "texture_context": {{
                "dominant_texture": "Smooth Shell Surface",
                "seasonal_vibe": "Summer"
            }}
        }},
        "space_analysis": [[100, 50, 800, 500]]
    }}
    
    RETURN ONLY RAW JSON. DO NOT USE MARKDOWN.
    """

    try:
        img = Image.open(image_path)
        response = model.generate_content([prompt, img])
        
        # JSON 정제
        json_res = response.text.replace("```json", "").replace("```", "").strip()
        return {"vision_result": json.loads(json_res)}
        
    except Exception as e:
        print(f"❌ Vision Analysis Error: {e}")
        return {"vision_result": None}