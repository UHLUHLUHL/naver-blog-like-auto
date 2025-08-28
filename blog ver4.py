import gradio as gr
import time
import threading
import random
import math
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# --- 계정 정보 저장을 위한 파일 경로 ---
ACCOUNTS_FILE = "accounts.json"

# --- 셀레니움 봇 클래스 ---
class NaverBlogBot:
    """
    Selenium을 사용하여 네이버 블로그 자동화 작업을 수행하는 클래스.
    """
    def __init__(self):
        self.driver = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set() # 시작 시에는 PAUSE 상태가 아님 (set() -> True)

    def _initialize_driver(self):
        """WebDriver를 초기화합니다."""
        try:
            options = webdriver.ChromeOptions()
            # options.add_argument("--headless")  # UI 없이 실행하려면 이 옵션 활성화
            options.add_argument("--disable-gpu")
            options.add_argument("--log-level=3") # 콘솔 로그 최소화
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(5) # 암시적 대기 설정
            return True
        except Exception as e:
            self.log(f"드라이버 초기화 실패: {e}", "ERROR")
            return False

    def log(self, message, log_type="INFO"):
        """Gradio UI에 표시될 로그 메시지를 생성합니다."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}][{log_type}] {message}\n"

    def stop(self):
        """봇의 작동 중지를 요청합니다."""
        self.stop_event.set()

    def pause(self):
        """봇을 일시정지합니다."""
        self.pause_event.clear()

    def resume(self):
        """봇을 재개합니다."""
        self.pause_event.set()

    def _login(self, naver_id, naver_pw):
        """네이버 로그인을 수행합니다."""
        self.driver.get('https://nid.naver.com/nidlogin.login')
        yield self.log("로그인 페이지로 이동했습니다.")
        
        # IP 보안 해제
        try:
            # 'ON' 상태인 IP 보안 스위치를 찾아 클릭
            ip_security_switch = self.driver.find_element(By.CSS_SELECTOR, "span.switch_on")
            ip_security_switch.click()
            yield self.log("IP 보안 기능을 OFF로 설정했습니다.")
        except NoSuchElementException:
            yield self.log("IP 보안이 이미 OFF 상태이거나 버튼을 찾을 수 없습니다.", "WARN")
        except Exception as e:
            yield self.log(f"IP 보안 설정 중 오류 발생: {e}", "ERROR")

        time.sleep(1)

        # 자바스크립트를 이용해 아이디와 비밀번호 입력 (봇 탐지 우회)
        self.driver.execute_script(f"document.getElementById('id').value = '{naver_id}'")
        self.driver.execute_script(f"document.getElementById('pw').value = '{naver_pw}'")
        yield self.log("ID와 비밀번호를 입력했습니다.")
        
        # 로그인 버튼 클릭
        self.driver.find_element(By.ID, 'log.login').click()
        
        # 로그인 성공/실패 확인
        try:
            # 2FA (2단계 인증) 또는 새 기기 등록 페이지 확인
            WebDriverWait(self.driver, 5).until(
                EC.any_of(
                    EC.presence_of_element_located((By.ID, "my_info")), # 로그인 성공 시 '내 정보'
                    EC.presence_of_element_located((By.ID, "new.save")), # 새 기기 등록
                    EC.presence_of_element_located((By.ID, "err_common")) # 로그인 실패
                )
            )

            current_url = self.driver.current_url
            if "nid.naver.com/login/sso/finalize" in current_url or "www.naver.com" in current_url:
                 yield self.log("로그인에 성공했습니다!")
                 return True
            elif "nid.naver.com/login/ext/deviceConfirm" in current_url:
                 yield self.log("새로운 기기 등록이 필요합니다. 브라우저에서 직접 등록 후 다시 시도해주세요.", "WARN")
                 time.sleep(30)
                 return True
            else:
                 error_element = self.driver.find_element(By.ID, "err_common")
                 yield self.log(f"로그인 실패: {error_element.text}", "ERROR")
                 return False

        except TimeoutException:
            if "www.naver.com" in self.driver.current_url:
                 yield self.log("로그인에 성공했습니다! (URL 확인)")
                 return True
            else:
                yield self.log("로그인 페이지에서 벗어나지 못했습니다. ID/PW를 확인해주세요.", "ERROR")
                return False

    def _human_like_scroll(self):
        """고도로 인간적인, 비선형적이고 불규칙한 방식으로 페이지를 스크롤합니다."""
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        num_scrolls = random.randint(5, 7)

        scroll_percentages = [random.uniform(0.15, 0.25) for _ in range(num_scrolls)]
        total_ratio = sum(scroll_percentages)
        scroll_percentages = [p / total_ratio for p in scroll_percentages]

        current_scroll_position = self.driver.execute_script("return window.pageYOffset;")

        for percent in scroll_percentages:
            if self.stop_event.is_set(): break
            self.pause_event.wait() # 일시정지 상태면 여기서 대기
            
            scroll_distance = total_height * percent
            start_pos = current_scroll_position
            
            animation_steps = random.randint(40, 60)
            total_duration = random.uniform(0.51, 0.72) # 스크롤 시간 변경

            for i in range(1, animation_steps + 1):
                if self.stop_event.is_set(): break
                self.pause_event.wait()
                
                t = i / animation_steps
                progress = -(math.cos(math.pi * t) - 1) / 2
                
                # Jitter 효과 제거
                scroll_to = start_pos + (scroll_distance * progress)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_to});")
                
                time.sleep(total_duration / animation_steps)
            
            current_scroll_position = start_pos + scroll_distance
            self.driver.execute_script(f"window.scrollTo(0, {current_scroll_position});")

            if random.random() < 0.25: 
                correction = (random.random() - 0.5) * 0.05 * total_height 
                self.driver.execute_script(f"window.scrollBy(0, {correction});")
                time.sleep(random.uniform(0.2, 0.4))
                current_scroll_position += correction

            if random.random() < 0.4: 
                time.sleep(random.uniform(0.3, 0.6))

        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        yield self.log("  └ 페이지를 자연스럽게 스크롤했습니다.")

    def _like_posts(self):
        """이웃 새글 페이지를 순회하며 각 포스트에 들어가 '공감'을 누릅니다."""
        current_page = 1
        total_liked_count = 0
        yield self.log("이웃 새글 공감 작업을 시작합니다.")

        while True: # 페이지 루프
            self.pause_event.wait()
            if self.stop_event.is_set():
                yield self.log("사용자에 의해 작업이 중지되었습니다.", "WARN")
                break
            
            target_url = f"https://section.blog.naver.com/BlogHome.naver?directoryNo=0&currentPage={current_page}&groupId=0"
            self.driver.get(target_url)
            yield self.log(f"이웃 새글 {current_page}페이지로 이동했습니다.")
            time.sleep(2.5)

            initial_posts = self.driver.find_elements(By.CSS_SELECTOR, "div.list_post_article")
            if not initial_posts:
                yield self.log("현재 페이지에서 더 이상 글을 찾지 못했습니다. 작업을 종료합니다.", "INFO")
                break
            
            yield self.log(f"{current_page}페이지에서 {len(initial_posts)}개의 글을 발견했습니다.")

            while True: # 페이지 내 포스트 처리 루프
                self.pause_event.wait()
                if self.stop_event.is_set(): break

                post_containers = self.driver.find_elements(By.CSS_SELECTOR, "div.list_post_article")
                if not post_containers:
                    break
                
                post = post_containers[0]
                post_title = "제목을 찾을 수 없음"
                
                try:
                    post_title_element = post.find_element(By.CSS_SELECTOR, "span[ng-bind='post.title']")
                    post_title = post_title_element.text

                    like_button_in_list = post.find_element(By.CSS_SELECTOR, "a.u_likeit_list_btn._button")
                    delete_button = post.find_element(By.CSS_SELECTOR, "i.icon_delete")

                    if like_button_in_list.get_attribute("aria-pressed") == 'true':
                        yield self.log(f"└ '{post_title}' 글은 이미 공감 상태입니다. 목록에서 삭제합니다.", "INFO")
                        self.driver.execute_script("arguments[0].click();", delete_button)
                        time.sleep(1.5)
                        continue

                    post_link = post.find_element(By.CSS_SELECTOR, "a.text[ng-href]")
                    post_url = post_link.get_attribute("href")
                    
                    self.driver.get(post_url)
                    yield self.log(f"└ '{post_title}' 포스트로 이동합니다.")
                    
                    WebDriverWait(self.driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "mainFrame")))
                    
                    for log_msg in self._human_like_scroll(): yield log_msg

                    like_button_in_post = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[class*='u_likeit_list_btn'][aria-pressed='false']"))
                    )
                    self.driver.execute_script("arguments[0].click();", like_button_in_post)
                    total_liked_count += 1
                    yield self.log(f"  └ 공감했습니다! (총 {total_liked_count}개)", "SUCCESS")
                    time.sleep(1.5)

                except TimeoutException:
                    yield self.log(f"  └ '{post_title}'은(는) 이미 공감했거나 버튼을 찾을 수 없어 건너뜁니다.", "WARN")
                except NoSuchElementException:
                    yield self.log(f"└ '{post_title}'은(는) 비표준 포스트(광고 등)로 추정되어 건너뛰고 삭제합니다.", "WARN")
                    try:
                        delete_button = post.find_element(By.CSS_SELECTOR, "i.icon_delete")
                        self.driver.execute_script("arguments[0].click();", delete_button)
                        time.sleep(1.5)
                    except NoSuchElementException:
                        yield self.log("  └ 삭제 버튼도 찾을 수 없어 페이지를 새로고침합니다.", "WARN")
                        self.driver.refresh()
                        time.sleep(2)
                    continue
                except Exception as e:
                    yield self.log(f"  └ '{post_title}' 처리 중 예외 발생: {repr(e)}", "ERROR")
                finally:
                    self.driver.switch_to.default_content()
                    if self.driver.current_url != target_url:
                        self.driver.get(target_url)
                        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.list_post_article")))
                    
                    try:
                        first_post = self.driver.find_element(By.CSS_SELECTOR, "div.list_post_article")
                        delete_button = first_post.find_element(By.CSS_SELECTOR, "i.icon_delete")
                        self.driver.execute_script("arguments[0].click();", delete_button)
                        yield self.log("  └ 목록에서 완료된 글을 삭제했습니다.")
                        time.sleep(1.5)
                    except Exception:
                        pass

            if self.stop_event.is_set(): break
            current_page += 1

        yield self.log(f"작업 완료! 총 {total_liked_count}개의 포스트에 공감했습니다.", "SUCCESS")


    def run(self, naver_id, naver_pw):
        """자동화 봇의 전체 실행 로직을 담당합니다."""
        self.stop_event.clear()
        self.pause_event.set()
        
        if not self._initialize_driver():
            yield self.log("봇을 시작할 수 없습니다. 프로그램을 종료합니다.", "ERROR")
            return

        login_generator = self._login(naver_id, naver_pw)
        login_success = False
        for log_msg in login_generator:
            yield log_msg
            if "로그인에 성공" in log_msg:
                login_success = True
        
        if not login_success:
            yield self.log("로그인에 실패하여 작업을 중단합니다.", "ERROR")
            self.driver.quit()
            return

        like_generator = self._like_posts()
        for log_msg in like_generator:
            yield log_msg
            if self.stop_event.is_set(): break
        
        yield self.log("자동 좋아요 작업을 완료했습니다.", "INFO")
        self.driver.quit()
        self.driver = None


# --- Gradio UI 및 이벤트 핸들러 ---
bot_instance = NaverBlogBot()

def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return {}
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=4)

def manage_account(action, selected_id, naver_id, naver_pw):
    accounts = load_accounts()
    if action == "save":
        if not naver_id:
            return gr.update(), gr.update(), "저장할 ID를 입력해주세요."
        accounts[naver_id] = {"password": naver_pw}
        save_accounts(accounts)
        message = f"계정 '{naver_id}'이(가) 저장되었습니다."
    elif action == "delete":
        if not selected_id:
            return gr.update(), gr.update(), "삭제할 계정을 선택해주세요."
        if selected_id in accounts:
            del accounts[selected_id]
            save_accounts(accounts)
            message = f"계정 '{selected_id}'이(가) 삭제되었습니다."
        else:
            message = "선택된 계정을 찾을 수 없습니다."
    
    # 드롭다운 목록 업데이트
    return gr.update(choices=list(accounts.keys())), gr.update(value=None, interactive=True), message

def select_account(selected_id):
    accounts = load_accounts()
    if selected_id in accounts:
        return selected_id, accounts[selected_id]['password']
    return "", ""

def start_bot_process(naver_id, naver_pw):
    """'Start' 버튼 클릭 시 봇 실행을 시작하는 제너레이터 함수."""
    if not naver_id or not naver_pw:
        yield bot_instance.log("ID와 비밀번호를 모두 입력해주세요.", "ERROR"), "IDLE", gr.update(visible=False), gr.update(visible=False)
        return

    log_output = ""
    yield " ", "RUNNING", gr.update(visible=True, value="⏸️ 일시정지"), gr.update(visible=True)
    
    for log_message in bot_instance.run(naver_id, naver_pw):
        log_output += log_message
        yield log_output, "RUNNING", gr.update(), gr.update()
    
    yield log_output, "FINISHED", gr.update(visible=False), gr.update(visible=False)


def stop_bot_process():
    """'Stop' 버튼 클릭 시 봇을 중지시킵니다."""
    bot_instance.stop()
    return "STOPPED", gr.update(visible=False), gr.update(visible=False)

def toggle_pause_resume(current_state):
    if current_state == "RUNNING":
        bot_instance.pause()
        return "PAUSED", gr.update(value="▶️ 재개")
    elif current_state == "PAUSED":
        bot_instance.resume()
        return "RUNNING", gr.update(value="⏸️ 일시정지")
    return current_state, gr.update()

def shutdown_server():
    """서버 종료 버튼 클릭 시 호출될 함수"""
    def _shutdown_thread():
        # UI가 메시지를 표시할 시간을 주기 위해 잠시 대기
        time.sleep(1)
        # 현재 프로세스를 종료
        os._exit(0)

    # 별도의 스레드에서 종료 로직을 실행
    threading.Thread(target=_shutdown_thread, daemon=True).start()
    # 사용자에게 즉시 피드백 제공
    return "서버를 1초 후에 종료합니다..."


with gr.Blocks(theme=gr.themes.Base(primary_hue=gr.themes.colors.green, secondary_hue=gr.themes.colors.blue), title="Naver Blog Auto-Liker") as app:
    bot_state = gr.State("IDLE")
    accounts_data = gr.State(load_accounts)

    with gr.Row():
        gr.HTML("""
            <div style="display: flex; align-items: center; justify-content: center; gap: 12px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-heart-handshake"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/><path d="M12 5 9.04 7.96a2.17 2.17 0 0 0 0 3.08v0c.82.82 2.13.82 2.94 0l.06-.06L12 11l2.96-2.96c.82-.82 2.13.82 2.94 0l0 0a2.17 2.17 0 0 0 0-3.08L12 5Z"/></svg>
                <h1 style="font-size: 2em; font-weight: 700;">Naver Blog Auto-Liker</h1>
            </div>
        """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## ⚙️ 제어판 (Control Panel)")
            
            with gr.Group():
                gr.Markdown("### 계정 관리")
                accounts_dropdown = gr.Dropdown(label="저장된 계정", choices=list(accounts_data.value.keys()))
                naver_id_input = gr.Textbox(label="네이버 ID", placeholder="아이디를 입력하세요")
                naver_pw_input = gr.Textbox(label="네이버 비밀번호", type="password", placeholder="비밀번호를 입력하세요")
                with gr.Row():
                    save_button = gr.Button("💾 계정 저장")
                    delete_button = gr.Button("🗑️ 계정 삭제")
                account_message = gr.Markdown()

            with gr.Group():
                gr.Markdown("### 봇 제어")
                start_button = gr.Button("🤖 봇 시작", variant="primary")
                with gr.Row():
                    pause_resume_button = gr.Button("⏸️ 일시정지", visible=False)
                    stop_button = gr.Button("🛑 봇 중지", visible=False)
                shutdown_button = gr.Button("🔌 서버 종료", variant="stop")


            gr.Markdown("### 📊 현재 상태 (Bot Status)")
            status_output = gr.Textbox(value="IDLE", label="상태", interactive=False)
            
        with gr.Column(scale=2):
            gr.Markdown("## 📝 상태 로그 (Status Log)")
            log_output = gr.Textbox(
                label="실시간 로그",
                lines=25,
                interactive=False,
                autoscroll=True,
                max_lines=25
            )

    # 이벤트 핸들러 연결
    start_event = start_button.click(
        fn=start_bot_process,
        inputs=[naver_id_input, naver_pw_input],
        outputs=[log_output, bot_state, pause_resume_button, stop_button]
    )
    
    stop_button.click(
        fn=stop_bot_process,
        inputs=None,
        outputs=[bot_state, pause_resume_button, stop_button],
        cancels=[start_event]
    )

    pause_resume_button.click(
        fn=toggle_pause_resume,
        inputs=[bot_state],
        outputs=[bot_state, pause_resume_button]
    )

    accounts_dropdown.change(
        fn=select_account,
        inputs=[accounts_dropdown],
        outputs=[naver_id_input, naver_pw_input]
    )
    
    save_button.click(
        fn=lambda selected, nid, npw: manage_account("save", selected, nid, npw),
        inputs=[accounts_dropdown, naver_id_input, naver_pw_input],
        outputs=[accounts_dropdown, naver_id_input, account_message]
    )

    delete_button.click(
        fn=lambda selected, nid, npw: manage_account("delete", selected, nid, npw),
        inputs=[accounts_dropdown, naver_id_input, naver_pw_input],
        outputs=[accounts_dropdown, naver_id_input, account_message]
    )

    shutdown_button.click(
        fn=shutdown_server,
        inputs=None,
        outputs=[account_message]
    )


if __name__ == "__main__":
    app.launch(inbrowser=True)
