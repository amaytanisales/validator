import requests
from multiprocessing import Pool
import time

# Baca daftar email dari file
def read_emails_from_file(filename):
    with open(filename, 'r') as file:
        return [line.strip() for line in file if line.strip()]

# Kirim request ke endpoint untuk setiap email
def check_email_status(email):
    url = f"https://lintaskita.my.id/server.php?email={email}&status=FAILED"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"[SUCCESS] {email}")
        else:
            print(f"[FAILED] {email}")
    except Exception as e:
        print(f"[ERROR] {email} - Error: {e}")

# Fungsi utama
def main():
    email_file = "die2.txt"
    emails = read_emails_from_file(email_file)

    # Tampilkan jumlah email dalam file
    print(f"Jumlah email dalam file: {len(emails)}")

    # Catat waktu mulai
    start_time = time.time()

    # Tetapkan 5 proses
    num_processes = 5

    # Gunakan Pool untuk menjalankan proses secara paralel dengan 5 proses
    with Pool(processes=num_processes) as pool:
        pool.map(check_email_status, emails)

    # Catat waktu selesai dan hitung durasi
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Konversi ke jam, menit, dan detik
    hours, rem = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(rem, 60)

    # Tampilkan durasi pemrosesan
    print(f"Waktu yang dibutuhkan untuk memproses {len(emails)} email: {int(hours)} jam, {int(minutes)} menit, {seconds:.2f} detik")

if __name__ == "__main__":
    main()
