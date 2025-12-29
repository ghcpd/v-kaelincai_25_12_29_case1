import http.client, time, sys
for i in range(6):
    try:
        conn = http.client.HTTPConnection('127.0.0.1', 5000, timeout=2)
        conn.request('GET', '/health')
        r = conn.getresponse()
        print('status', r.status)
        print('body', r.read().decode())
        sys.exit(0)
    except Exception as e:
        print('attempt', i, 'failed:', repr(e))
        time.sleep(0.5)
print('could not connect')
sys.exit(2)
