lsof -ti:8000,8001,8002,8003,8004 | xargs kill -9

docker stop xiaozhi-esp32-server-redis xiaozhi-esp32-server-db
docker start xiaozhi-esp32-server-redis xiaozhi-esp32-server-db

# 启动 manager-api（后台运行，日志输出到当前终端）
cd /root/xiaozhi-esp32-server/main/manager-api && mvn spring-boot:run > >(tee -a manager-api.log) 2>&1 &

# 启动 manager-web（后台运行，日志输出到当前终端）
cd /root/xiaozhi-esp32-server/main/manager-web && npm run serve > >(tee -a manager-web.log) 2>&1 &

# 启动 xiaozhi-server（后台运行，日志输出到当前终端）
cd /root/xiaozhi-esp32-server/main/xiaozhi-server && source ~/miniconda/etc/profile.d/conda.sh && conda activate xiaozhi-esp32-server && sleep 20 && python app.py > >(tee -a xiaozhi-server.log) 2>&1 &

# 等待用户按任意键后清理后台进程
read -n 1 -s -r -p "所有服务已启动！按任意键停止服务并退出..."
pkill -P $$
