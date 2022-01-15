FROM python:3.9.6-alpine
MAINTAINER Rafael Girão <git@rafael.ovh>
WORKDIR /app
COPY main.py /app/ 
VOLUME /data
RUN apk update && apk add g++ gcc libxml2 libxslt-dev
RUN addgroup -S bolsas-scraper && adduser -S bolsas-scraper -G bolsas-scraper
RUN chown -R bolsas-scraper:bolsas-scraper /app
USER bolsas-scraper
RUN pip install --no-cache-dir bs4 lxml requests 
#RUN chmod +x src/run.sh
#ENTRYPOINT ["python", "main.py"]
ENTRYPOINT ["/bin/sh"]

