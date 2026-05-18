# Path B: Hugging Face free Docker Space.
# Serves the SAME app as local/tunnel use, just hosted. Dependency versions
# mirror scripts/setup_env.py (the set proven to install on cp312).
FROM python:3.12-slim

# Runtime libs: libgomp1 for torch/onnxruntime OpenMP, libglib2.0-0 for
# opencv-python-headless (pulled in by rembg).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces run the container as uid 1000.
RUN useradd -m -u 1000 user

# All caches point at /tmp, the only guaranteed-writable path on HF Spaces.
ENV HOME=/home/user \
    PATH=/usr/local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    IMAGE_TO_3D_OUTPUT_DIR=/tmp/outputs \
    HF_HOME=/tmp/huggingface \
    U2NET_HOME=/tmp/u2net \
    NUMBA_CACHE_DIR=/tmp/numba \
    MPLCONFIGDIR=/tmp/mpl

WORKDIR /home/user/app

# Dependencies first for layer caching. torch/torchvision from the CPU index.
RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu \
        torch==2.2.2 torchvision==0.17.2 \
    && pip install \
        transformers==4.40.2 omegaconf==2.3.0 einops==0.7.0 Pillow==10.1.0 \
        "numpy<2" rembg==2.0.59 onnxruntime==1.17.3 PyMCubes==0.1.6 \
        trimesh==4.0.5 huggingface-hub fastapi==0.110.0 uvicorn==0.29.0 \
        python-multipart==0.0.9

# App source (src/tsr is intentionally NOT copied; it is regenerated next).
COPY --chown=user:user . /home/user/app

# Vendor + patch TripoSR into the image, then install the package. Order
# matters: tsr must exist before the editable install discovers packages.
RUN python scripts/fetch_triposr.py \
    && pip install -e . \
    && chown -R user:user /home/user/app

USER user
EXPOSE 7860
CMD ["uvicorn", "image_to_3d.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
