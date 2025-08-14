FROM continuumio/miniconda3:latest

WORKDIR /app

COPY environment.yml .
RUN ["conda", "env", "create", "-f", "environment.yml"]

COPY . .

CMD ["make", "prod"]

