"""
下载 BGE-M3 模型到本地 (用于构建离线镜像)
使用阿里云镜像加速下载
"""
import os
from huggingface_hub import snapshot_download

def download_model():
    model_id = "BAAI/bge-m3"
    local_dir = os.path.join(os.path.dirname(__file__), "../models/bge-m3")
    
    print(f"🚀 开始下载模型 {model_id} ...")
    print(f"📂 保存路径: {local_dir}")
    print("⏳这可能需要几分钟 (约 500MB)...")
    
    # 使用 HF 镜像站加速
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    
    snapshot_download(
        repo_id=model_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,  # 必须设为 False，否则 Windows 下可能出问题
        ignore_patterns=["*.msgpack", "*.h5", "*.ot", "flax_model.msgpack"] # 只下载 pytorch/safetensors
    )
    
    print("✅ 模型下载完成！")

if __name__ == "__main__":
    try:
        download_model()
    except ImportError:
        print("❌ 请先安装依赖: pip install huggingface_hub")
    except Exception as e:
        print(f"❌ 下载失败: {e}")
