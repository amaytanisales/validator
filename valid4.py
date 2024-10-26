import requests
from colorama import Fore, Style, init
import concurrent.futures
import time
import itertools
from threading import Lock
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import warnings
import os
import ctypes
import sys

# Disable InsecureRequestWarning
warnings.simplefilter('ignore', requests.packages.urllib3.exceptions.InsecureRequestWarning)

# Clear screen dan set title
os.system('cls' if os.name == 'nt' else 'clear')
if os.name == 'nt':
    ctypes.windll.kernel32.SetConsoleTitleW('XFINITY VALIDATOR | KLIVERZ')
else:
    sys.stdout.write('\033]0;XFINITY VALIDATOR | KLIVERZ\007')

# Inisialisasi colorama
init(autoreset=True)

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

# Variabel untuk menghitung hasil
valid_count = 0
failed_count = 0
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
        response = requests.get(server_url, timeout=10)  # Gunakan GET request dengan timeout 10 detik
        if response.status_code == 200:
            return True  # Server tersedia jika status kode 200
        elif "Email must be provided" in response.text:
            return True  # Server tersedia jika respons mengandung pesan ini
        else:
            return False  # Respons lainnya dianggap server tidak tersedia
    except requests.exceptions.RequestException:
        return False  # Jika terjadi kesalahan, server dianggap tidak tersedia

# Fungsi untuk memeriksa email di database
def check_email_in_database(email):
    db_url = f"https://lintaskita.my.id/server.php?email={email}"
    try:
        response = requests.get(db_url, timeout=10)
        response.raise_for_status()  # Memeriksa apakah status HTTP adalah 200 (OK)
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}[ERROR] Tidak dapat mengakses database: {e}{Style.RESET_ALL}")
        return None

# Fungsi untuk submit email ke database
def submit_email_to_database(email, status):
    # Format URL dengan parameter email dan status
    url = f"https://lintaskita.my.id/server.php?email={email}&status={status}"
    
    try:
        # Mengirim permintaan GET ke server
        response = requests.get(url, timeout=10)
        
        # Memeriksa apakah permintaan berhasil
        if response.status_code == 200:
            return response.json()  # Kembalikan respons JSON dari server (jika ada)
        else:
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Terjadi kesalahan saat mengirim permintaan: {e}")
        return None

# Fungsi untuk memvalidasi email
def validate_email(email, server_cycle):
    global valid_count, failed_count

    # Cek status email di database terlebih dahulu
    db_result = check_email_in_database(email)
    
    if db_result:
        if db_result.get("status") == "SUCCESS":
            print(f"{Fore.GREEN}[LIVE]{Style.RESET_ALL} {email}")
            valid_count += 1
            with open("live.txt", "a") as valid_file:
                valid_file.write(f"{email}\n")
            return  # Tidak perlu melanjutkan validasi ke server lain

        elif db_result.get("status") == "FAILED":
            print(f"{Fore.RED}[DIE]{Style.RESET_ALL} {email}")
            failed_count += 1
            with open("die.txt", "a") as bad_file:
                bad_file.write(f"{email}\n")
            return  # Tidak perlu melanjutkan validasi ke server lain

    # Jika email tidak ditemukan di database, lanjutkan ke server validator
    while True:
        with server_lock:
            server_url = next(server_cycle)
        
        # Cek apakah server tersedia sebelum mengirim permintaan validasi
        if not is_server_available(server_url):
            continue  # Abaikan server ini dan coba server berikutnya
        
        full_url = f'{server_url}?email={email}'
        
        try:
            session = requests_retry_session()
            response = session.get(full_url, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("status") == "SUCCESS":
                print(f"{Fore.GREEN}[LIVE]{Style.RESET_ALL} {email}")
                with open("live.txt", "a") as valid_file:
                    valid_file.write(f"{email}\n")
                    status = "SUCCESS"
                    submit_email_to_database(email, status)
                valid_count += 1
                break
            
            elif result.get("status") == "FAILED":
                print(f"{Fore.RED}[DIE]{Style.RESET_ALL} {email}")
                with open("die.txt", "a") as bad_file:
                    bad_file.write(f"{email}\n")
                    status = "FAILED"
                    submit_email_to_database(email, status)
                failed_count += 1
                break
            
            elif result.get("status") == "FORBIDDEN":
                continue  # Coba server lain jika status FORBIDDEN
            
            elif result.get("status") == "ERROR":
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {email}")
                with open("bad.txt", "a") as bad_file:
                    bad_file.write(f"{email}\n")
                break
        
            else:
                print(f"[UNKNOWN] {email}")
                break
        
        except requests.exceptions.RequestException as e:
            print(f"{Fore.YELLOW}[TIMEOUT] {server_url}{Style.RESET_ALL}")
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

# Meminta input file secara interaktif
email_file = input("Masukkan nama file .txt yang berisi daftar email: ")
validator_file = 'server.txt'  # File server validator yang sudah ditentukan

# Membaca daftar email dari file
email_list = read_file(email_file)

# Membaca daftar URL validator dari file server.txt
validator_list = read_file(validator_file)

# Menampilkan jumlah email yang akan diproses
total_emails = len(email_list)
print(f"{Fore.GREEN}Total Email List: {total_emails}{Style.RESET_ALL}\n")

# Menginisialisasi siklus server menggunakan itertools.cycle
server_cycle = itertools.cycle(validator_list)

# Menghitung waktu mulai
start_time = time.time()

# Menggunakan ThreadPoolExecutor dengan 5 thread
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(lambda email: validate_email(email, server_cycle), email_list)

# Menghitung waktu selesai
end_time = time.time()
elapsed_time = end_time - start_time

hours, remainder = divmod(elapsed_time, 3600)
minutes, seconds = divmod(remainder, 60)

# Menampilkan hasil akhir setelah semua email diproses
print(f"\n{Fore.WHITE}[RESULT] : {Style.RESET_ALL}{Fore.GREEN}VALID: {valid_count}{Style.RESET_ALL} | {Fore.RED}FAILED: {failed_count}{Style.RESET_ALL}")
print(f"{Fore.GREEN}[INFO] Waktu pemrosesan: {int(hours)} jam {int(minutes)} menit {int(seconds)} detik.{Style.RESET_ALL}")
