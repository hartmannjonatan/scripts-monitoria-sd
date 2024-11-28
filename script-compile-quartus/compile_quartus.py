import sys
import subprocess
import glob
import os
import re
import argparse

def get_container_id(image_name):
    # Execute o comando 'docker ps' para listar os contêineres em execução
    ps_process = subprocess.Popen(['docker', 'ps'], stdout=subprocess.PIPE)
    
    # Execute o comando 'grep' para filtrar os contêineres pelo nome da imagem
    grep_process = subprocess.Popen(['grep', image_name], stdin=ps_process.stdout, stdout=subprocess.PIPE)
    
    # Leia a saída do comando 'grep'
    output = grep_process.communicate()[0].decode()
    
    # Divida a saída em linhas e pegue o primeiro ID de contêiner da lista
    container_id = output.split()[0] if output else None
    
    return container_id

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
    with open("/home/jonatan/Documentos/UFSC/MONITORIA_SD/script-compile-quartus/netlist.tcl", "w") as file:
        file.write(tcl_content)

def set_generic(pasta, toplevel, GENERICS):

    generics_content = """"""
    for generic, value in GENERICS.items():
        generics_content = f"""{generics_content}
set_parameter -name {generic} {value}
        """

    tcl_content = f"""
# Abrir o projeto Quartus
project_open -force "{pasta}/{toplevel}.qpf" -revision {toplevel}
{generics_content}
# Fechar o projeto
project_close
    """

    with open(f"{pasta}/set_generics.tcl", "w") as file:
        file.write(tcl_content)

def set_testbench(pasta, toplevel, filepath, entity, architecture, end_simulation):
    tcl_content = f"""
project_open -force "{pasta}/{toplevel}.qpf" -revision {toplevel}
set_global_assignment -name EDA_TEST_BENCH_ENABLE_STATUS TEST_BENCH_MODE -section_id eda_simulation
set_global_assignment -name EDA_NATIVELINK_SIMULATION_TEST_BENCH {entity} -section_id eda_simulation
set_global_assignment -name EDA_TEST_BENCH_NAME {entity} -section_id eda_simulation
set_global_assignment -name EDA_DESIGN_INSTANCE_NAME {architecture} -section_id {entity}
set_global_assignment -name EDA_TEST_BENCH_RUN_SIM_FOR "{end_simulation}" -section_id {entity}
set_global_assignment -name EDA_TEST_BENCH_MODULE_NAME {entity} -section_id {entity}
set_global_assignment -name EDA_TEST_BENCH_FILE {filepath} -section_id {entity}
set_global_assignment -name EDA_OUTPUT_DATA_FORMAT VHDL -section_id eda_simulation
set_global_assignment -name POWER_PRESET_COOLING_SOLUTION "23 MM HEAT SINK WITH 200 LFPM AIRFLOW"
set_global_assignment -name POWER_BOARD_THERMAL_MODEL "NONE (CONSERVATIVE)"
project_close
    """
    with open(f"{pasta}/set_testbench.tcl", "w") as file:
        file.write(tcl_content)

    

# Verifica se o número de argumentos é correto
if len(sys.argv) < 1:
    print("Uso: python3 script.py <caminho_para_pasta> <--toplevel> <--simulate> <--generics>")
    sys.exit(1)

# Criação do parser
parser = argparse.ArgumentParser(description="Descrição do programa")

# Argumento posicional para o caminho da pasta (padrão: pasta atual)
parser.add_argument('folder', nargs='?', default='.', help='Caminho para a pasta (padrão: pasta atual)')

# Argumentos opcionais
parser.add_argument('--simulate', action='store_true', help='Simular')
parser.add_argument('--only_simulate', default=False, action='store_true', help='Apenas simular')
parser.add_argument('--toplevel', type=str, help='Nome da entidade toplevel')
parser.add_argument('--testbench', type=str, help='Caminho do testbench')
parser.add_argument('--testbench_entity', type=str, help='Entidade do testbench')
parser.add_argument('--testbench_arch', default="dut", type=str, help='Arquitetura do testbench')
parser.add_argument('--time', default="1 s", type=str, help='Tempo de simulação (ex: "1 s")')
parser.add_argument('--no_gui', action='store_true', help='Simula apenas retornando na linha de comando, sem abrir o ModelSim')

# Argumentos opcionais para genéricos
parser.add_argument('--generics', nargs='+', help='Argumentos genéricos no formato parametro:valor')

# Parse dos argumentos da linha de comando
args = parser.parse_args()
    
# Obtém o caminho para a pasta do primeiro argumento
pasta = os.path.abspath(args.folder)

# Verifica se o caminho é válido
if not os.path.isdir(pasta):
    sys.exit(1)

try:
    qsf = glob.glob(os.path.join(pasta, '*.qsf'))[0]
except Exception:
    print(".qsf não encontrado!")
    sys.exit(1)
toplevel = extrair_top_level_entity(qsf) if args.toplevel is None else args.toplevel

if args.generics:
    GENERICS = {}
    for generic_arg in args.generics:
        param, value = generic_arg.split(':')
        GENERICS[param] = value
    
    set_generic(pasta, toplevel, GENERICS)

nome_do_container = get_container_id("quartus:13.0.1.2")
comandos = [
    f"cd {pasta}"
]
if not args.only_simulate:
    if args.generics:
        comandos.append(f"quartus_sh -t ./set_generics.tcl")
    if args.testbench is not None and args.simulate:
        set_testbench(pasta, toplevel, args.testbench, args.testbench_entity, args.testbench_arch, args.time)
        comandos.append(f"quartus_sh -t ./set_testbench.tcl")
    comandos.append(f"quartus_sh --flow compile {toplevel}")
if args.simulate:
    gui = "--no_gui" if args.no_gui else "--block_on_gui"
    comandos.append(f"quartus_sh -t /opt/altera/13.0sp1/quartus/common/tcl/internal/nativelink/qnativesim.tcl {gui} {toplevel} {toplevel}")

comando_completo = " && ".join(comandos)
try:
    subprocess.run(["docker", "exec", nome_do_container, "bash", "-c", comando_completo], check=True)
except Exception:
    print("Erro na compilação ou simulação (certifique-se de que o container está ativo). Tentando gerar relatório do Time Quest Analyzer...")

generate_tcl(pasta, toplevel)

try:
    subprocess.run(["docker", "exec", nome_do_container, "bash", "-c", f'cd {pasta} && quartus_sta -t "/home/jonatan/Documentos/UFSC/MONITORIA_SD/script-compile-quartus/netlist.tcl"'], check=True)
except Exception:
    print("Erro em gerar o relatório do Time Quest Analyzer.")
    sys.exit(1)
