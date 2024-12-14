import os
base_dir = os.path.dirname(os.path.abspath(__file__))


with open(os.path.join(base_dir, 'data', 'config.yaml'), 'r', encoding='utf-8') as file:
    filedata = file.read()

print(filedata)