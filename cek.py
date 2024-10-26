import requests

# Fungsi untuk memeriksa URL
def check_url(url):
    try:
        response = requests.get(url, timeout=10)
        if "Email must" in response.text:
            print(f"{url} [LIVE]")
        else:
            print(f"{url} [DEAD]")
    except requests.RequestException as e:
        print(f"{url} [ERROR]")

# Membaca file yang berisi daftar URL
def read_url_list(file_path):
    with open(file_path, 'r') as file:
        urls = file.readlines()
    return [url.strip() for url in urls]

if __name__ == "__main__":
    file_path = 'server.txt'  # Nama file daftar URL
    urls = read_url_list(file_path)

    for url in urls:
        check_url(url)
