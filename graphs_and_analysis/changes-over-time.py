import os
import csv
import glob
import subprocess

def find_and_save_files(directory: str, pattern: str, output_csv: str):
    with open(output_csv, 'w', newline='') as csvfile:

        writer = csv.writer(csvfile)

        writer.writerow(['Solution', 'Changes'])

        for filename in glob.glob(os.path.join(directory, pattern)):

            # file_stats = os.stat(filename)
            process = subprocess.run(['./changes-over-time.exe', '../benchmark.csv', filename], capture_output=True, text=True)

            writer.writerow([filename, process.stdout.strip()])


directory = '../score_lookup'

pattern = '[0-9]*.csv'

output_csv = 'solution_changes.csv'



find_and_save_files(directory, pattern, output_csv)
