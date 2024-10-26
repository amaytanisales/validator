import requests
from colorama import Fore, Style, init
import concurrent.futures
import time
import itertools
from threading import Lock
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry  # Update di sini
import warnings
import os
import ctypes
import sys
from multiprocessing import Queue

# Inisialisasi colorama
init(autoreset=True)

# Disable InsecureRequestWarning
warnings.simplefilter('ignore', requests.packages.urllib3.exceptions.InsecureRequestWarning)

# Clear screen dan set title
os.system('cls' if os.name == 'nt' else 'clear')
if os.name == 'nt':
    ctypes.windll.kernel32.SetConsoleTitleW('XFINITY VALIDATOR')
else:
    sys.stdout.write('\033]0;XFINITY VALIDATOR\007')

# Banner ASCII berwarna hijau
banner = f"""
{Fore.GREEN}
██╗  ██╗███████╗██╗███╗   ██╗██╗████████╗██╗   ██╗
╚██╗██╔╝██╔════╝██║████╗  ██║██║╚══██╔══╝╚██╗ ██╔╝
 ╚███╔╝ █████╗  ██║██╔██╗ ██║██║   ██║    ╚████╔╝ 
 ██╔══╝ ██╔══╝  ██║██║╚██╗██║██║   ██║     ╚██╔╝  
██╔╝ ██╗██║     ██║██║ ╚████║██║   ██║      ██║   
╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝   ╚═╝      ╚═╝   
                                                  
{Style.RESET_ALL}
"""

print(banner)

server_lock = Lock()  # Lock untuk sinkronisasi rotasi server

# Mengatur retry mechanism
def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Fungsi untuk memeriksa ketersediaan server sebelum digunakan
def is_server_available(server_url):
    try:
        response = requests.get(server_url, timeout=10)
        if response.status_code == 200 or "Email must be provided" in response.text:
            return True
        else:
            return False
    except requests.exceptions.RequestException:
        return False

# Fungsi untuk memeriksa apakah email sudah ada di database eksternal
def check_email_in_database(email):
    try:
        url = f'https://lintaskita.my.id/server.php?email={email}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}[ERROR] Terjadi kesalahan saat memeriksa database: {e}{Style.RESET_ALL}")
        return None

def validate_email(email, server_cycle, result_queue):
    # Periksa email di database eksternal terlebih dahulu
    db_result = check_email_in_database(email)
    
    if db_result is not None:
        if db_result.get("status") == "SUCCESS":
            print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {email} - Email sudah ada di database")
            with open("valid.txt", "a") as valid_file:
                valid_file.write(f"{email}\n")
            result_queue.put("valid")
            return

        elif db_result.get("status") == "FAILED":
            print(f"{Fore.RED}[FAILED]{Style.RESET_ALL} {email} - Email sudah ada di database")
            with open("bad.txt", "a") as bad_file:
                bad_file.write(f"{email}\n")
            result_queue.put("failed")
            return

        elif db_result.get("message") == "Email kosong":
            print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} {email} - Melanjutkan validasi di server validator...")
        else:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {email} - Respon tidak dikenal dari database")
            result_queue.put("failed")
            return

    while True:
        with server_lock:
            server_url = next(server_cycle)
        
        if not is_server_available(server_url):
            print(f"{Fore.YELLOW}[SKIP]{Style.RESET_ALL} SERVER TIMEOUT")
            continue
        
        full_url = f'{server_url}?email={email}'
        
        try:
            session = requests_retry_session()
            response = session.get(full_url, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "SUCCESS":
                print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {email}")
                with open("valid.txt", "a") as valid_file:
                    valid_file.write(f"{email}\n")
                result_queue.put("valid")
                break

            elif result.get("status") == "FAILED":
                print(f"{Fore.RED}[FAILED]{Style.RESET_ALL} {email}")
                with open("bad.txt", "a") as bad_file:
                    bad_file.write(f"{email}\n")
                result_queue.put("failed")
                break

            elif result.get("status") == "FORBIDDEN":
                print(f"{Fore.YELLOW}[FORBIDDEN]{Style.RESET_ALL} {email} - Trying another server...")
                continue

            elif result.get("status") == "ERROR":
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {email}")
                with open("bad.txt", "a") as bad_file:
                    bad_file.write(f"{email}\n")
                result_queue.put("failed")
                break

            else:
                print(f"[UNKNOWN] {email}")
                result_queue.put("failed")
                break

        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}[ERROR] Terjadi kesalahan saat mengirim permintaan: {e}{Style.RESET_ALL}")
            result_queue.put("failed")
            break

def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            items = file.readlines()
            items = [item.strip() for item in items]
        return items
    except FileNotFoundError:
        print(f"{Fore.RED}[ERROR] File {file_path} tidak ditemukan.{Style.RESET_ALL}")
        return []

email_file = input("Masukkan nama file .txt yang berisi daftar email: ")
validator_file = 'server.txt'

email_list = read_file(email_file)
validator_list = read_file(validator_file)

total_emails = len(email_list)
print(f"{Fore.GREEN}Total Email List: {total_emails}{Style.RESET_ALL}")

server_cycle = itertools.cycle(validator_list)

result_queue = Queue()  # Queue untuk mengumpulkan hasil validasi

start_time = time.time()

with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(validate_email, email, server_cycle, result_queue) for email in email_list]
    concurrent.futures.wait(futures)

end_time = time.time()
elapsed_time = end_time - start_time

# Mengambil hasil dari queue dan menghitung jumlah valid dan failed
valid_count = 0
failed_count = 0

while not result_queue.empty():
    result = result_queue.get()
    if result == "valid":
        valid_count += 1
    elif result == "failed":
        failed_count += 1

hours, remainder = divmod(elapsed_time, 3600)
minutes, seconds = divmod(remainder, 60)

print(f"\n{Fore.WHITE}[RESULT] : {Style.RESET_ALL}{Fore.GREEN}VALID: {valid_count}{Style.RESET_ALL} | {Fore.RED}FAILED: {failed_count}{Style.RESET_ALL}")
print(f"{Fore.GREEN}[INFO] Waktu pemrosesan: {int(hours)} jam {int(minutes)} menit {int(seconds)} detik{Style.RESET_ALL}")
