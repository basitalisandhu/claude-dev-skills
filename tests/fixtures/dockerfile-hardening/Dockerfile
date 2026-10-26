FROM python:latest
MAINTAINER someone
ENV API_KEY=set-at-build-time
ARG DB_PASSWORD
RUN apt-get update && apt-get install -y curl && apt-get upgrade -y
RUN curl -sSL https://example.com/install.sh | bash
RUN pip install flask && chmod -R 777 /app
RUN sudo make install
ADD https://example.com/tool.tgz /tmp/
ADD src/ /app/src/
COPY .env /app/.env
COPY . /app
EXPOSE 22 8080
CMD python app.py
