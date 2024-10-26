import requests
import time

# URL yang akan diminta
url = "http://192.46.230.161:3000/validator?email=kliverz1337@gmail.com"

# Mencatat waktu sebelum permintaan
start_time = time.time()

try:
    # Melakukan permintaan GET
    response = requests.get(url)
    
    # Mencatat waktu setelah menerima respons
    elapsed_time = time.time() - start_time

    # Menampilkan hasil
    print(f"Status Code: {response.status_code}")
    print(f"Response Time: {elapsed_time:.2f} seconds")
    print("Response Content:", response.text)

except requests.exceptions.RequestException as e:
    print("Error:", e)
