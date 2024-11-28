
    # Abrir o projeto Quartus
    project_open -force "/home/jonatan/Documentos/UFSC/MONITORIA_SD/242/AP1/grupo-14/decodificadorBCD7Seg/decodificadorBCD7Seg.qpf" -revision decodificadorBCD7Seg
    
    # Compilar e gerar netlist com Zero IC Delays
    create_timing_netlist -model slow -zero_ic_delays
    
    # Exportar o relatório Datasheet
    report_datasheet -panel_name "Datasheet Report" -file "relatorio_datasheet.html"
    
    # Exportar o relatório Fmax Summary
    report_clock_fmax_summary -panel_name "Fmax Summary" -file "relatorio_fmax_summary.html"
    
    # Fechar o projeto
    project_close
    