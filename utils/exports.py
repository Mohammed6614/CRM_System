import csv
from io import StringIO
from flask import Response


def customers_csv(customers):
    csv_file = StringIO()
    writer = csv.writer(csv_file)
    writer.writerow(['id', 'first_name', 'last_name', 'email', 'phone', 'company', 'created_at'])
    for c in customers:
        writer.writerow([c.id, c.first_name, c.last_name, c.email, c.phone or '', c.company or '', c.created_at])
    csv_file.seek(0)
    return Response(csv_file.getvalue(), mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename=customers.csv'
    })
