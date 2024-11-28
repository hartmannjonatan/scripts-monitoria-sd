import sys
import os
from script_correcao import *

def main():
    # Verifica se o número de argumentos é correto
    if len(sys.argv) != 2:
        print("Uso: python3 script.py <caminho_para_pasta>")
        sys.exit(1)

    # Obtém o caminho para a pasta do primeiro argumento
    pasta = sys.argv[1]

    # Verifica se o caminho é válido
    if not os.path.isdir(pasta):
        print("O caminho especificado não é uma pasta válida.")
        sys.exit(1)

    print(corrigir_relatorio(pasta))

if __name__ == "__main__":
    main()
