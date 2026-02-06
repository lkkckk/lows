from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import os
from typing import List

app = FastAPI(title="Offline Embedding Service")

# 加载模型
MODEL_PATH = os.getenv("MODEL_PATH", "./models/bge-m3")
print(f"🔄 Loading model from {MODEL_PATH}...")
try:
    model = SentenceTransformer(MODEL_PATH)
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    model = None

class EmbedRequest(BaseModel):
    texts: List[str]

@app.get("/health")
def health():
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "ok", "model": MODEL_PATH}

@app.post("/embed")
def embed(request: EmbedRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if not request.texts:
        return {"embeddings": []}
    
    # 生成向量
    embeddings = model.encode(request.texts, normalize_embeddings=True)
    
    # 转换为列表返回
    return {"embeddings": embeddings.tolist()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
