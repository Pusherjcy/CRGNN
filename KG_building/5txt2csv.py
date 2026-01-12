import csv

input_file = '../KG_file/dataset_TSMC2014_NYC.txt'
output_file = '../KG_file/Foursquare_NewYork.csv'

with open(input_file, 'r', encoding='ISO-8859-1') as infile, open(output_file, 'w', newline='', encoding='utf-8') as outfile:
    reader = csv.reader(infile, delimiter='\t')
    writer = csv.writer(outfile)

    writer.writerow(['user_id', 'poi_lon', 'poi_lat'])

    for row in reader:
        if len(row) >= 6:
            user_id = row[0]
            poi_lat = row[4]
            poi_lon = row[5]
            writer.writerow([user_id, poi_lon, poi_lat])
