# -*- coding: utf-8 -*-
import os
import secrets
import asyncio
import io
from flask import Flask, request, jsonify, render_template, send_file, redirect
import edge_tts
from deep_translator import GoogleTranslator

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = secrets.token_hex(16)
app.template_folder = os.path.join('static', 'ui')

# Voice ID Mapping
VOICE_ID_TABLE = {
    "zh-TW": {"female": "zh-TW-HsiaoChenNeural", "male": "zh-TW-YunJheNeural"},
    "en-US": {"female": "en-US-JennyNeural", "male": "en-US-GuyNeural"},
    "ja-JP": {"female": "ja-JP-NanamiNeural", "male": "ja-JP-KeitaNeural"},
    "ko-KR": {"female": "ko-KR-SunHiNeural", "male": "ko-KR-InJoonNeural"},
}

def get_voice_id(lang_code, gender='female'):
    # Check if lang_code is a full voice ID
    if lang_code and ("-Neural" in lang_code or "-" in lang_code and len(lang_code) > 10):
        return lang_code
    
    # Fallback to table
    lang_map = VOICE_ID_TABLE.get(lang_code, VOICE_ID_TABLE["zh-TW"])
    return lang_map.get(gender, "zh-TW-HsiaoChenNeural")

@app.route('/')
def index():
    # Back to original default: index.html
    return redirect("/static/ui/index.html")

@app.route('/demo')
def demo_page():
    return render_template('demo.html')

@app.route('/api/translate', methods=['POST'])
def api_translate():
    try:
        data = request.json or request.form
        text = data.get('text')
        target = data.get('target', 'zh-TW')
        source = data.get('source', 'auto')
        
        if not text:
            return jsonify(ok=False, error="Missing text"), 400
            
        translated = GoogleTranslator(source=source, target=target).translate(text)
        return jsonify(ok=True, translated=translated)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route('/api/tts_preview', methods=['POST'])
def api_tts_preview():
    try:
        data = request.json or {}
        text = data.get('text')
        lang = data.get('lang') # This can be a voice ID or lang code
        gender = data.get('gender', 'female')
        
        if not text:
            return jsonify(ok=False, error="No text"), 400
            
        voice = get_voice_id(lang, gender)
        
        async def _gen():
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            audio_bytes = loop.run_until_complete(_gen())
        finally:
            loop.close()
            
        return send_file(
            io.BytesIO(audio_bytes),
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name="preview.mp3"
        )
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return jsonify(ok=False, error=str(e)), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host='0.0.0.0', port=port, debug=True)
