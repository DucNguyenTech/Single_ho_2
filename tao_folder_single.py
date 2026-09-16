import os
import shutil

# Thư mục hiện tại mà Jupyter Notebook đang chạy
BASE_DIR = os.getcwd()

# Folder mới
SINGLE_HO_DIR = os.path.join(BASE_DIR, "Single_ho")

# Tạo folder Single_ho
os.makedirs(SINGLE_HO_DIR, exist_ok=True)


# ============================================================
# 1. Tạo các file mới rỗng
# ============================================================

empty_files = [
    "alpha_false_single.txt",
    "alpha_pass_single.txt",
    "alpha_single.txt",
    "gen_alpha_single.py",
    "run_single.py",
    "loc_single.ipynb",
]

for filename in empty_files:
    filepath = os.path.join(SINGLE_HO_DIR, filename)

    open(filepath, "w", encoding="utf-8").close()


# ============================================================
# 2. Copy các file từ BASE_DIR vào Single_ho
# ============================================================

# ace_lib.py
shutil.copy2(
    os.path.join(BASE_DIR, "ace_lib.py"),
    os.path.join(SINGLE_HO_DIR, "ace_lib.py")
)

# helpful_functions.py
shutil.copy2(
    os.path.join(BASE_DIR, "helpful_functions.py"),
    os.path.join(SINGLE_HO_DIR, "helpful_functions.py")
)

# config.json -> config_single.json
shutil.copy2(
    os.path.join(BASE_DIR, "config.json"),
    os.path.join(SINGLE_HO_DIR, "config_single.json")
)

print("✅ Đã tạo Single_ho thành công!")
print(f"📁 Vị trí: {SINGLE_HO_DIR}")