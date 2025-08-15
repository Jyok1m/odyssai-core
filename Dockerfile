FROM continuumio/miniconda3:latest

SHELL ["/bin/bash", "-lc"]
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libsndfile1 libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

RUN conda install -n base -c conda-forge -y mamba \
    && conda clean -afy

COPY environment-export.yml /tmp/environment.yml
RUN mamba env create -n odyssai -f /tmp/environment.yml --override-channels -c conda-forge \
    && conda clean -afy

COPY requirements-export.txt /tmp/requirements.txt
RUN conda run -n odyssai pip install --no-cache-dir -r /tmp/requirements.txt

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh /usr/local/bin/start.sh

# Code
COPY . .

# Runtime
ENV PYTHONPATH=/app/src \
    BACKEND_PORT=9000 \
    PORT=9000
EXPOSE 9000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/usr/local/bin/start.sh"]
