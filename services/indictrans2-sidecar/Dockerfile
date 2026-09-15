# Runs as a Linux container (Docker Desktop's Linux VM backend) because
# IndicTransToolkit ships no Windows wheel (only manylinux/macOS/PyPy -
# checked directly against PyPI's file listing) and building it from
# source needs Cython, which this machine's Windows Application Control
# policy blocks outright (same class of problem documented in
# apps/api/pyproject.toml for the langgraph package). Same infra pattern
# as postgres/chroma in infra/docker-compose.yml - not a new architecture.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# CPU-only torch wheel explicitly - the default PyPI torch pulls CUDA
# libraries that are multiple GB and useless on this CPU-only deployment.
RUN pip install --no-cache-dir torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8600

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8600"]
