FROM python:3.13-alpine
WORKDIR /app
RUN pip install --no-cache-dir --no-deps yt-dlp==2026.10.26
COPY music_bridge.py music_search.py music_connection.py device_controls.py server.py ha_bridge.py panel_config.py theme_palettes.py home_config.py header_icon.py /app/
COPY www /app/www
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8099
CMD ["python", "/app/server.py"]
