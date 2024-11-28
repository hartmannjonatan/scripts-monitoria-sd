import jsonschema
import json
import sys
import subprocess
import glob
import os
import re
from deepdiff import DeepDiff

RELATORIO = None

def validar_json(caminho_projeto: str):
    with open("/home/jonatan/Documentos/UFSC/MONITORIA_SD/script-relatorio-compare/relatorio-schema.json", 'r') as arquivo:
        SCHEMA = json.load(arquivo)
    try:
        with open(f'{caminho_projeto}/relatorio.json', 'r') as arquivo:
            RELATORIO = json.load(arquivo)
        jsonschema.validate(instance=RELATORIO, schema=SCHEMA)
        return True
    except jsonschema.exceptions.ValidationError as e:
        print("Relatório inconsistente:", e)
        return False
    except FileNotFoundError:
        print(f"{caminho_projeto}/relatorio.json não encontrado.")
        return False
        
def extrair_fmax_netlist(caminho_projeto):
    html_path = f"{caminho_projeto}/relatorio_fmax_summary.html"
    with open(html_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Localize a célula <td> contendo o valor de Fmax
    start_td = html_content.find('<TD >')
    if start_td == -1:
        return None

    # Localize o fim da célula <td>
    end_td = html_content.find('</TD>', start_td)
    if end_td == -1:
        return None

    # Extraia o conteúdo entre <TD > e </TD>
    fmax_text = html_content[start_td + len('<TD >'):end_td].strip()

    # Divida o texto em valor e unidade
    fmax_value, fmax_unit = fmax_text.split()

    # Converta o valor para float e retorne como uma tupla (valor, unidade)
    return float(fmax_value), fmax_unit

def extrair_atraso_netlist(caminho_projeto: str):
    # Carregue o conteúdo do arquivo HTML
    with open(f"{caminho_projeto}/relatorio_datasheet.html_files/1.htm", "r") as arquivo:
        conteudo = arquivo.read()

    # Use regex para encontrar todas as linhas da tabela, exceto o cabeçalho
    linhas_tabela = re.findall(r"<TR[^>]*>(.*?)</TR>", conteudo, re.DOTALL)

    # Inicialize variáveis para armazenar o maior valor e suas respectivas linha, coluna, input port e output port
    maior_valor = float("-inf")
    linha_maior_valor = None
    coluna_maior_valor = None
    input_port_maior_valor = None
    output_port_maior_valor = None

    # Percorra todas as linhas da tabela
    for linha in linhas_tabela:
        # Use regex para encontrar os valores de cada célula da linha
        valores = re.findall(r"<TD[^>]*>(.*?)</TD>", linha, re.DOTALL)
        # Verifique se há células suficientes na linha
        if len(valores) >= 6:
            # A primeira célula do grupo é o input port
            input_port = valores[0].strip()
            # A segunda célula do grupo é o output port
            output_port = valores[1].strip()
            # Percorra as células de valores (a partir da terceira célula do grupo)
            for idx, valor in enumerate(valores[2:], start=2):
                # Se a coluna não for RR, RF, FR ou FF, continue para a próxima coluna
                if idx not in {2, 3, 4, 5}:
                    continue
                # Converta o valor para float, removendo espaços em branco
                try:
                    valor_float = float(valor.strip())
                except ValueError:
                    continue
                # Se o valor for maior do que o maior valor atual, atualize as variáveis
                if valor_float > maior_valor:
                    maior_valor = valor_float
                    linha_maior_valor = input_port
                    coluna_maior_valor = ["RR", "RF", "FR", "FF"][idx - 2]  # Índice direto da coluna
                    input_port_maior_valor = input_port
                    output_port_maior_valor = output_port

    return maior_valor, input_port_maior_valor, output_port_maior_valor, coluna_maior_valor

def extrair_top_level_entity(filename):
    with open(filename, 'r') as file:
        data = file.read()
        match = re.search(r'set_global_assignment -name TOP_LEVEL_ENTITY\s+(\S+)', data)
        if match:
            return match.group(1)
        else:
            return None
            
def renomear_arquivo_json(caminho_pasta):
    # Lista os arquivos no diretório
    arquivos = os.listdir(caminho_pasta)
    
    # Verifica se existe um arquivo .json
    arquivo_encontrado = False
    for arquivo in arquivos:
        if arquivo.endswith('.json') or arquivo.endswith('.JSON'):
            arquivo_encontrado = True
            novo_nome = os.path.join(caminho_pasta, 'relatorio.json')
            os.rename(os.path.join(caminho_pasta, arquivo), novo_nome)
            print(f"Arquivo {arquivo} renomeado para relatorio.json.")
            break
    
    # Se nenhum arquivo .json for encontrado, levanta uma exceção
    if not arquivo_encontrado:
        raise FileNotFoundError("Nenhum arquivo .json foi encontrado.")

def comparar_relatorio(caminho_projeto: str, toplevel: str):
    with open(f'{caminho_projeto}/relatorio.json', 'r') as arquivo:
        RELATORIO = json.load(arquivo)
    dados = None
    
    caminho_saida = f"{caminho_projeto}/output_files/"
    if not(os.path.exists(caminho_saida)):
        caminho_saida = f"{caminho_projeto}/"
        
    with open(f"{caminho_saida}/{project}.fit.summary", "r") as arquivo:
        # Leia todo o conteúdo do arquivo
        conteudo = arquivo.read()
        dados = {
            "fpga":{
                "familia": re.search(r"Family\s*:\s*(.*?)\n", conteudo).group(1),
                "dispositivo": re.search(r"Device\s*:\s*(.*?)\n", conteudo).group(1)
            },
            "utilizacao":{
                "total combinational functions": int(re.search(r"Total combinational functions\s*:\s*(\d+)", conteudo).group(1)),
                "dedicated logic registers": int(re.search(r"Dedicated logic registers\s*:\s*(\d+)", conteudo).group(1)),
                "total pins": int(re.search(r"Total pins\s*:\s*(\d+)", conteudo).group(1))
            }
        }

    atraso, inp, out, tipo = extrair_atraso_netlist(caminho_projeto)
    #Fmax_value, Fmax_un = extrair_fmax_netlist(caminho_projeto)

    dados["atraso"]= {
        "input port": inp,
        "output port": out,
        "atraso": atraso,
        "unidade": "ns",
        "tipo de atraso": tipo
    }
    
    #dados["atraso"]= {
    #    "Fmax": Fmax_value,
    #    "unidade": Fmax_un
    #}
    
    if not(RELATORIO["atraso"] == dados["atraso"]):
        print(f"\n\n Atraso incorreto, diferenças:")
        print(DeepDiff(RELATORIO["atraso"], dados["atraso"]))

    if not(RELATORIO["utilizacao"] == dados["utilizacao"]):
        print(f"\n\n Utilizacao incorreto, diferenças:")
        print(DeepDiff(RELATORIO["utilizacao"], dados["utilizacao"]))

    if not(RELATORIO["quartus"]["fpga"] == dados["fpga"]):
        print(f"\n\n FPGA incorreto, diferenças:")
        print(DeepDiff(RELATORIO["quartus"]["fpga"], dados["fpga"]))

    return RELATORIO["atraso"] == dados["atraso"] and RELATORIO["utilizacao"] == dados["utilizacao"] and RELATORIO["quartus"]["fpga"] == dados["fpga"]

# Verifica se o número de argumentos é correto
if len(sys.argv) != 2:
    print("Uso: python3 script.py <caminho_para_pasta>")
    sys.exit(1)

# Obtém o caminho para a pasta do primeiro argumento
pasta = os.path.abspath(sys.argv[1])

# Verifica se o caminho é válido
if not os.path.isdir(pasta):
    print("O caminho especificado não é uma pasta válida.")
    sys.exit(1)
    
qsf = glob.glob(os.path.join(pasta, '*.qsf'))[0]
project, _ = os.path.splitext(os.path.basename(qsf))
toplevel = extrair_top_level_entity(qsf)
    
renomear_arquivo_json(pasta)
validar_json(pasta)
print("\n\nComparação de relatório com os dados: ")
print(comparar_relatorio(pasta, toplevel))


#pyinstaller --onefile --name compare_relatorio compare_relatorio.py
