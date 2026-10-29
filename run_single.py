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
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_FILE = os.path.join(BASE_DIR, 'session.json')
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(CURRENT_DIR, 'config_single.json')
with open(config_file, 'r', encoding='utf-8') as file:
    config = json.load(file)
default_settings = config.get('default_settings')
output_csv = config.get('OUTPUT_CSV')
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

max_workers = 8

MAX_ALPHA_PER_BATCH = 1500
MAX_ALPHA_RUNTIME = 45 * 60
WATCHDOG_NO_PROGRESS = 60 * 60
WATCHDOG_CHECK_INTERVAL = 15
RESTART_DELAY = 5
SIMULATION_URL = 'https://api.worldquantbrain.com/simulations'
stop_event = threading.Event()
csv_write_lock = threading.Lock()
pass_write_lock = threading.Lock()
false_write_lock = threading.Lock()
watchdog_lock = threading.Lock()
last_progress_time = time.time()
completed_alpha_count = 0
running_alpha_count = 0
current_batch_number = 0
current_session_number = 0

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
        return (last_progress_time, completed_alpha_count, running_alpha_count)

def restart_process(reason):
    print()
    print('=' * 80)
    print('🚨 WATCHDOG RESTART')
    print(reason)
    print(f'Time : {datetime.now(VIETNAM_TZ)}')
    print('=' * 80)
    print()
    try:
        stop_event.set()
    except Exception:
        pass
    sys.stdout.flush()
    sys.stderr.flush()
    time.sleep(RESTART_DELAY)
    os.execv(sys.executable, [sys.executable] + sys.argv)

def watchdog_check(future_start_times, future_to_alpha):
    """
    Kiểm tra:

    1. Future nào chạy quá MAX_ALPHA_RUNTIME
    2. Toàn bộ hệ thống không có progress quá WATCHDOG_NO_PROGRESS
    """
    now = time.time()
    for future, start_time in list(future_start_times.items()):
        runtime = now - start_time
        if runtime >= MAX_ALPHA_RUNTIME:
            alpha_data = future_to_alpha.get(future)
            alpha_name = None
            try:
                if alpha_data:
                    alpha_name = alpha_data.get('regular')
            except Exception:
                alpha_name = None
            restart_process(f'Future chạy quá {MAX_ALPHA_RUNTIME / 60:.0f} phút. Runtime={runtime / 60:.1f} phút. Alpha={alpha_name}')
    last_progress, completed_count, running_count = get_watchdog_state()
    no_progress_time = now - last_progress
    if running_count > 0 and no_progress_time >= WATCHDOG_NO_PROGRESS:
        restart_process(f'Không có alpha hoàn thành trong {no_progress_time / 60:.1f} phút. Completed={completed_count}, Running={running_count}')

def process_data(result_data, output_csv):
    """
    Lấy dữ liệu cần thiết từ simulation result
    và ghi trực tiếp vào CSV.

    Không tạo DataFrame 1 dòng.
    """
    try:
        is_data = result_data.get('is', {})
        checks_data = is_data.get('checks', [])
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
        LOW_GLB_AMER_SHARPE_result = None
        LOW_GLB_EMEA_SHARPE_result = None
        LOW_GLB_APAC_SHARPE_result = None
        CLUSTER_TEST_value = None
        MATCHES_PYRAMID_effective = None
        MATCHES_PYRAMID_multiplier = None
        MATCHES_PYRAMID_result = None
        LOW_ASI_JPN_SHARPE_value = None
        LOW_ASI_JPN_SHARPE_result = None
        LOW_INVESTABILITY_CONSTRAINED_SHARPE_value = None
        LOW_INVESTABILITY_CONSTRAINED_SHARPE_result = None
        LOW_ROBUST_UNIVERSE_SHARPE_WITH_RATIO_value = None
        LOW_ROBUST_UNIVERSE_SHARPE_WITH_RATIO_result = None
        LOW_ROBUST_UNIVERSE_RETURNS_value = None
        LOW_ROBUST_UNIVERSE_RETURNS_result = None
        for check in checks_data:
            if not isinstance(check, dict):
                continue
            check_name = check.get('name')
            if check_name == 'CONCENTRATED_WEIGHT':
                concentrated_weight_value = check.get('value')
                concentrated_weight_result = check.get('result')
            elif check_name == 'LOW_2Y_SHARPE':
                low_2y_sharpe_value = check.get('value')
                low_2y_sharpe_result = check.get('result')
            elif check_name == 'LOW_SUB_UNIVERSE_SHARPE':
                low_sub_universe_sharpe_value = check.get('value')
                low_sub_universe_sharpe_result = check.get('result')
            elif check_name == 'IS_LADDER_SHARPE':
                IS_LADDER_SHARPE_value = check.get('value')
                IS_LADDER_SHARPE_result = check.get('result')
            elif check_name == 'MATCHES_PYRAMID':
                MATCHES_PYRAMID_effective = check.get('effective')
                MATCHES_PYRAMID_multiplier = check.get('multiplier')
                MATCHES_PYRAMID_result = check.get('result')
            elif check_name == 'LOW_ROBUST_UNIVERSE_SHARPE':
                LOW_ROBUST_UNIVERSE_SHARPE_value = check.get('value')
                LOW_ROBUST_UNIVERSE_SHARPE_result = check.get('result')
            elif check_name == 'LOW_GLB_AMER_SHARPE':
                LOW_GLB_AMER_SHARPE_result = check.get('result')
            elif check_name == 'LOW_GLB_EMEA_SHARPE':
                LOW_GLB_EMEA_SHARPE_result = check.get('result')
            elif check_name == 'LOW_GLB_APAC_SHARPE':
                LOW_GLB_APAC_SHARPE_result = check.get('result')
            elif check_name == 'CLUSTER_TEST':
                CLUSTER_TEST_value = check.get('value')
            elif check_name == 'LOW_ASI_JPN_SHARPE':
                LOW_ASI_JPN_SHARPE_value = check.get('value')
                LOW_ASI_JPN_SHARPE_result = check.get('result')
            elif check_name == 'LOW_INVESTABILITY_CONSTRAINED_SHARPE':
                LOW_INVESTABILITY_CONSTRAINED_SHARPE_value = check.get('value')
                LOW_INVESTABILITY_CONSTRAINED_SHARPE_result = check.get('result')
            elif check_name == 'LOW_ROBUST_UNIVERSE_SHARPE.WITH_RATIO':
                LOW_ROBUST_UNIVERSE_SHARPE_WITH_RATIO_value = check.get('value')
                LOW_ROBUST_UNIVERSE_SHARPE_WITH_RATIO_result = check.get('result')
            elif check_name == 'LOW_ROBUST_UNIVERSE_RETURNS':
                LOW_ROBUST_UNIVERSE_RETURNS_value = check.get('value')
                LOW_ROBUST_UNIVERSE_RETURNS_result = check.get('result')
        regular_data = result_data.get('regular', {})
        if not isinstance(regular_data, dict):
            regular_data = {}
        row_data = {'id': result_data.get('id'), 'sharpe': is_data.get('sharpe'), 'fitness': is_data.get('fitness'), 'LOW_2Y_SHARPE_value': low_2y_sharpe_value, 'LOW_SUB_UNIVERSE_SHARPE_value': low_sub_universe_sharpe_value, 'LOW_ROBUST_UNIVERSE_SHARPE_value': LOW_ROBUST_UNIVERSE_SHARPE_value, 'LOW_ASI_JPN_SHARPE_value': LOW_ASI_JPN_SHARPE_value, 'LOW_INVESTABILITY_CONSTRAINED_SHARPE_value': LOW_INVESTABILITY_CONSTRAINED_SHARPE_value, 'LOW_ROBUST_UNIVERSE_SHARPE_WITH_RATIO_value': LOW_ROBUST_UNIVERSE_SHARPE_WITH_RATIO_value, 'LOW_ROBUST_UNIVERSE_RETURNS_value': LOW_ROBUST_UNIVERSE_RETURNS_value, 'pnl': is_data.get('pnl'), 'turnover': is_data.get('turnover'), 'returns': is_data.get('returns'), 'drawdown': is_data.get('drawdown'), 'margin': is_data.get('margin'), 'CONCENTRATED_WEIGHT_value': concentrated_weight_value, 'CLUSTER_TEST_value': CLUSTER_TEST_value, 'CONCENTRATED_WEIGHT_result': concentrated_weight_result, 'LOW_2Y_SHARPE_result': low_2y_sharpe_result, 'LOW_SUB_UNIVERSE_SHARPE_result': low_sub_universe_sharpe_result, 'LOW_ROBUST_UNIVERSE_SHARPE_result': LOW_ROBUST_UNIVERSE_SHARPE_result, 'LOW_ASI_JPN_SHARPE_result': LOW_ASI_JPN_SHARPE_result, 'LOW_INVESTABILITY_CONSTRAINED_SHARPE_result': LOW_INVESTABILITY_CONSTRAINED_SHARPE_result, 'LOW_ROBUST_UNIVERSE_SHARPE_WITH_RATIO_result': LOW_ROBUST_UNIVERSE_SHARPE_WITH_RATIO_result, 'LOW_ROBUST_UNIVERSE_RETURNS_result': LOW_ROBUST_UNIVERSE_RETURNS_result, 'LOW_GLB_AMER_SHARPE_result': LOW_GLB_AMER_SHARPE_result, 'LOW_GLB_EMEA_SHARPE_result': LOW_GLB_EMEA_SHARPE_result, 'LOW_GLB_APAC_SHARPE_result': LOW_GLB_APAC_SHARPE_result, 'IS_LADDER_SHARPE_result': IS_LADDER_SHARPE_result, 'MATCHES_PYRAMID_effective': MATCHES_PYRAMID_effective, 'MATCHES_PYRAMID_multiplier': MATCHES_PYRAMID_multiplier, 'MATCHES_PYRAMID_result': MATCHES_PYRAMID_result, 'operatorCount': regular_data.get('operatorCount'), 'regular': regular_data.get('code'), 'bookSize': is_data.get('bookSize'), 'longCount': is_data.get('longCount'), 'shortCount': is_data.get('shortCount'), 'startDate': is_data.get('startDate')}
        with csv_write_lock:
            file_exists = os.path.exists(output_csv) and os.path.getsize(output_csv) > 0
            with open(output_csv, 'a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS, extrasaction='ignore')
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row_data)
        del row_data
        del checks_data
        del regular_data
        return True
    except Exception as e:
        print(f'❌ Lỗi khi ghi file CSV: {e}')
        return False

CSV_COLUMNS = ['id', 'sharpe', 'fitness','turnover','pnl', 'LOW_2Y_SHARPE_value' , 'CONCENTRATED_WEIGHT_result', 'LOW_2Y_SHARPE_result', 'LOW_SUB_UNIVERSE_SHARPE_result', 'LOW_ROBUST_UNIVERSE_SHARPE_result', 'LOW_ASI_JPN_SHARPE_result', 'LOW_INVESTABILITY_CONSTRAINED_SHARPE_result', 'LOW_ROBUST_UNIVERSE_SHARPE_WITH_RATIO_result', 'LOW_ROBUST_UNIVERSE_RETURNS_result', 'LOW_GLB_AMER_SHARPE_result', 'LOW_GLB_EMEA_SHARPE_result', 'LOW_GLB_APAC_SHARPE_result', 'IS_LADDER_SHARPE_result', 'MATCHES_PYRAMID_effective', 'MATCHES_PYRAMID_multiplier', 'MATCHES_PYRAMID_result', 'operatorCount', 'regular','LOW_SUB_UNIVERSE_SHARPE_value', 'LOW_ROBUST_UNIVERSE_SHARPE_value', 'LOW_ASI_JPN_SHARPE_value', 'LOW_INVESTABILITY_CONSTRAINED_SHARPE_value', 'LOW_ROBUST_UNIVERSE_SHARPE_WITH_RATIO_value', 'LOW_ROBUST_UNIVERSE_RETURNS_value', 'returns', 'drawdown', 'margin', 'CONCENTRATED_WEIGHT_value', 'CLUSTER_TEST_value' , 'bookSize', 'longCount', 'shortCount', 'startDate']
def ensure_csv_schema(output_csv):
    if not os.path.exists(output_csv):
        with open(output_csv, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_COLUMNS)
        print('✅ Tạo file CSV mới với schema chuẩn')
        return
    if os.path.getsize(output_csv) == 0:
        with open(output_csv, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_COLUMNS)
        print('✅ CSV rỗng → tạo header')
        return
    try:
        with open(output_csv, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            existing_columns = next(reader)
    except Exception as e:
        print(f'❌ Không đọc được CSV header: {e}')
        return
    if existing_columns == CSV_COLUMNS:
        print('✅ CSV schema đã đúng')
        return
    print('⚠️ CSV schema khác chuẩn → đang chuẩn hóa...')
    temp_file = output_csv + '.tmp'
    try:
        with open(output_csv, 'r', newline='', encoding='utf-8') as source, open(temp_file, 'w', newline='', encoding='utf-8') as target:
            reader = csv.DictReader(source)
            writer = csv.DictWriter(target, fieldnames=CSV_COLUMNS, extrasaction='ignore')
            writer.writeheader()
            for row in reader:
                writer.writerow({column: row.get(column) for column in CSV_COLUMNS})
        os.replace(temp_file, output_csv)
        print('✅ Schema CSV đã được chuẩn hóa')
    except Exception as e:
        print(f'❌ Lỗi chuẩn hóa CSV: {e}')
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass

def load_session():
    if not os.path.exists(SESSION_FILE):
        print('Không tìm thấy session, hãy xác thực lại.')
        return None
    try:
        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        token = cookies.get('t')
        if not token:
            print('❌ session.json không có token t')
            return None
        return token
    except Exception as e:
        print(f'❌ Lỗi load session: {e}')
        return None

def load_headers():
    token = load_session()
    if not token:
        return {}
    return {'Content-Type': 'application/json', 'Cookie': f't={token}'}

def read_alpha(path, max_lines=1500):
    pass_lines = set()
    if os.path.exists('alpha_pass_single.txt'):
        with open('alpha_pass_single.txt', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    pass_lines.add(stripped)
    false_lines = set()
    if os.path.exists('alpha_false_single.txt'):
        with open('alpha_false_single.txt', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    false_lines.add(stripped)
    filtered_alphas = pass_lines | false_lines
    del pass_lines
    del false_lines
    list_alphas = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if stripped and stripped not in filtered_alphas:
                list_alphas.append(stripped)
                if len(list_alphas) >= max_lines:
                    break
    del filtered_alphas
    return list_alphas

def write_alpha_pass(alpha):
    with pass_write_lock:
        with open('alpha_pass_single.txt', 'a', encoding='utf-8') as file:
            file.write(alpha + '\n')

def write_alpha_false(alpha):
    with false_write_lock:
        with open('alpha_false_single.txt', 'a', encoding='utf-8') as file:
            file.write(alpha + '\n')

def process_alpha(s, alpha_data, stop_event):
    watchdog_mark_start()
    alpha_regular = None
    try:
        if stop_event.is_set():
            return False
        if alpha_data.get('regular') is None:
            return None
        alpha_regular = alpha_data['regular']
        while True:
            if stop_event.is_set():
                return False
            simulate_response = None
            try:
                simulate_response = s.post(SIMULATION_URL, json=alpha_data, timeout=300)
            except requests.exceptions.Timeout:
                print(f'⌛ POST simulation Timeout {datetime.now(VIETNAM_TZ)}')
                write_alpha_false(alpha_regular)
                return {'completed': False}
            except requests.exceptions.ConnectionError as e:
                print(f'🌐 POST lỗi mạng: {e}')
                time.sleep(30)
                continue
            except requests.exceptions.RequestException as e:
                print(f'⚠️ POST request error: {e}')
                time.sleep(30)
                continue
            if simulate_response.status_code == 201:
                break
            elif simulate_response.status_code == 401:
                print(f'🔐 Session đã hết hạn {datetime.now(VIETNAM_TZ)}')
                stop_event.set()
                return False
            elif simulate_response.status_code == 429:
                try:
                    retry_after = int(simulate_response.headers.get('Retry-After', 100))
                except Exception:
                    retry_after = 100
                jitter = random.uniform(1, 6)
                total_sleep = retry_after + jitter
                print(f'🚫 429 SIMULATION_LIMIT_EXCEEDED. Sleep {total_sleep:.2f}s -- {datetime.now(VIETNAM_TZ)}')
                del simulate_response
                time.sleep(total_sleep)
                continue
            elif simulate_response.status_code == 502:
                sleep_time = random.uniform(40, 60)
                print(f'🌐 502 Bad Gateway. Sleep {sleep_time:.2f}s -- {datetime.now(VIETNAM_TZ)}')
                del simulate_response
                time.sleep(sleep_time)
                continue
            else:
                response_status = simulate_response.status_code
                response_text = simulate_response.text
                print(f'⚠️ Simulation POST lỗi: {response_status}, {response_text[:500]}')
                write_alpha_false(alpha_regular)
                del simulate_response
                return {'completed': False}
        simulation_progress_url = simulate_response.headers.get('Location')
        del simulate_response
        if not simulation_progress_url:
            print(f'❌ Không có Location cho alpha {alpha_regular}')
            write_alpha_false(alpha_regular)
            return {'completed': False}
        progress_json = None
        progress_status_code = None
        error_flag = False
        while True:
            if stop_event.is_set():
                return False
            simulation_progress_response = None
            try:
                simulation_progress_response = s.get(simulation_progress_url, timeout=1800)
            except requests.exceptions.ReadTimeout:
                print(f'❌ GET simulation timeout {datetime.now(VIETNAM_TZ)}')
                stop_event.set()
                return False
            except requests.exceptions.ConnectionError as e:
                print(f'🌐 GET lỗi mạng: {e}')
                time.sleep(30)
                continue
            except requests.exceptions.RequestException as e:
                print(f'⚠️ GET request error: {e}')
                time.sleep(30)
                continue
            progress_status_code = simulation_progress_response.status_code
            progress_json = None
            if progress_status_code // 100 != 2:
                try:
                    progress_json = simulation_progress_response.json()
                except Exception:
                    progress_json = {}
                if progress_json == {'detail': 'Incorrect authentication credentials.'}:
                    print(f'🔐 Session hết hạn {datetime.now(VIETNAM_TZ)}')
                    del progress_json
                    del simulation_progress_response
                    stop_event.set()
                    return False
                print(f'Simulation failed, Status code: {progress_status_code}')
                del progress_json
                del simulation_progress_response
                time.sleep(30)
                continue
            retry_after = simulation_progress_response.headers.get('Retry-After', 0)
            try:
                retry_after = float(retry_after)
            except Exception:
                retry_after = 0
            if retry_after <= 0:
                if progress_json is None:
                    try:
                        progress_json = simulation_progress_response.json()
                    except Exception:
                        progress_json = {}
                if progress_json.get('status', 'ERROR') == 'ERROR':
                    error_flag = True
                del simulation_progress_response
                break
            del progress_json
            del simulation_progress_response
            time.sleep(retry_after)
        if error_flag:
            print(f'❌ Simulation failed. {progress_json} Status code: {progress_status_code}')
            if progress_json == {'detail': 'Incorrect authentication credentials.'}:
                stop_event.set()
                del progress_json
                return False
            write_alpha_false(alpha_regular)
            del progress_json
            return {'completed': False}
        alpha = progress_json.get('alpha', 0)
        if alpha == 0:
            print(f"❌ Simulation alpha {progress_json.get('id')} failed. {progress_json}")
            del progress_json
            write_alpha_false(alpha_regular)
            return {'completed': False}
        del progress_json
        simulation_result = get_simulation_result_json(s, alpha)
        # print('simulation_result : ', simulation_result)
        Flat_process_data = process_data(simulation_result, output_csv)
        del simulation_result
        if Flat_process_data:
            write_alpha_pass(alpha_regular)
            print('555', end='', flush=True)
        else:
            write_alpha_false(alpha_regular)
        return {'completed': bool(Flat_process_data)}
    except Exception as e:
        print(f'❌ Exception process_alpha {alpha_regular}: {e}')
        if alpha_regular:
            try:
                write_alpha_false(alpha_regular)
            except Exception:
                pass
        return {'completed': False}
    finally:
        try:
            del alpha_data
        except Exception:
            pass
        watchdog_mark_done()

def create_session():
    new_session = ace.SingleSession()
    headers = load_headers()
    if not headers:
        print('❌ Không load được headers')
        return None
    new_session.headers.update(headers)
    return new_session

def main():
    global current_batch_number
    global current_session_number
    global last_progress_time
    ensure_csv_schema(output_csv)
    s = create_session()
    if s is None:
        print('❌ Không tạo được session.')
        return
    current_session_number = 1
    print(f'🚀 Start Run Alpha {datetime.now(VIETNAM_TZ)}')
    print(f'Workers: {max_workers}')
    print(f'Alpha/batch: {MAX_ALPHA_PER_BATCH}')
    print(f'Watchdog alpha: {MAX_ALPHA_RUNTIME / 60:.0f} phút')
    print(f'Watchdog no progress: {WATCHDOG_NO_PROGRESS / 60:.0f} phút')
    count_load = 0
    while True:
        try:
            time_session = check_session_timeout(s)
        except Exception as e:
            print(f'⚠️ check_session_timeout lỗi: {e}')
            time_session = 0
        if time_session > 0:
            print()
            print('=' * 80)
            print(f'Session còn: {time_session} ---- {datetime.now(VIETNAM_TZ)}')
            print('=' * 80)
            stop_event.clear()
            with watchdog_lock:
                last_progress_time = time.time()
            list_alphas = read_alpha('alpha_single.txt', max_lines=MAX_ALPHA_PER_BATCH)
            if not list_alphas:
                print('🎉 ******************** Không còn alpha mới trong alpha_single.txt ********************')
                del list_alphas
                break
            List_request = []
            for alpha in list_alphas:
                List_request.append({'type': 'REGULAR', 'settings': default_settings, 'regular': alpha})
            del list_alphas
            current_batch_number += 1
            print(f'📦 Batch #{current_batch_number}')
            print(f'Alpha trong batch: {len(List_request)}')
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
            alpha_iterator = iter(List_request)
            future_to_alpha = {}
            future_start_times = {}
            for _ in range(max_workers):
                try:
                    alpha_data = next(alpha_iterator)
                except StopIteration:
                    break
                future = executor.submit(process_alpha, s, alpha_data, stop_event)
                future_to_alpha[future] = alpha_data
                future_start_times[future] = time.time()
            stop_processing = False
            try:
                while future_to_alpha and (not stop_processing):
                    watchdog_check(future_start_times, future_to_alpha)
                    done, not_done = concurrent.futures.wait(future_to_alpha.keys(), timeout=WATCHDOG_CHECK_INTERVAL, return_when=concurrent.futures.FIRST_COMPLETED)
                    if not done:
                        continue
                    for future in done:
                        alpha_data = future_to_alpha.pop(future, None)
                        future_start_times.pop(future, None)
                        alpha_name = None
                        try:
                            if alpha_data:
                                alpha_name = alpha_data.get('regular')
                        except Exception:
                            pass
                        try:
                            result = future.result()
                            if result is False:
                                stop_event.set()
                                stop_processing = True
                                for fut in list(future_to_alpha.keys()):
                                    fut.cancel()
                                break
                        except concurrent.futures.CancelledError:
                            pass
                        except Exception as e:
                            print(f'❌ Lỗi Future {alpha_name}: {e}')
                        finally:
                            try:
                                del result
                            except Exception:
                                pass
                            try:
                                del alpha_data
                            except Exception:
                                pass
                        if not stop_processing:
                            try:
                                next_alpha = next(alpha_iterator)
                                new_future = executor.submit(process_alpha, s, next_alpha, stop_event)
                                future_to_alpha[new_future] = next_alpha
                                future_start_times[new_future] = time.time()
                            except StopIteration:
                                pass
                    del done
                    del not_done
            except Exception as e:
                print(f'❌ Lỗi main Future loop: {e}')
                stop_event.set()
                stop_processing = True
                time.sleep(10)
            finally:
                if stop_processing:
                    for fut in list(future_to_alpha.keys()):
                        try:
                            fut.cancel()
                        except Exception:
                            pass
                future_to_alpha.clear()
                future_start_times.clear()
                del future_to_alpha
                del future_start_times
                try:
                    executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    executor.shutdown(wait=False)
                del List_request
                del alpha_iterator
                gc.collect()
                print(f'✅ Kết thúc batch #{current_batch_number} {datetime.now(VIETNAM_TZ)}')
            if stop_processing:
                print('⚠️ Batch dừng do session hết hạn.')
                s = create_session()
                if s is None:
                    print('❌ Không tạo được session mới.')
                    time.sleep(120)
                    continue
                current_session_number += 1
                gc.collect()
                continue
            print(f'📦 Đã xử lý xong batch #{current_batch_number}')
            try:
                remaining_session = check_session_timeout(s)
            except Exception:
                remaining_session = 0
            if remaining_session > 0:
                print(f'➡️ Session vẫn còn {remaining_session}. Load batch 1500 tiếp theo.')
            else:
                print('🔐 Session đã hết sau batch.')
            gc.collect()
            continue
        count_load += 1
        if count_load % 30 == 0:
            print(f'Session đã hết hạn, load lại session lúc --- {datetime.now(VIETNAM_TZ)}')
        time.sleep(120)
        try:
            s = create_session()
        except Exception as e:
            print(f'❌ Lỗi tạo session mới: {e}')
            s = None
        if s is None:
            print('⚠️ Chưa tạo được session mới.')
            time.sleep(120)
            continue
        current_session_number += 1
        gc.collect()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print('🛑 Người dùng dừng chương trình.')
    except Exception as e:
        print(f'💥 MAIN CRASH: {e}')
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        time.sleep(10)
        os.execv(sys.executable, [sys.executable] + sys.argv)