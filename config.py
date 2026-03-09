# Configuração do Projeto PPM-C

# Parâmetros de compressão
MAX_K = 10  # Valor máximo de k_max para testes
DEFAULT_K = 3  # Valor padrão de k_max

# Configurações de teste
TEST_FILE_SIZE_LIMIT = 100000  # Limitar arquivos de teste a 100KB para velocidade
SILESIA_DOWNLOAD_TIMEOUT = 300  # Timeout para download em segundos

# Configurações de corpus
ENGLISH_CORPUS_SIZE_MB = 1  # Tamanho do corpus em inglês para testes (1MB para velocidade)
MIN_CORPUS_SIZE_MB = 100  # Tamanho mínimo para corpus completo

# URLs do Corpus Silesia
SILESIA_BASE_URL = "http://sun.aei.polsl.pl/~sdeor/corpus/"
SILESIA_FILES = [
    "dickens",
    "mozilla", 
    "mr",
    "nci",
    "ooffice",
    "osdb",
    "reymont",
    "samba",
    "sao",
    "webster",
    "xml",
    "x-ray"
]

# Configurações de saída
RESULTS_DIR = "results"
DATA_DIR = "data"
VISUALIZATIONS_DIR = "visualizations"

# Configurações de gráficos
PLOT_DPI = 300
PLOT_STYLE = "default"
FIGURE_SIZE = (12, 8)

# Configurações de benchmark
COMPARE_WITH_ZIP = True
COMPARE_WITH_GZIP = True
VERIFY_INTEGRITY = True

# Configurações de geração de texto
DEFAULT_TEXT_LENGTH = 1000
MAX_TEXT_LENGTH = 10000
