import requests
import time
import concurrent.futures
import os
import threading

API_URL = "https://ark.ap-southeast.bytepluses.com/api/v3/chat/completions"
API_KEY = os.getenv("ARK_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Large output to increase token usage
prompt = "Write a 4000-word extremely detailed technical analysis about AI infrastructure scaling, distributed systems, GPU optimization, and inference pipelines."

payload = {
    "model": "seed-2-0-lite-260228",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 4000,
    "temperature": 0.7
}

# Global metrics
total_tokens = 0
total_requests = 0
total_errors = 0
start_time = time.time()
lock = threading.Lock()


def call_seed(i):
    global total_tokens, total_requests, total_errors

    try:
        t0 = time.time()
        response = requests.post(API_URL, headers=headers, json=payload, timeout=180)

        latency = time.time() - t0

        if response.status_code == 429:
            print(f"[{i}] 429 Rate limited. Backing off...")
            time.sleep(2)
            return 0

        if not response.ok:
            total_errors += 1
            print(f"[{i}] HTTP {response.status_code}")
            return 0

        data = response.json()
        usage = data.get("usage", {}).get("total_tokens", 0)

        with lock:
            total_tokens += usage
            total_requests += 1

        print(f"[{i}] OK | {usage} tokens | {latency:.2f}s")

        return usage

    except Exception as e:
        total_errors += 1
        print(f"[{i}] ERROR: {e}")
        return 0


def monitor():
    while True:
        time.sleep(10)
        elapsed = time.time() - start_time
        tps = total_tokens / elapsed if elapsed > 0 else 0
        rps = total_requests / elapsed if elapsed > 0 else 0

        print("\n====== LIVE STATS ======")
        print(f"Elapsed: {elapsed:.1f}s")
        print(f"Requests: {total_requests}")
        print(f"Tokens: {total_tokens:,}")
        print(f"Errors: {total_errors}")
        print(f"Tokens/sec: {tps:.2f}")
        print(f"Req/sec: {rps:.2f}")
        print("========================\n")


def run_stress_test(duration_hours=3, max_concurrency=30):
    end_time = time.time() + duration_hours * 3600

    # Start monitoring thread
    threading.Thread(target=monitor, daemon=True).start()

    concurrency = 5  # start small
    print(f"Starting with concurrency {concurrency}")

    while time.time() < end_time:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(call_seed, i) for i in range(concurrency)]
            concurrent.futures.wait(futures)

        # Gradual ramp-up
        if concurrency < max_concurrency:
            concurrency += 2
            print(f"Ramping up concurrency to {concurrency}")

    print("\n✅ Stress test complete.")
    print(f"Total tokens: {total_tokens:,}")


if __name__ == "__main__":
    run_stress_test(duration_hours=3, max_concurrency=30)
