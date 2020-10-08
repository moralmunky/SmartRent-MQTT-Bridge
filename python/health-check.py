import datetime

with open("last_heartbeat", "r") as f
    last_check = float(f.read())
    
if datetime.datetime.now().timestamp() - last_check < 300:
    sys.exit(0)

sys.exit(1)
