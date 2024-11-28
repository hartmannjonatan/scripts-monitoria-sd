import sys
import difflib

def compare_files(file1, file2):
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        lines1 = f1.readlines()
        lines2 = f2.readlines()

    # Encontre diferenças entre as duas listas de linhas
    diff = [line for line in difflib.unified_diff(lines1, lines2, fromfile=file1, tofile=file2)]

    # Imprima as diferenças
    if diff:
        print("Diferenças encontradas:")
        for line in diff:
            print(line, end='')
    else:
        print("Os arquivos são iguais.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 compare_files.py arquivo1 arquivo2")
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]

    compare_files(file1, file2)
