import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('solution_progress.csv')

df['Date'] = pd.to_datetime(df['Date'], unit='s')

plt.figure(figsize=(10, 6))
plt.plot(df['Date'], df['Solution'], marker='o')
plt.xlabel('Date')
plt.ylabel('Solution')
plt.title('Solution vs. Date')
plt.grid(True)


plt.gcf().autofmt_xdate() #format dates for better readability

plt.show()
