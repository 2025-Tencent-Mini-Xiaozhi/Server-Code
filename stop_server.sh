lsof -ti:8000,8001,8002,8003,8004 | xargs kill -9
docker stop xiaozhi-esp32-server-redis xiaozhi-esp32-server-db