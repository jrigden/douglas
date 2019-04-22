import os
from config import CONFIG



def clean_file(file_path):
    with open(file_path) as f:
        urls = f.read().splitlines()

    urls = [url.strip() for url in urls]
    urls = list(set(urls))
    urls.sort()

    with open(file_path,'w') as f:
        for url in urls:
            if url:
                f.write(url)
                f.write("\n")


locations = ['Washington']
for location in locations:
    file_path = data_path = os.path.join(os.getcwd(), 'data', location)
    clean_file(file_path)