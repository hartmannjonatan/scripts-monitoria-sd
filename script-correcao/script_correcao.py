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
    with open("./relatorio-schema.json", 'r') as arquivo:
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

def extrair_top_level_entity(filename):
    with open(filename, 'r') as file:
        data = file.read()
        match = re.search(r'set_global_assignment -name TOP_LEVEL_ENTITY\s+(\S+)', data)
        if match:
            return match.group(1)
        else:
            return None

def generate_tcl(project_path, top_entity):
    # Conteúdo do arquivo netlist.tcl
    tcl_content = f"""
    # Abrir o projeto Quartus
    project_open -force "{project_path}/{top_entity}.qpf" -revision {top_entity}
    
    # Compilar e gerar netlist com Zero IC Delays
    create_timing_netlist -model slow -zero_ic_delays
    
    # Exportar o relatório Datasheet
    report_datasheet -panel_name "Datasheet Report" -file "relatorio_datasheet.html"
    
    # Exportar o relatório Fmax Summary
    report_clock_fmax_summary -panel_name "Fmax Summary" -file "relatorio_fmax_summary.html"
    
    # Fechar o projeto
    project_close
    """

    # Escrever o conteúdo no arquivo netlist.tcl
    with open("netlist.tcl", "w") as file:
        file.write(tcl_content)

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


def comparar_relatorio(caminho_projeto: str, toplevel: str):
    with open(f'{caminho_projeto}/relatorio.json', 'r') as arquivo:
        RELATORIO = json.load(arquivo)
    dados = None
    with open(f"{caminho_projeto}/output_files/{toplevel}.fit.summary", "r") as arquivo:
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

    dados["atraso"]= {
        "input port": inp,
        "output port": out,
        "atraso": atraso,
        "unidade": "ns",
        "tipo de atraso": tipo
    }
    del RELATORIO["grupo"]
    
    if not(RELATORIO == dados):
        print(f"\n\n Relatório incorreto, diferenças:")
        print(DeepDiff(RELATORIO, dados))

    return RELATORIO ==  dados

def corrigir_relatorio(caminho_projeto: str):
    validar_json(caminho_projeto)
    
    qsf = glob.glob(os.path.join(caminho_projeto, '*.qsf'))[0]
    toplevel = extrair_top_level_entity(qsf)
    nome_do_container = "fbce452d726a"
    comandos = [
        f"cd {caminho_projeto}",
        f"quartus_sh --flow compile {toplevel}"
    ]
    comando_completo = " && ".join(comandos)
    subprocess.run(["docker", "exec", nome_do_container, "bash", "-c", comando_completo], check=True)
    
    generate_tcl(caminho_projeto, toplevel)
    subprocess.run(["docker", "exec", nome_do_container, "quartus_sta", "-t", "./netlist.tcl"], check=True)

    return comparar_relatorio(caminho_projeto, toplevel)


# Somador1bit.map.summary