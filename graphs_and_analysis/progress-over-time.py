import os
import csv
import glob

def find_and_save_files(directory: str, pattern: str, output_csv: str):
    with open(output_csv, 'w', newline='') as csvfile:

        writer = csv.writer(csvfile)

        writer.writerow(['Solution', 'Date'])

        for filename in glob.glob(os.path.join(directory, pattern)):

            file_stats = os.stat(filename)

            last_modified = file_stats.st_mtime

            writer.writerow([filename, last_modified])

directory = '../score_lookup'

pattern = '[0-9]*.csv'

output_csv = 'solution_progress.csv'



find_and_save_files(directory, pattern, output_csv)
