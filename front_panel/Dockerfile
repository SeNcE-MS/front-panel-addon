FROM python:3.13-alpine
WORKDIR /app
COPY server.py ha_bridge.py panel_config.py theme_palettes.py home_config.py header_icon.py /app/
COPY www /app/www
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8099
CMD ["python", "/app/server.py"]
