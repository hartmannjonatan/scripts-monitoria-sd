import os
import re
import sys
import shutil
import unicodedata
import zipfile

def normalize_name(name):
    # Remove espaços e substitui por "_"
    name = name.replace(" ", "_")
    
    # Remove caracteres especiais e acentos
    name = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
    name = re.sub(r'[^\w\s.-]', '', name)

    return name

def extract_and_rename_zip(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".zip"):
                zip_path = os.path.join(root, file)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(root)
                os.remove(zip_path)
                print(f"Descompactado e removido: {zip_path}")

def rename_files_and_dirs(directory):
    # Se o diretório for '.', use o diretório atual
    if directory == '.':
        directory = os.getcwd()

    # Renomeia a pasta raiz
    head, tail = os.path.split(directory)
    new_directory_name = normalize_name(tail)
    new_directory_path = os.path.join(head, new_directory_name)
    if directory != new_directory_path:
        shutil.move(directory, new_directory_path)
        print(f"Renomeada pasta raiz: {directory} -> {new_directory_path}")

    # Renomeia arquivos e pastas dentro do diretório
    for root, dirs, files in os.walk(new_directory_path, topdown=False):
        for name in files + dirs:
            old_path = os.path.join(root, name)
            new_name = normalize_name(name)
            new_path = os.path.join(root, new_name)
            
            # Verifica se o nome mudou
            if old_path != new_path:
                os.rename(old_path, new_path)
                print(f"Renomeado: {old_path} -> {new_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: normalize_files '.' ou 'caminho/da/pasta'")
        sys.exit(1)

    directory_path = sys.argv[1]
    extract_and_rename_zip(directory_path)
    rename_files_and_dirs(directory_path)
    print("Renomeação concluída.")

