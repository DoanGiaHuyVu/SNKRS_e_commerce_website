import sqlite3

# Path to your database
db_path = '/Users/adamvu/100_Days_of_Code_Python/day_96_e_commerce_website/instance/shoes.db'

# Connect to the SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# SQL query to delete rows where product_data is NULL
delete_query = "DELETE FROM shoes WHERE product_data IS NULL"

# Execute the query
cursor.execute(delete_query)

# Commit the changes
conn.commit()

# Close the connection
conn.close()

print("Rows with NULL product_data have been deleted.")
