$env:DATABASE_URL='sqlite:///./visionqa_temp.db'
$env:REDIS_URL='redis://localhost:6379/0'
python run_server.py
