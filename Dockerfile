FROM continuumio/miniconda3:latest

WORKDIR /app

COPY environment.yml .
RUN conda env create -f environment.yml
SHELL ["conda", "run", "-n", "odyssai", "/bin/bash", "-c"]

COPY . .
EXPOSE 9000

CMD ["conda", "run", "-n", "odyssai", "gunicorn", "-c", "gunicorn.conf.py", "src.odyssai_core.app:app"]
