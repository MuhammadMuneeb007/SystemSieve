"""Application-wide constants: registry paths, safety keyword lists, and category maps.

These lists are heuristics, not guarantees. They are used to warn users and to bias
default choices toward caution, never to silently permit destructive actions.
"""

from __future__ import annotations

APP_NAME = "SystemSieve"
APP_ID = "systemsieve"
ORG_NAME = "SystemSieve"

# --- Registry uninstall locations -------------------------------------------------

UNINSTALL_KEY_PATHS: list[tuple[str, str]] = [
    ("HKEY_LOCAL_MACHINE", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (
        "HKEY_LOCAL_MACHINE",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ),
    ("HKEY_CURRENT_USER", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]

# --- Safety classification ---------------------------------------------------------

SAFETY_NORMAL = "normal"
SAFETY_REVIEW = "review"
SAFETY_PROTECTED = "protected"
SAFETY_UNKNOWN = "unknown"

ACTIVITY_HIGH = "high"
ACTIVITY_MEDIUM = "medium"
ACTIVITY_LOW = "low"
ACTIVITY_UNAVAILABLE = "unavailable"

# Publisher / name substrings that indicate categories requiring a warning before removal.
# Matching is case-insensitive and applied to display name + publisher.

VCREDIST_KEYWORDS = ["visual c++", "vc_redist", "vcredist", "visual studio.*redistributable"]
DOTNET_KEYWORDS = [".net runtime", ".net core", ".net framework", "microsoft .net", "aspnet"]
DRIVER_KEYWORDS = [
    "driver",
    "chipset",
    "graphics driver",
    "nvidia graphics",
    "amd software",
    "intel graphics",
    "realtek",
    "broadcom",
    "wireless driver",
]
SECURITY_SOFTWARE_KEYWORDS = [
    "antivirus",
    "defender",
    "firewall",
    "endpoint protection",
    "norton",
    "mcafee",
    "bitdefender",
    "kaspersky",
    "malwarebytes",
    "webroot",
    "eset",
    "sophos",
    "crowdstrike",
    "trend micro",
]
VPN_KEYWORDS = [
    "vpn",
    "nordvpn",
    "expressvpn",
    "openvpn",
    "wireguard",
    "tunnelbear",
    "cisco anyconnect",
    "surfshark",
    "protonvpn",
]
PYTHON_RUNTIME_KEYWORDS = ["python 3", "python 2", "python launcher", "anaconda", "miniconda"]
JAVA_RUNTIME_KEYWORDS = [
    "java se",
    "java runtime",
    "java(tm)",
    "jdk",
    "jre",
    "openjdk",
    "eclipse temurin",
]
DATABASE_SERVER_KEYWORDS = [
    "sql server",
    "mysql server",
    "postgresql",
    "mongodb",
    "mariadb",
    "oracle database",
    "redis",
]
DEV_TOOL_KEYWORDS = [
    "visual studio",
    "git",
    "docker desktop",
    "node.js",
    "jdk",
    "android studio",
    "visual studio code",
    "jetbrains",
    "windows sdk",
    "windows driver kit",
]
SHARED_FRAMEWORK_KEYWORDS = [
    "directx",
    "webview2",
    "microsoft edge webview",
    "runtime library",
    "universal crt",
    "microsoft visual studio.*tools",
]

WARN_BEFORE_REMOVAL_CATEGORIES: dict[str, list[str]] = {
    "Microsoft Visual C++ Redistributable": VCREDIST_KEYWORDS,
    ".NET Runtime": DOTNET_KEYWORDS,
    "Hardware Driver": DRIVER_KEYWORDS,
    "Security Software": SECURITY_SOFTWARE_KEYWORDS,
    "VPN Software": VPN_KEYWORDS,
    "Python Runtime": PYTHON_RUNTIME_KEYWORDS,
    "Java Runtime": JAVA_RUNTIME_KEYWORDS,
    "Database Server": DATABASE_SERVER_KEYWORDS,
    "Development Tool": DEV_TOOL_KEYWORDS,
    "Shared Framework": SHARED_FRAMEWORK_KEYWORDS,
}

# Names/publishers that must never be offered for removal at all (core OS components).
PROTECTED_HARD_BLOCK_KEYWORDS = [
    "microsoft windows operating system",
    "windows security update",
    "windows malicious software removal tool",
    "kb-",  # Windows update KB articles when they appear as uninstall entries
]

# --- Protected filesystem paths -----------------------------------------------------
# Whole-directory deletion of these paths (and their exact match) is always blocked.
# Scanning is still permitted; only bulk/whole-directory deletion is blocked.

PROTECTED_DIRECTORY_NAMES = [
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
]

# --- File categories -----------------------------------------------------------------

FILE_CATEGORY_EXTENSIONS: dict[str, list[str]] = {
    "Documents": [
        ".doc",
        ".docx",
        ".pdf",
        ".txt",
        ".rtf",
        ".odt",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".csv",
        ".md",
        ".epub",
    ],
    "Images": [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".svg",
        ".webp",
        ".tiff",
        ".ico",
        ".heic",
        ".raw",
    ],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".cab"],
    "Installers": [".exe", ".msi", ".msix", ".appx", ".msixbundle"],
    "Source Code": [
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".html",
        ".css",
        ".sql",
    ],
    "Data Files": [".json", ".xml", ".yaml", ".yml", ".db", ".sqlite", ".sqlite3", ".log"],
    "Machine Learning Models": [
        ".pt",
        ".pth",
        ".ckpt",
        ".onnx",
        ".h5",
        ".hdf5",
        ".pkl",
        ".joblib",
        ".parquet",
        ".feather",
        ".npy",
        ".npz",
        ".safetensors",
        ".gguf",
    ],
    "Genomics/Scientific": [
        ".fastq",
        ".fastq.gz",
        ".fq",
        ".bam",
        ".sam",
        ".vcf",
        ".vcf.gz",
        ".bed",
        ".fasta",
        ".fa",
    ],
    "Temporary Files": [".tmp", ".temp", ".bak", ".old", ".~", ".crdownload", ".part"],
    "Logs": [".log", ".etl", ".evtx"],
}

# Directory name patterns that indicate special categories regardless of extension.
VENV_DIRECTORY_NAMES = ["venv", ".venv", "env", "virtualenv", "site-packages", "node_modules"]
CACHE_DIRECTORY_NAMES = ["__pycache__", ".cache", "cache", "temp", "tmp", "cachedstorage"]

DEFAULT_OLD_FILE_DAYS = 365
DEFAULT_RECENT_FILE_DAYS = 30
