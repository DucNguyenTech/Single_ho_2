import pandas as pd
import os
import json
import csv
import gc
import ace_lib as ace
from ace_lib import check_session_timeout, get_simulation_result_json
import time
from datetime import datetime
import pytz
import concurrent.futures
import threading
import sys
import requests
import random
import tempfile


# ============================================================
# ĐỌC CONFIG
# ============================================================
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_FILE = os.path.join(BASE_DIR, "session.json")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(CURRENT_DIR, "config_single.json")

with open(config_file, "r", encoding="utf-8") as file:
    config = json.load(file)

default_settings = config.get("default_settings")
output_csv = config.get("OUTPUT_CSV")


# ============================================================
# CẤU HÌNH
# ============================================================

VIETNAM_TZ = pytz.timezone("Asia/Ho_Chi_Minh")


# ============================================================
# WORKER
# ============================================================

# Tối đa 8 alpha chạy đồng thời
max_workers = 5


# ============================================================
# BATCH
# ============================================================

# Mỗi batch chỉ load 1500 alpha
MAX_ALPHA_PER_BATCH = 1500


# ============================================================
# WATCHDOG
# ============================================================

# ------------------------------------------------------------
# Một alpha chạy quá thời gian này => coi là bị treo
# ------------------------------------------------------------

MAX_ALPHA_RUNTIME = 45 * 60


# ------------------------------------------------------------
# Nếu toàn bộ hệ thống không có alpha nào hoàn thành
# trong khoảng thời gian này => restart process.
#
# 60 phút = đủ rộng cho simulation lâu,
# nhưng vẫn tránh treo nhiều giờ/ngày.
# ------------------------------------------------------------

WATCHDOG_NO_PROGRESS = 60 * 60


# ------------------------------------------------------------
# Main loop kiểm tra watchdog mỗi bao nhiêu giây
# ------------------------------------------------------------

WATCHDOG_CHECK_INTERVAL = 15


# ------------------------------------------------------------
# Khi restart, chờ một chút để tránh restart liên tục
# ------------------------------------------------------------

RESTART_DELAY = 5


# ============================================================
# URL
# ============================================================

SIMULATION_URL = (
    "https://api.worldquantbrain.com/simulations"
)


# ============================================================
# EVENT / LOCK
# ============================================================

stop_event = threading.Event()

csv_write_lock = threading.Lock()

pass_write_lock = threading.Lock()

false_write_lock = threading.Lock()


# ============================================================
# WATCHDOG STATE
# ============================================================

watchdog_lock = threading.Lock()


# Thời điểm alpha cuối cùng hoàn thành
last_progress_time = time.time()


# Số alpha đã hoàn thành
completed_alpha_count = 0


# Số alpha đang chạy
running_alpha_count = 0


# Batch hiện tại
current_batch_number = 0


# Session hiện tại
current_session_number = 0


# ============================================================
# WATCHDOG HELPERS
# ============================================================

def watchdog_mark_start():
    """
    Đánh dấu có alpha bắt đầu chạy.
    """

    global running_alpha_count

    with watchdog_lock:

        running_alpha_count += 1


def watchdog_mark_done():
    """
    Đánh dấu alpha đã hoàn thành.

    Đây là heartbeat chính của watchdog.
    """

    global last_progress_time
    global completed_alpha_count
    global running_alpha_count

    with watchdog_lock:

        last_progress_time = time.time()

        completed_alpha_count += 1

        if running_alpha_count > 0:
            running_alpha_count -= 1


def watchdog_mark_stop():
    """
    Worker kết thúc mà không phải completed.
    """

    global running_alpha_count

    with watchdog_lock:

        if running_alpha_count > 0:
            running_alpha_count -= 1


def get_watchdog_state():

    with watchdog_lock:

        return (
            last_progress_time,
            completed_alpha_count,
            running_alpha_count
        )


# ============================================================
# RESTART PROCESS
# ============================================================

def restart_process(reason):

    print()
    print("=" * 80)
    print("🚨 WATCHDOG RESTART")
    print(reason)
    print(
        f"Time : {datetime.now(VIETNAM_TZ)}"
    )
    print("=" * 80)
    print()

    try:

        stop_event.set()

    except Exception:
        pass


    # Cho log được flush
    sys.stdout.flush()
    sys.stderr.flush()


    time.sleep(
        RESTART_DELAY
    )


    # --------------------------------------------------------
    # Restart chính process Python
    #
    # Không chỉ tạo Session mới.
    # Đây là reset hoàn toàn process.
    # --------------------------------------------------------

    os.execv(
        sys.executable,
        [
            sys.executable
        ] + sys.argv
    )


# ============================================================
# WATCHDOG CHECK
# ============================================================

def watchdog_check(
    future_start_times,
    future_to_alpha
):
    """
    Kiểm tra:

    1. Future nào chạy quá MAX_ALPHA_RUNTIME
    2. Toàn bộ hệ thống không có progress quá WATCHDOG_NO_PROGRESS
    """

    now = time.time()


    # ========================================================
    # CHECK FUTURE QUÁ LÂU
    # ========================================================

    for future, start_time in list(
        future_start_times.items()
    ):

        runtime = now - start_time


        if runtime >= MAX_ALPHA_RUNTIME:

            alpha_data = future_to_alpha.get(
                future
            )


            alpha_name = None

            try:

                if alpha_data:

                    alpha_name = alpha_data.get(
                        "regular"
                    )

            except Exception:

                alpha_name = None


            restart_process(
                (
                    f"Future chạy quá "
                    f"{MAX_ALPHA_RUNTIME / 60:.0f} phút. "
                    f"Runtime={runtime / 60:.1f} phút. "
                    f"Alpha={alpha_name}"
                )
            )


    # ========================================================
    # CHECK GLOBAL NO PROGRESS
    # ========================================================

    (
        last_progress,
        completed_count,
        running_count
    ) = get_watchdog_state()


    no_progress_time = (
        now - last_progress
    )


    if (
        running_count > 0
        and no_progress_time >= WATCHDOG_NO_PROGRESS
    ):

        restart_process(
            (
                f"Không có alpha hoàn thành trong "
                f"{no_progress_time / 60:.1f} phút. "
                f"Completed={completed_count}, "
                f"Running={running_count}"
            )
        )


# ============================================================
# PROCESS DATA
# ============================================================

def process_data(result_data, output_csv):

    """
    Lấy dữ liệu cần thiết từ simulation result
    và ghi trực tiếp vào CSV.

    Không tạo DataFrame 1 dòng.
    """

    try:

        # ----------------------------------------------------
        # IS
        # ----------------------------------------------------

        is_data = result_data.get(
            "is",
            {}
        )

        checks_data = is_data.get(
            "checks",
            []
        )


        # ----------------------------------------------------
        # DEFAULT CHECK VALUES
        # ----------------------------------------------------

        concentrated_weight_value = None
        concentrated_weight_result = None

        low_2y_sharpe_value = None
        low_2y_sharpe_result = None

        low_sub_universe_sharpe_value = None
        low_sub_universe_sharpe_result = None

        IS_LADDER_SHARPE_value = None
        IS_LADDER_SHARPE_result = None

        LOW_ROBUST_UNIVERSE_SHARPE_value = None
        LOW_ROBUST_UNIVERSE_SHARPE_result = None

        MATCHES_PYRAMID_effective = None
        MATCHES_PYRAMID_multiplier = None
        MATCHES_PYRAMID_result = None


        # ----------------------------------------------------
        # Duyệt checks
        # ----------------------------------------------------

        for check in checks_data:

            if not isinstance(
                check,
                dict
            ):
                continue


            check_name = check.get(
                "name"
            )


            if check_name == (
                "CONCENTRATED_WEIGHT"
            ):

                concentrated_weight_value = (
                    check.get("value")
                )

                concentrated_weight_result = (
                    check.get("result")
                )


            elif check_name == (
                "LOW_2Y_SHARPE"
            ):

                low_2y_sharpe_value = (
                    check.get("value")
                )

                low_2y_sharpe_result = (
                    check.get("result")
                )


            elif check_name == (
                "LOW_SUB_UNIVERSE_SHARPE"
            ):

                low_sub_universe_sharpe_value = (
                    check.get("value")
                )

                low_sub_universe_sharpe_result = (
                    check.get("result")
                )


            elif check_name == (
                "IS_LADDER_SHARPE"
            ):

                IS_LADDER_SHARPE_value = (
                    check.get("value")
                )

                IS_LADDER_SHARPE_result = (
                    check.get("result")
                )


            elif check_name == (
                "MATCHES_PYRAMID"
            ):

                MATCHES_PYRAMID_effective = (
                    check.get("effective")
                )

                MATCHES_PYRAMID_multiplier = (
                    check.get("multiplier")
                )

                MATCHES_PYRAMID_result = (
                    check.get("result")
                )


            elif check_name == (
                "LOW_ROBUST_UNIVERSE_SHARPE"
            ):

                LOW_ROBUST_UNIVERSE_SHARPE_value = (
                    check.get("value")
                )

                LOW_ROBUST_UNIVERSE_SHARPE_result = (
                    check.get("result")
                )


        # ----------------------------------------------------
        # REGULAR
        # ----------------------------------------------------

        regular_data = result_data.get(
            "regular",
            {}
        )

        if not isinstance(
            regular_data,
            dict
        ):

            regular_data = {}


        # ----------------------------------------------------
        # ROW
        # ----------------------------------------------------

        row_data = {

            "id":
                result_data.get("id"),

            "sharpe":
                is_data.get("sharpe"),

            "fitness":
                is_data.get("fitness"),


            "LOW_2Y_SHARPE_value":
                low_2y_sharpe_value,

            "LOW_SUB_UNIVERSE_SHARPE_value":
                low_sub_universe_sharpe_value,

            "LOW_ROBUST_UNIVERSE_SHARPE_value":
                LOW_ROBUST_UNIVERSE_SHARPE_value,


            "pnl":
                is_data.get("pnl"),

            "turnover":
                is_data.get("turnover"),

            "returns":
                is_data.get("returns"),

            "drawdown":
                is_data.get("drawdown"),

            "margin":
                is_data.get("margin"),


            "CONCENTRATED_WEIGHT_value":
                concentrated_weight_value,

            "CONCENTRATED_WEIGHT_result":
                concentrated_weight_result,


            "LOW_2Y_SHARPE_result":
                low_2y_sharpe_result,

            "LOW_SUB_UNIVERSE_SHARPE_result":
                low_sub_universe_sharpe_result,


            "IS_LADDER_SHARPE_result":
                IS_LADDER_SHARPE_result,


            "MATCHES_PYRAMID_effective":
                MATCHES_PYRAMID_effective,

            "MATCHES_PYRAMID_multiplier":
                MATCHES_PYRAMID_multiplier,

            "MATCHES_PYRAMID_result":
                MATCHES_PYRAMID_result,


            "operatorCount":
                regular_data.get(
                    "operatorCount"
                ),

            "regular":
                regular_data.get(
                    "code"
                ),


            "bookSize":
                is_data.get("bookSize"),

            "longCount":
                is_data.get("longCount"),

            "shortCount":
                is_data.get("shortCount"),

            "startDate":
                is_data.get("startDate")
        }


        # ----------------------------------------------------
        # Ghi CSV
        # ----------------------------------------------------

        with csv_write_lock:

            file_exists = (
                os.path.exists(output_csv)
                and os.path.getsize(output_csv) > 0
            )


            with open(
                output_csv,
                "a",
                newline="",
                encoding="utf-8"
            ) as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=CSV_COLUMNS,
                    extrasaction="ignore"
                )


                if not file_exists:

                    writer.writeheader()


                writer.writerow(
                    row_data
                )


        # ----------------------------------------------------
        # Giải phóng
        # ----------------------------------------------------

        del row_data
        del checks_data
        del regular_data

        return True


    except Exception as e:

        print(
            f"❌ Lỗi khi ghi file CSV: {e}"
        )

        return False


# ============================================================
# CSV SCHEMA
# ============================================================

CSV_COLUMNS = [

    "id",
    "sharpe",
    "fitness",

    "LOW_2Y_SHARPE_value",
    "LOW_SUB_UNIVERSE_SHARPE_value",
    "LOW_ROBUST_UNIVERSE_SHARPE_value",

    "pnl",
    "turnover",
    "returns",
    "drawdown",
    "margin",

    "CONCENTRATED_WEIGHT_value",
    "CONCENTRATED_WEIGHT_result",

    "LOW_2Y_SHARPE_result",
    "LOW_SUB_UNIVERSE_SHARPE_result",

    "IS_LADDER_SHARPE_result",

    "MATCHES_PYRAMID_effective",
    "MATCHES_PYRAMID_multiplier",
    "MATCHES_PYRAMID_result",

    "operatorCount",
    "regular",

    "bookSize",
    "longCount",
    "shortCount",
    "startDate"
]


# ============================================================
# ENSURE CSV SCHEMA
# ============================================================

def ensure_csv_schema(output_csv):

    # --------------------------------------------------------
    # Nếu chưa có file
    # --------------------------------------------------------

    if not os.path.exists(output_csv):

        with open(
            output_csv,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(
                file
            )

            writer.writerow(
                CSV_COLUMNS
            )


        print(
            "✅ Tạo file CSV mới với schema chuẩn"
        )

        return


    # --------------------------------------------------------
    # File rỗng
    # --------------------------------------------------------

    if os.path.getsize(output_csv) == 0:

        with open(
            output_csv,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(
                file
            )

            writer.writerow(
                CSV_COLUMNS
            )


        print(
            "✅ CSV rỗng → tạo header"
        )

        return


    # --------------------------------------------------------
    # Chỉ đọc HEADER
    #
    # Không pd.read_csv toàn bộ file.
    # Đây là điểm giảm RAM quan trọng.
    # --------------------------------------------------------

    try:

        with open(
            output_csv,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.reader(
                file
            )

            existing_columns = next(
                reader
            )


    except Exception as e:

        print(
            f"❌ Không đọc được CSV header: {e}"
        )

        return


    # --------------------------------------------------------
    # Nếu đúng schema
    # --------------------------------------------------------

    if existing_columns == CSV_COLUMNS:

        print(
            "✅ CSV schema đã đúng"
        )

        return


    # --------------------------------------------------------
    # Nếu thiếu / sai schema
    #
    # Rewrite theo stream để không load toàn bộ CSV vào RAM.
    # --------------------------------------------------------

    print(
        "⚠️ CSV schema khác chuẩn → đang chuẩn hóa..."
    )


    temp_file = (
        output_csv
        + ".tmp"
    )


    try:

        with open(
            output_csv,
            "r",
            newline="",
            encoding="utf-8"
        ) as source, open(
            temp_file,
            "w",
            newline="",
            encoding="utf-8"
        ) as target:

            reader = csv.DictReader(
                source
            )

            writer = csv.DictWriter(
                target,
                fieldnames=CSV_COLUMNS,
                extrasaction="ignore"
            )

            writer.writeheader()


            for row in reader:

                writer.writerow(
                    {
                        column:
                        row.get(column)
                        for column in CSV_COLUMNS
                    }
                )


        os.replace(
            temp_file,
            output_csv
        )


        print(
            "✅ Schema CSV đã được chuẩn hóa"
        )


    except Exception as e:

        print(
            f"❌ Lỗi chuẩn hóa CSV: {e}"
        )


        try:

            if os.path.exists(
                temp_file
            ):

                os.remove(
                    temp_file
                )

        except Exception:
            pass


# ============================================================
# LOAD SESSION
# ============================================================

def load_session():

    if not os.path.exists(
        SESSION_FILE
    ):

        print(
            "Không tìm thấy session, hãy xác thực lại."
        )

        return None


    try:

        with open(
            SESSION_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            cookies = json.load(
                f
            )


        token = cookies.get(
            "t"
        )


        if not token:

            print(
                "❌ session.json không có token t"
            )

            return None


        return token


    except Exception as e:

        print(
            f"❌ Lỗi load session: {e}"
        )

        return None


# ============================================================
# LOAD HEADERS
# ============================================================

def load_headers():

    token = load_session()


    if not token:

        return {}


    return {

        "Content-Type":
            "application/json",

        "Cookie":
            f"t={token}"
    }


# ============================================================
# READ ALPHA
# ============================================================

def read_alpha(
    path,
    max_lines=1500
):

    # --------------------------------------------------------
    # PASS
    # --------------------------------------------------------

    pass_lines = set()


    if os.path.exists(
        "alpha_pass_single.txt"
    ):

        with open(
            "alpha_pass_single.txt",
            encoding="utf-8"
        ) as f:

            for line in f:

                stripped = line.strip()

                if stripped:

                    pass_lines.add(
                        stripped
                    )


    # --------------------------------------------------------
    # FALSE
    # --------------------------------------------------------

    false_lines = set()


    if os.path.exists(
        "alpha_false_single.txt"
    ):

        with open(
            "alpha_false_single.txt",
            encoding="utf-8"
        ) as f:

            for line in f:

                stripped = line.strip()

                if stripped:

                    false_lines.add(
                        stripped
                    )


    # --------------------------------------------------------
    # FILTERED
    # --------------------------------------------------------

    filtered_alphas = (
        pass_lines
        | false_lines
    )


    del pass_lines
    del false_lines


    # --------------------------------------------------------
    # READ ALPHA
    #
    # Chỉ giữ tối đa 1500 alpha trong RAM.
    # --------------------------------------------------------

    list_alphas = []


    with open(
        path,
        encoding="utf-8"
    ) as f:

        for line in f:

            stripped = line.strip()


            if (
                stripped
                and stripped not in filtered_alphas
            ):

                list_alphas.append(
                    stripped
                )


                if len(
                    list_alphas
                ) >= max_lines:

                    break


    del filtered_alphas


    return list_alphas


# ============================================================
# WRITE PASS
# ============================================================

def write_alpha_pass(alpha):

    with pass_write_lock:

        with open(
            "alpha_pass_single.txt",
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                alpha + "\n"
            )


# ============================================================
# WRITE FALSE
# ============================================================

def write_alpha_false(alpha):

    with false_write_lock:

        with open(
            "alpha_false_single.txt",
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                alpha + "\n"
            )


# ============================================================
# PROCESS ALPHA
# ============================================================

def process_alpha(
    s,
    alpha_data,
    stop_event
):

    watchdog_mark_start()


    alpha_regular = None


    try:

        # ----------------------------------------------------
        # STOP
        # ----------------------------------------------------

        if stop_event.is_set():

            return False


        # ----------------------------------------------------
        # REGULAR
        # ----------------------------------------------------

        if alpha_data.get(
            "regular"
        ) is None:

            return None


        alpha_regular = alpha_data[
            "regular"
        ]


        # ====================================================
        # POST SIMULATION
        # ====================================================

        while True:

            if stop_event.is_set():

                return False


            simulate_response = None


            try:

                simulate_response = s.post(
                    SIMULATION_URL,
                    json=alpha_data,
                    timeout=300
                )


            except requests.exceptions.Timeout:

                print(
                    f"⌛ POST simulation Timeout "
                    f"{datetime.now(VIETNAM_TZ)}"
                )

                write_alpha_false(
                    alpha_regular
                )

                return {
                    "completed": False
                }


            except requests.exceptions.ConnectionError as e:

                print(
                    f"🌐 POST lỗi mạng: {e}"
                )

                time.sleep(30)

                continue


            except requests.exceptions.RequestException as e:

                print(
                    f"⚠️ POST request error: {e}"
                )

                time.sleep(30)

                continue


            # ------------------------------------------------
            # 201
            # ------------------------------------------------

            if (
                simulate_response.status_code
                == 201
            ):

                break


            # ------------------------------------------------
            # 401
            # ------------------------------------------------

            elif (
                simulate_response.status_code
                == 401
            ):

                print(
                    f"🔐 Session đã hết hạn "
                    f"{datetime.now(VIETNAM_TZ)}"
                )

                stop_event.set()

                return False


            # ------------------------------------------------
            # 429
            # ------------------------------------------------

            elif (
                simulate_response.status_code
                == 429
            ):

                try:

                    retry_after = int(
                        simulate_response.headers.get(
                            "Retry-After",
                            100
                        )
                    )

                except Exception:

                    retry_after = 100


                jitter = random.uniform(
                    1,
                    6
                )


                total_sleep = (
                    retry_after
                    + jitter
                )


                print(
                    f"🚫 429 SIMULATION_LIMIT_EXCEEDED. "
                    f"Sleep {total_sleep:.2f}s -- "
                    f"{datetime.now(VIETNAM_TZ)}"
                )


                del simulate_response


                time.sleep(
                    total_sleep
                )


                continue


            # ------------------------------------------------
            # 502
            # ------------------------------------------------

            elif (
                simulate_response.status_code
                == 502
            ):

                sleep_time = random.uniform(
                    40,
                    60
                )


                print(
                    f"🌐 502 Bad Gateway. "
                    f"Sleep {sleep_time:.2f}s -- "
                    f"{datetime.now(VIETNAM_TZ)}"
                )


                del simulate_response


                time.sleep(
                    sleep_time
                )


                continue


            # ------------------------------------------------
            # ERROR KHÁC
            # ------------------------------------------------

            else:

                response_status = (
                    simulate_response.status_code
                )

                response_text = (
                    simulate_response.text
                )


                print(
                    f"⚠️ Simulation POST lỗi: "
                    f"{response_status}, "
                    f"{response_text[:500]}"
                )


                write_alpha_false(
                    alpha_regular
                )


                del simulate_response


                return {
                    "completed": False
                }


        # ====================================================
        # LOCATION
        # ====================================================

        simulation_progress_url = (
            simulate_response
            .headers
            .get("Location")
        )


        del simulate_response


        if not simulation_progress_url:

            print(
                f"❌ Không có Location "
                f"cho alpha {alpha_regular}"
            )


            write_alpha_false(
                alpha_regular
            )


            return {
                "completed": False
            }


        # ====================================================
        # CHECK PROGRESS
        # ====================================================

        progress_json = None

        progress_status_code = None

        error_flag = False


        while True:

            if stop_event.is_set():

                return False


            simulation_progress_response = None


            try:

                simulation_progress_response = s.get(
                    simulation_progress_url,
                    timeout=1800
                )


            except requests.exceptions.ReadTimeout:

                print(
                    f"❌ GET simulation timeout "
                    f"{datetime.now(VIETNAM_TZ)}"
                )


                stop_event.set()

                return False


            except requests.exceptions.ConnectionError as e:

                print(
                    f"🌐 GET lỗi mạng: {e}"
                )

                time.sleep(30)

                continue


            except requests.exceptions.RequestException as e:

                print(
                    f"⚠️ GET request error: {e}"
                )

                time.sleep(30)

                continue


            progress_status_code = (
                simulation_progress_response.status_code
            )


            # ------------------------------------------------
            # Parse JSON nếu cần
            # ------------------------------------------------

            progress_json = None


            if (
                progress_status_code // 100
                != 2
            ):

                try:

                    progress_json = (
                        simulation_progress_response.json()
                    )

                except Exception:

                    progress_json = {}


                if progress_json == {
                    "detail":
                    "Incorrect authentication credentials."
                }:

                    print(
                        f"🔐 Session hết hạn "
                        f"{datetime.now(VIETNAM_TZ)}"
                    )


                    del progress_json
                    del simulation_progress_response


                    stop_event.set()

                    return False


                print(
                    f"Simulation failed, "
                    f"Status code: "
                    f"{progress_status_code}"
                )


                del progress_json
                del simulation_progress_response


                time.sleep(30)

                continue


            # ------------------------------------------------
            # Retry-After
            # ------------------------------------------------

            retry_after = (
                simulation_progress_response
                .headers
                .get(
                    "Retry-After",
                    0
                )
            )


            try:

                retry_after = float(
                    retry_after
                )

            except Exception:

                retry_after = 0


            # ------------------------------------------------
            # Simulation hoàn thành
            # ------------------------------------------------

            if retry_after <= 0:

                if progress_json is None:

                    try:

                        progress_json = (
                            simulation_progress_response
                            .json()
                        )

                    except Exception:

                        progress_json = {}


                if (
                    progress_json.get(
                        "status",
                        "ERROR"
                    )
                    == "ERROR"
                ):

                    error_flag = True


                del simulation_progress_response

                break


            # ------------------------------------------------
            # Chưa xong
            # ------------------------------------------------

            del progress_json
            del simulation_progress_response


            time.sleep(
                retry_after
            )


        # ====================================================
        # SIMULATION ERROR
        # ====================================================

        if error_flag:

            print(
                f"❌ Simulation failed. "
                f"{progress_json} "
                f"Status code: "
                f"{progress_status_code}"
            )


            if progress_json == {
                "detail":
                "Incorrect authentication credentials."
            }:

                stop_event.set()

                del progress_json

                return False


            write_alpha_false(
                alpha_regular
            )


            del progress_json


            return {
                "completed": False
            }


        # ====================================================
        # ALPHA ID
        # ====================================================

        alpha = progress_json.get(
            "alpha",
            0
        )


        if alpha == 0:

            print(
                f"❌ Simulation alpha "
                f"{progress_json.get('id')} "
                f"failed. "
                f"{progress_json}"
            )


            del progress_json


            write_alpha_false(
                alpha_regular
            )


            return {
                "completed": False
            }


        # ----------------------------------------------------
        # Không cần progress JSON nữa
        # ----------------------------------------------------

        del progress_json


        # ====================================================
        # LẤY KẾT QUẢ
        # ====================================================

        simulation_result = (
            get_simulation_result_json(
                s,
                alpha
            )
        )


        # ====================================================
        # GHI CSV
        # ====================================================

        Flat_process_data = process_data(
            simulation_result,
            output_csv
        )


        # Không giữ JSON lớn nữa
        del simulation_result


        # ----------------------------------------------------
        # Nếu ghi CSV thành công
        # ----------------------------------------------------

        if Flat_process_data:
            
            write_alpha_pass(
                alpha_regular
            )
            print(
                "555",
                end="",
                flush=True
            )

        else:

            write_alpha_false(
                alpha_regular
            )


        return {
            "completed": bool(
                Flat_process_data
            )
        }


    except Exception as e:

        print(
            f"❌ Exception process_alpha "
            f"{alpha_regular}: {e}"
        )


        if alpha_regular:

            try:

                write_alpha_false(
                    alpha_regular
                )

            except Exception:
                pass


        return {
            "completed": False
        }


    finally:

        try:

            del alpha_data

        except Exception:
            pass


        watchdog_mark_done()


# ============================================================
# TẠO SESSION
# ============================================================

def create_session():

    new_session = ace.SingleSession()


    headers = load_headers()


    if not headers:

        print(
            "❌ Không load được headers"
        )

        return None


    new_session.headers.update(
        headers
    )


    return new_session


# ============================================================
# MAIN
# ============================================================

def main():

    global current_batch_number
    global current_session_number
    global last_progress_time


    # ========================================================
    # CSV SCHEMA
    # ========================================================

    ensure_csv_schema(
        output_csv
    )


    # ========================================================
    # SESSION
    # ========================================================

    s = create_session()


    if s is None:

        print(
            "❌ Không tạo được session."
        )

        return


    current_session_number = 1


    print(
        f"🚀 Start Run Alpha "
        f"{datetime.now(VIETNAM_TZ)}"
    )

    print(
        f"Workers: {max_workers}"
    )

    print(
        f"Alpha/batch: {MAX_ALPHA_PER_BATCH}"
    )

    print(
        f"Watchdog alpha: "
        f"{MAX_ALPHA_RUNTIME / 60:.0f} phút"
    )

    print(
        f"Watchdog no progress: "
        f"{WATCHDOG_NO_PROGRESS / 60:.0f} phút"
    )


    # ========================================================
    # MAIN LOOP
    # ========================================================
    count_load = 0
    while True:

        # ----------------------------------------------------
        # Kiểm tra session
        # ----------------------------------------------------

        try:

            time_session = (
                check_session_timeout(s)
            )

        except Exception as e:

            print(
                f"⚠️ check_session_timeout lỗi: {e}"
            )

            time_session = 0


        # ====================================================
        # SESSION CÒN
        # ====================================================

        if time_session > 0:

            print()

            print(
                "=" * 80
            )

            print(
                f"Session còn: "
                f"{time_session} ---- {datetime.now(VIETNAM_TZ)}"
            )

            print(
                "=" * 80
            )


            # ------------------------------------------------
            # RESET EVENT
            # ------------------------------------------------

            stop_event.clear()


            # ------------------------------------------------
            # RESET WATCHDOG
            # ------------------------------------------------

            with watchdog_lock:

                last_progress_time = (
                    time.time()
                )


            # =================================================
            # LOAD 1500 ALPHA
            # =================================================

            list_alphas = read_alpha(
                "alpha_single.txt",
                max_lines=MAX_ALPHA_PER_BATCH
            )


            # ------------------------------------------------
            # Không còn alpha
            # ------------------------------------------------

            if not list_alphas:

                print(
                    "🎉 ********************* Không còn alpha mới trong alpha_single.txt ********************"
                )


                del list_alphas

                break


            # =================================================
            # LIST REQUEST
            # =================================================

            List_request = []


            for alpha in list_alphas:

                List_request.append(
                    {
                        "type":
                            "REGULAR",

                        "settings":
                            default_settings,

                        "regular":
                            alpha
                    }
                )


            del list_alphas


            current_batch_number += 1


            print(
                f"📦 Batch #{current_batch_number}"
            )

            print(
                f"Alpha trong batch: "
                f"{len(List_request)}"
            )


            # =================================================
            # EXECUTOR
            # =================================================

            executor = (
                concurrent.futures.ThreadPoolExecutor(
                    max_workers=max_workers
                )
            )


            # =================================================
            # ITERATOR
            # =================================================

            alpha_iterator = iter(
                List_request
            )


            # =================================================
            # FUTURE MAP
            # =================================================

            future_to_alpha = {}


            # Thời điểm từng Future bắt đầu
            future_start_times = {}


            # =================================================
            # SUBMIT 8 FUTURE ĐẦU
            # =================================================

            for _ in range(
                max_workers
            ):

                try:

                    alpha_data = next(
                        alpha_iterator
                    )

                except StopIteration:

                    break


                future = executor.submit(
                    process_alpha,
                    s,
                    alpha_data,
                    stop_event
                )


                future_to_alpha[
                    future
                ] = alpha_data


                future_start_times[
                    future
                ] = time.time()


            # =================================================
            # BATCH STATE
            # =================================================

            stop_processing = False


            # =================================================
            # PROCESS FUTURES
            # =================================================

            try:

                while (
                    future_to_alpha
                    and not stop_processing
                ):

                    # ------------------------------------------------
                    # WATCHDOG
                    # ------------------------------------------------

                    watchdog_check(
                        future_start_times,
                        future_to_alpha
                    )


                    # ------------------------------------------------
                    # WAIT
                    #
                    # Chỉ wait 15 giây để watchdog có cơ hội kiểm tra.
                    # ------------------------------------------------

                    done, not_done = (
                        concurrent.futures.wait(
                            future_to_alpha.keys(),
                            timeout=WATCHDOG_CHECK_INTERVAL,
                            return_when=(
                                concurrent.futures.FIRST_COMPLETED
                            )
                        )
                    )


                    # ------------------------------------------------
                    # Không có Future xong
                    # ------------------------------------------------

                    if not done:

                        continue


                    # =================================================
                    # PROCESS DONE FUTURES
                    # =================================================

                    for future in done:

                        alpha_data = (
                            future_to_alpha.pop(
                                future,
                                None
                            )
                        )


                        future_start_times.pop(
                            future,
                            None
                        )


                        alpha_name = None


                        try:

                            if alpha_data:

                                alpha_name = (
                                    alpha_data.get(
                                        "regular"
                                    )
                                )


                        except Exception:

                            pass


                        try:

                            result = future.result()


                            # ----------------------------------------
                            # Session hết
                            # ----------------------------------------

                            if result is False:

                                # print(
                                #     f"🔐 Session False: "
                                #     f"{alpha_name}"
                                # )


                                stop_event.set()

                                stop_processing = True


                                # Cancel các Future
                                # chưa bắt đầu
                                for fut in list(
                                    future_to_alpha.keys()
                                ):

                                    fut.cancel()


                                break


                        except (
                            concurrent.futures.CancelledError
                        ):

                            pass


                        except Exception as e:

                            print(
                                f"❌ Lỗi Future "
                                f"{alpha_name}: {e}"
                            )


                        finally:

                            # ----------------------------------------
                            # Giải phóng
                            # ----------------------------------------

                            try:

                                del result

                            except Exception:
                                pass


                            try:

                                del alpha_data

                            except Exception:
                                pass


                        # =================================================
                        # NẠP ALPHA TIẾP
                        # =================================================

                        if not stop_processing:

                            try:

                                next_alpha = next(
                                    alpha_iterator
                                )


                                new_future = (
                                    executor.submit(
                                        process_alpha,
                                        s,
                                        next_alpha,
                                        stop_event
                                    )
                                )


                                future_to_alpha[
                                    new_future
                                ] = next_alpha


                                future_start_times[
                                    new_future
                                ] = time.time()


                            except StopIteration:

                                # Không còn alpha
                                pass


                    # ------------------------------------------------
                    # Giải phóng temporary sets
                    # ------------------------------------------------

                    del done
                    del not_done


            except Exception as e:

                print(
                    f"❌ Lỗi main Future loop: {e}"
                )


                stop_event.set()

                stop_processing = True


                time.sleep(10)


            finally:

                # =================================================
                # CANCEL FUTURE
                # =================================================

                if stop_processing:

                    for fut in list(
                        future_to_alpha.keys()
                    ):

                        try:

                            fut.cancel()

                        except Exception:
                            pass


                # =================================================
                # CLEAR MAP
                # =================================================

                future_to_alpha.clear()

                future_start_times.clear()


                del future_to_alpha
                del future_start_times


                # =================================================
                # SHUTDOWN
                # =================================================

                try:

                    executor.shutdown(
                        wait=False,
                        cancel_futures=True
                    )

                except TypeError:

                    executor.shutdown(
                        wait=False
                    )


                # =================================================
                # GIẢI PHÓNG
                # =================================================

                del List_request
                del alpha_iterator


                # =================================================
                # GC
                # =================================================

                gc.collect()


                print(
                    f"✅ Kết thúc batch "
                    f"#{current_batch_number} "
                    f"{datetime.now(VIETNAM_TZ)}"
                )


            # =================================================
            # SESSION FALSE
            # =================================================

            if stop_processing:

                print(
                    "⚠️ Batch dừng do session hết hạn."
                )


                # ------------------------------------------------
                # Tạo session mới ngay
                # ------------------------------------------------

                s = create_session()


                if s is None:

                    print(
                        "❌ Không tạo được session mới."
                    )

                    time.sleep(120)

                    continue


                current_session_number += 1


                gc.collect()


                continue


            # =================================================
            # BATCH HẾT
            #
            # Nếu session vẫn còn:
            # vòng while tiếp tục đọc thêm 1500 alpha.
            # =================================================

            print(
                f"📦 Đã xử lý xong batch "
                f"#{current_batch_number}"
            )


            # ------------------------------------------------
            # Check session ngay sau batch
            # ------------------------------------------------

            try:

                remaining_session = (
                    check_session_timeout(s)
                )

            except Exception:

                remaining_session = 0


            if remaining_session > 0:

                print(
                    f"➡️ Session vẫn còn "
                    f"{remaining_session}. "
                    f"Load batch 1500 tiếp theo."
                )

            else:

                print(
                    "🔐 Session đã hết sau batch."
                )


            gc.collect()


            continue


        # ====================================================
        # SESSION HẾT
        # ====================================================

        count_load += 1


        if (
            count_load % 30
            == 0
        ):

            print(
                f"Session đã hết hạn, "
                f"load lại session lúc --- "
                f"{datetime.now(VIETNAM_TZ)}"
            )

        # ----------------------------------------------------
        # Chờ
        # ----------------------------------------------------

        time.sleep(120)


        # ----------------------------------------------------
        # Tạo session mới
        # ----------------------------------------------------

        try:

            s = create_session()


        except Exception as e:

            print(
                f"❌ Lỗi tạo session mới: {e}"
            )

            s = None


        if s is None:

            print(
                "⚠️ Chưa tạo được session mới."
            )

            time.sleep(120)

            continue


        current_session_number += 1


        # ----------------------------------------------------
        # GC
        # ----------------------------------------------------

        gc.collect()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except KeyboardInterrupt:

        print()

        print(
            "🛑 Người dùng dừng chương trình."
        )


    except Exception as e:

        print(
            f"💥 MAIN CRASH: {e}"
        )


        # ----------------------------------------------------
        # Nếu main crash bất ngờ:
        # restart process sau 10 giây.
        # ----------------------------------------------------

        try:

            sys.stdout.flush()
            sys.stderr.flush()

        except Exception:
            pass


        time.sleep(10)


        os.execv(
            sys.executable,
            [
                sys.executable
            ] + sys.argv
        )